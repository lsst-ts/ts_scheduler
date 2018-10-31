import logging
from importlib import import_module
import inspect
import asyncio
import concurrent
import time

from salobj import base_csc, base
import SALPY_Scheduler

from lsst.ts.scheduler.conf.conf_utils import load_override_configuration
from lsst.ts.scheduler.setup import WORDY
from lsst.ts.scheduler.driver import Driver
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.dateloc import version as dateloc_version
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import version as obs_mod_version
from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.astrosky.model import version as astrosky_version

from lsst.sims.seeingModel import SeeingModel
from lsst.sims.seeingModel import version as seeing_version
from lsst.sims.cloudModel import CloudModel
from lsst.sims.cloudModel import version as cloud_version
from lsst.sims.downtimeModel import ScheduledDowntime, UnscheduledDowntime
from lsst.sims.downtimeModel import version as downtime_version

import lsst.pex.config as pexConfig

from scheduler_config.constants import CONFIG_DIRECTORY, CONFIG_DIRECTORY_PATH

try:
    from git import Repo
except ImportError:
    raise ImportError("gitpython not installed. Please install it with 'pip install gitpython' before proceeding.")


__all__ = ['SchedulerCSC', 'SchedulerCscParameters']


class SchedulerCscParameters(pexConfig.Config):
    """Configuration of the LSST Scheduler's Model.
    """
    recommended_settings_version = pexConfig.Field("Name of the recommended settings.", str, default='master')
    driver_type = pexConfig.Field("Choose a driver to use. This should be an import string that is passed to "
                                  "`importlib.import_module()`. Model will look for a subclass of Driver "
                                  "class inside the module.", str,
                                  default='lsst.ts.scheduler.driver')
    night_boundary = pexConfig.Field('Solar altitude (degrees) when it is considered night.', float)
    new_moon_phase_threshold = pexConfig.Field('New moon phase threshold for swapping to dark time filter.',
                                               float)
    startup_type = pexConfig.ChoiceField("The method used to startup the scheduler.", str,
                                         default='HOT',
                                         allowed={"HOT": "Hot start, this means the scheduler is started up from "
                                                         "scratch",
                                                  "WARM": "Reads the scheduler state from a previously saved "
                                                          "internal state.",
                                                  "COLD": "Rebuilds scheduler state from observation database.", })
    startup_database = pexConfig.Field("Path to the file holding scheduler state or observation database "
                                       "to be used on WARM or COLD start.", str, default='')

    def setDefaults(self):
        """Set defaults for the LSST Scheduler's Driver.
        """
        self.recommended_settings_version = 'master'
        self.driver_type = 'lsst.ts.scheduler.driver'
        self.night_boundary = -12.0
        self.new_moon_phase_threshold = 20.0
        self.startup_type = 'HOT'
        self.startup_database = ''


class SchedulerCSC(base_csc.BaseCsc):
    """This class is a reactive component which is SAL aware and delegates work.

    The SchedulerCSC is the only layer that is exposed to SAL communication. All
    commands recieved are by the SchedulerCSC then delegated to the repsonible
    objects. Along with this the SchedulerCSC maintains a statemachine which is
    taken care of by the inherited class `base_csc.BaseCsc`. 

    Attributes
    ----------
    log : logging.Log
        Logging mechanism for the SchedulerCSC.
    summary_state : `salobj.base_csc.State`
        Enume type, OFFLINE = 4 STANDBY = 5 DISABLED = 1 ENABLED = 2 FAULT = 3.
    parameters: `lsst.ts.scheduler.scheduler_csc.SchedulerCscParameters` 
        Object to contain parameter values to configure the SchedulerCSC.
    configuration_path: `str` 
        Absolute path to the configuration location for the validSettings event.
    configuration_repo: `str`
        String of comma delimated Git repos that exist at configuration_path.
        ex; "origin/master,origin/develop"
    valid_settings: `list` of `str`
        Shortened and listed names of configuration_repo. ex; [master, develop].
    models: `dict`
        Dictionary of the models necessary for the SchedulerCSC to fulfill SAL
        commands.
        - ``location`` : lsst.ts.datelo.ObservatoryLocation
        - ``observatory_model`` : lsst.ts.observatory.model.ObservatoryModel
        - ``observatory_state`` : lsst.ts.observatory.model.ObservatoryState
        - ``sky`` : lsst.ts.astrosky.model.AstronomicalSkyModel
        - ``seeing`` : lsst.sims.seeingModel.SeeingModel
        - ``scheduled_downtime`` : lsst.sims.downtimeModel.ScheduleDowntime
        - ``unscheduled_downtime`` : lsst.sims.downtimeModel.UnschedulerDowntime
    raw_telemetry: {`str`: :object:}
        Raw, as in unparsed data that is recieved over SAL. The SchedulerCSC 
        parses self.raw_telemtry and formats the data into self.models.
    driver: `lsst.ts.scheduler.driver.Driver`
        A worker class that does much of the lower level computation called by
        the SchedulerCSC.
    """
    def __init__(self, index):
        """Initialized many of the class attributes.

        The __init__ method initializes the minimal amount of setup needed for
        the SchedulerCSC to be able to change state.

        Parameters
        ----------
        index : int
            We can create multiple CSC's based from the same XML explained here
            https://confluence.lsstcorp.org/display/~aheyer/CSC+Name+Guidlines.
            This index value refers to the Enumeration value specified in the
            ts_xml/sal_interfaces/SALSubsystem.xml file. Under the Scheduler
            tag.  
        """
        self.log = logging.getLogger("SchedulerCSC")

        super().__init__(SALPY_Scheduler, index)
        self.summary_state = base_csc.State.OFFLINE

        self.parameters = SchedulerCscParameters()

        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))

        self.models = {}
        self.raw_telemetry = {}

        self.driver = None

    def do_enterControl(self, id_data):
        """Transition from `State.OFFLINE` to `State.STANDBY`.

        Parameters
        ----------
        id_data : `salobj.CommandIdData`
            Command ID and data
        """
        self._do_change_state(id_data, "enterControl", [base_csc.State.OFFLINE], base_csc.State.STANDBY)

    def begin_enterControl(self, id_data):
        """Begin do_enterControl; called before state changes.

        Parameters
        ----------
        id_data : `salobj.CommandIdData`
            Command ID and data
        """
        pass

    def end_enterControl(self, id_data):
        """End do_enterControl; called after state changes
         but before command acknowledged.

         Parameters
         ----------
         id_data : `salobj.CommandIdData`
             Command ID and data
         """
        self.send_valid_settings()  # Send valid settings once we are done

    def do_exitControl(self, id_data):
        """Transition from `State.STANDBY` to `State.OFFLINE` and quit.

        Parameters
        ----------
        id_data : `salobj.CommandIdData`
            Command ID and data
        """
        self._do_change_state(id_data, "exitControl", [base_csc.State.STANDBY], base_csc.State.OFFLINE)

    async def do_start(self, id_data):
        """Override superclass method to transition from `State.STANDBY` to `State.DISABLED`. This is the step where
        we configure the models, driver and scheduler, which can take some time. So here we acknowledge that the
        task started, start working on the configuration and then make the state transition.

        Parameters
        ----------
        id_data : `salobj.CommandIdData`
            Command ID and data
        """
        if self.summary_state != base_csc.State.STANDBY:
            raise base.ExpectedError(f"Start not allowed in state {self.summary_state}")

        settings_to_apply = id_data.data.settingsToApply

        # check settings_to_apply
        if len(settings_to_apply) == 0:
            self.log.warning("No settings selected. Using current one: %s", self.current_setting)
            settings_to_apply = self.current_setting

        is_valid = False
        for valid_setting in self.valid_settings:
            await asyncio.sleep(0)  # give control to the event loop for responsiveness
            if 'origin/%s' % settings_to_apply == valid_setting:
                is_valid = True
                break

        if not is_valid:
            raise base.ExpectedError(f"{settings_to_apply} is not a valid settings. "
                                     f"Choose one of: {self.valid_settings}.")

        self.log.debug("Configuring the scheduler with setting '%s'", settings_to_apply)

        await asyncio.sleep(0)  # give control to the event loop for responsiveness

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        await  self.run_configuration(settings_to_apply, executor)

        self._do_change_state(id_data, "start", [base_csc.State.STANDBY], base_csc.State.DISABLED)

    async def run_configuration(self, setting, executor):
        """This coroutine is responsible for executing the entire configuration set in a worker so the event loop
        will not block.

        Parameters
        ----------
        setting: str: The selected setting.
        executor: concurrent.futures.ThreadPoolExecutor: The executor where the task will run.

        Returns
        -------
        None

        """
        loop = asyncio.get_event_loop()

        # Run configure method on the executer thus, not blocking the event loop.
        await loop.run_in_executor(executor, self.configure, setting)

    @property
    def valid_settings(self):
        """Reads the branches on the configuration repo and preps them.

        Returns
        -------
        valid_setting: list(str): List of branches on the configuration repository. A single branch
            represents a valid setting.
        """

        remote_branches = []
        for ref in self.configuration_repo.git.branch('-r').split('\n'):
            if 'HEAD' not in ref:
                remote_branches.append(ref.replace(' ', ''))

        return remote_branches

    @property
    def current_setting(self):
        """str: The current setting.

        Returns
        -------
        str
            Unshortened name of the activet branch in the 
            self.configuration_path location. For ex; "origin/develop".

        """
        return str(self.configuration_repo.active_branch)

    def send_valid_settings(self):
        """Publish valid settings over SAL & return a string of valid settings.

        Returns
        -------
        str
            Comma delimited string of available Git repos withing the 
            self.configuration_path location. For ex; 
            "origin/develop,origin/master".

        """
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        # FIXME: Update to use salobj
        topic = self.evt_settingVersions.DataType()
        topic.recommendedSettingsLabels = valid_settings
        topic.recommendedSettingsVersion = self.parameters.recommended_settings_version

        self.evt_settingVersions.put(topic)

        return valid_settings

    def init_models(self):
        """Initialize but not configure needed models. 

        Returns
        -------

        """
        self.models['location'] = ObservatoryLocation()
        self.models['observatory_model'] = ObservatoryModel(self.models['location'], WORDY)
        self.models['observatory_state'] = ObservatoryState()
        self.models['sky'] = AstronomicalSkyModel(self.models['location'])
        self.models['seeing'] = SeeingModel()
        # FIXME: I'll leave cloud model out for now as we need to flush out the cloud model.
        # self.models['cloud'] = CloudModel()
        self.models['scheduled_downtime'] = ScheduledDowntime()
        self.models['unscheduled_downtime'] = UnscheduledDowntime()

        # Fixme: The list of raw telemetry should be something that the models return, plus some additional standard
        # telemetry like time.
        # Observatory Time. This is NOT observation time. Observation time will be derived from observatory time by
        # the scheduler and will aways be in the future.
        self.raw_telemetry['timeHandler'] = None
        self.raw_telemetry['observatoryState'] = None  # Observatory State
        self.raw_telemetry['bulkCloud'] = None  # Transparency measurement
        self.raw_telemetry['seeing'] = None  # Seeing measurement

    def update_telemetry(self):
        """ Update data on all the telemetry values.

        Returns
        -------
        None

        """
        pass

    def put_on_queue(self, targets, position=None):
        """ Given a list of targets, put them on the queue to be observed. By default targets are appended to the
        queue. An optional position argument is available and specify the position on the queue. Position can either
        be a single integer number or a list. If an integer, the position is considered to be for the first target on
        the list. If a list, it must have the same number of elements as targets.

        Parameters
        ----------
        targets: list(Targets): A list of targets to put on the queue.
        position: int or list(int): Position of the targets on the queue. By default (None) append to the queue.

        Returns
        -------

        """
        pass

    def configure(self, setting=None):
        """This method is responsible for configuring the scheduler models and the scheduler algorithm, given the
        input setting. It will raise an exception if the input setting is not valid.

        Parameters
        ----------
        setting: string: A valid setting from the the `read_valid_settings` method.

        Returns
        -------
        None

        """
        # Prepare configuration repository by checking out the selected setting.
        if setting is None:
            self.log.debug('Loading current setting: %s', self.current_setting)
            self.load_configuration(self.current_setting)
        else:
            self.log.debug('Loading setting: %s', setting)
            self.load_configuration(setting)

        # Now, configure modules in the proper order

        # Configuring Models
        if len(self.models) == 0:
            self.log.warning("Models are not initialized. Initializing...")
            self.init_models()

        for model in self.models:
            # TODO: This check will give us time to implement the required changes on the models.
            if hasattr(self.models[model], "parameters"):
                self.log.debug('Loading overwrite parameters for %s', model)
                load_override_configuration(self.models[model].parameters, self.configuration_path)
            else:
                self.log.warning('Model %s does not have a parameter class.' % model)

        # Configuring Driver and Scheduler

        self.configure_driver()

        self.configure_scheduler()

        # Publish settingsApplied and appliedSettingsMatchStart

        match_start_topic = self.evt_appliedSettingsMatchStart.DataType()
        match_start_topic.appliedSettingsMatchStartIsTrue = True
        self.evt_appliedSettingsMatchStart.put(match_start_topic)

        settings_applied = self.evt_settingsApplied.DataType()
        # Most configurations comes from this single commit hash. I think the other modules could host the
        # version for each one of them
        settings_applied.version = self.configuration_repo.head.object.hexsha
        settings_applied.scheduler = self.parameters.driver_type  # maybe add version?
        settings_applied.observatoryModel = obs_mod_version.__version__
        settings_applied.observatoryLocation = dateloc_version.__version__
        settings_applied.seeingModel = seeing_version.__version__
        settings_applied.cloudModel = cloud_version.__version__
        settings_applied.skybrightnessModel = astrosky_version.__version__
        settings_applied.downtimeModel = downtime_version.__version__

        self.evt_settingsApplied.put(settings_applied)

    def configure_driver(self):
        """Load driver for selected scheduler and configure its basic parameters.

        Returns
        -------

        """
        if self.driver is not None:
            self.log.warning('Driver already defined. Overwriting driver.')
            # TODO: It is probably a good idea to tell driver to save its state before overwriting. So
            # it is possible to recover.

        self.log.debug('Loading driver from %s', self.parameters.driver_type)
        driver_lib = import_module(self.parameters.driver_type)
        members_of_driver_lib = inspect.getmembers(driver_lib)

        driver_type = None
        for member in members_of_driver_lib:
            if issubclass(member[1], Driver):
                self.log.debug('Found driver %s%s', member[0], member[1])
                driver_type = member[1]
                break

        if driver_type is None:
            raise ImportError("Could not find Driver on module %s" % self.parameters.driver_type)

        self.driver = driver_type(models=self.models, raw_telemetry=self.raw_telemetry)

        # load_override_configuration(self.driver.parameters, self.configuration_path)

    def configure_scheduler(self):
        """Configure driver scheduler and publish survey topology.

        Note that driver does not pass any information to configure_scheduler. If there is any information needed
        Driver should define that on the DriverParameters, which are loaded on configure_driver().

        Returns
        -------

        """
        survey_topology = self.driver.configure_scheduler()

        # Publish topology
        self.tel_surveyTopology.put(survey_topology.to_topic(self.tel_surveyTopology.DataType()))

    def load_configuration(self, config_name):
        """Load configuration by checking out the selected branch.

        Parameters
        ----------
        config_name: str: The name of the selected configuration.

        Returns
        -------

        """

        if self.configuration_path is None:
            self.log.warning("No configuration path. Using default values.")
        else:
            valid_setting = False
            for config in self.valid_settings:
                if config_name == config[config.find('/') + 1:]:
                    self.log.debug('Loading settings: %s [%s]' % (config, config_name))
                    self.configuration_repo.git.checkout(config_name)
                    valid_setting = True
                    break
            if not valid_setting:
                self.log.warning('Setting %s not valid! Using %s' % (config_name, self.current_setting))

    def run(self):
        """ This is the method that runs when the system is in enable state. It is responsible for the target
        production loop, updating telemetry, requesting targets from the driver to build a queue and filling
        the queue with targets.

        Returns
        -------

        """
        pass
