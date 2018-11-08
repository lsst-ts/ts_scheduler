import logging
from importlib import import_module
import inspect
import asyncio
import concurrent
import time

from salobj import base_csc, base, Remote
import SALPY_Scheduler
import SALPY_ScriptQueue

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

from .base_script import ScriptState

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
    mode = pexConfig.ChoiceField("The mode of operation of the scheduler. This basically chooses one of the available "
                                 "target production loops. ",
                                 str,
                                 default='SIMPLE',
                                 allowed={"SIMPLE": "The Scheduler will publish one target at a time, no next target"
                                                    "published in advance and no predicted schedule.",
                                          "ADVANCE": "The Scheduler will pre-compute a predicted schedule"
                                                     "that is published as an event and will fill the queue"
                                                     "with a specified number of targets. The scheduler will "
                                                     "then monitor the telemetry stream, recompute the queue and"
                                                     "change next target up to a certain lead time.", })
    n_targets = pexConfig.Field('Number of targets to put in the queue ahead of time.', int, default=1)
    predicted_scheduler_window = pexConfig.Field('Size of predicted scheduler window, in hours.', float, default=2.)
    loop_sleep_time = pexConfig.Field('How long should the target production loop wait when there is '
                                      'a wait event. Unit = seconds.', float, default=0.05)
    observing_script = pexConfig.Field("Name of the observing script.", str, default='standard_visit.py')
    observing_script_is_standard = pexConfig.Field("Is observing script standard?", bool, default=True)

    def setDefaults(self):
        """Set defaults for the LSST Scheduler's Driver.
        """
        self.recommended_settings_version = 'master'
        self.driver_type = 'lsst.ts.scheduler.driver'
        self.night_boundary = -12.0
        self.new_moon_phase_threshold = 20.0
        self.startup_type = 'HOT'
        self.startup_database = ''
        self.mode = 'SIMPLE'
        self.n_targets = 1
        self.predicted_scheduler_window = 2.
        self.loop_sleep_time = 0.05
        self.observing_script = 'standard_visit.py'
        self.observing_script_is_standard = True


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

        # Communication channel with OCS queue. This must probably be indexed as we will have a queue for the
        # main telescope and one for auxtel.
        self.queue_remote = Remote(SALPY_ScriptQueue)

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
        self.raw_telemetry['scheduled_targets'] = None  # List of scheduled targets and script ids
        self.raw_telemetry['observing_queue'] = None  # List of things on the observatory queue
        self.raw_telemetry['observatoryState'] = None  # Observatory State
        self.raw_telemetry['bulkCloud'] = None  # Transparency measurement
        self.raw_telemetry['seeing'] = None  # Seeing measurement
        self.raw_telemetry['seeing'] = None  # Seeing measurement

    def update_telemetry(self):
        """ Update data on all the telemetry values.

        Returns
        -------
        None

        """
        pass

    async def put_on_queue(self, targets, position=None):
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
        script_indexes : list(int)
            The list of script indexes.

        """

        script_ids = []

        for target in targets:
            load_script_topic = self.queue_remote.cmd_add.DataType()
            load_script_topic.path = self.parameters.observing_script
            load_script_topic.config = target.to_json()
            load_script_topic.isStandard = self.parameters.observing_script_is_standard
            load_script_topic.location = 2  # should be last

            script_info_coro = self.queue_remote.evt_script.next(timeout=1.)

            add_task = await self.queue_remote.cmd_add.start(load_script_topic)

            if add_task.ack.ack != self.queue_remote.salinfo.lib.SAL__CMD_COMPLETE:
                raise IOError("Could not put target on queue.")

            script_info = await script_info_coro

            # Need to get salIndex for the script that I just created

            # Check that the script I received was generated by my add command
            if script_info.cmdId != add_task.cmd_id:
                self.log.warning('Received script info not from expected script. Searching the queue...')
                # If the received event does not match the command sent, grab the entire queue and check all items
                # on it
                script_found = False
                queue = await self.get_queue()

                # Looking at the queue
                for i in range(queue.length):
                    info = await self.get_script_info(queue.salIndices[i])
                    if info.cmdId == add_task.cmd_id:
                        script_found = True
                        script_ids.append(info.salIndex)
                        break

                if script_found:
                    continue

                # Looking at the currently running script
                info = await self.get_script_info(queue.currentSalIndex)
                if info.cmdId == add_task.cmd_id:
                    script_ids.append(info.salIndex)
                    continue

                # Last resort, looking at the past queue (very unlikely)
                for i in range(queue.pastLength):
                    info = await self.get_script_info(queue.pastSalIndices[i])
                    if info.cmdId == add_task.cmd_id:
                        script_found = True
                        script_ids.append(info.salIndex)
                        break

                if not script_found:
                    script_ids.append(-1)

            else:
                script_ids.append(script_info.salIndex)

        return script_ids

    async def get_script_info(self, index):
        """

        Parameters
        ----------
        index

        Returns
        -------

        """
        info_coro = self.queue_remote.evt_script.next(timeout=10.)
        topic = self.queue_remote.cmd_showScript.DataType()
        topic.salIndex = index
        await self.queue_remote.cmd_showScript.start(topic)
        return await info_coro

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

    async def get_queue(self):
        """Utility method to get the queue.

        Returns
        -------
        queue: SALPY_ScriptQueue.ScriptQueue_logevent_queueC
            SAL Topic with information about the queue.
        """

        queue_coro = self.queue_remote.evt_queue.next(timeout=10.)

        request_queue = await self.queue_remote.cmd_showQueue.start(self.queue_remote.cmd_showQueue.DataType())

        if request_queue.ack.ack != self.queue_remote.salinfo.lib.SAL__CMD_COMPLETE:
            raise IOError("Could not get queue.")

        return await queue_coro

    def check_scheduled(self):
        """ Loop through the target list and tell driver of completed observations.

        Returns
        -------

        """
        ntargets = len(self.raw_telemetry['scheduled_targets'])

        for i in range(ntargets):
            check = self.raw_telemetry['scheduled_targets'].pop(0)
            state = self.get_script_execution(check)
            if state == self.queue_remote.salinfo.lib.script_Complete:
                # Script completed I'll assume the observation was successful. Need to make sure
                # this is accurate.
                # FIXME: we probably need to get updated information about the observed target
                self.driver.register_observation(check[0])
                # target now simply disappears... Should I keep it in for future refs?
            elif state == self.queue_remote.salinfo.lib.script_Failed or \
                    state == self.queue_remote.salinfo.lib.script_Terminated:
                # Script completed with errors, will remove from list and will not register
                continue
            else:
                # script in a non-final state, just put it back on the list.
                self.raw_telemetry['scheduled_targets'].append(check)

    async def simple_target_production_loop(self):
        """ This coroutine implements the simple target production loop. It will query the status of the queue and,
        if there is nothing running, it will add an observation to the back of the queue. Once Scheduler is enabled
        with simple mode, this coroutine will be added to the event loop as a future. While running it will checking
        the queue and put targets to it. If the queue is paused or there is a running script, it will not add any
        target to it. If the Scheduler is disabled this method will be cancelled.

        Also, note that the target production loop does not care about if it is day or night. It is up to the
        scheduling algorithm to decide whether there is something to observe or not given the input telemetry. A
        target produced by the scheduler can have a start time. In this case, the task will be sent to the queue
        and it is up to the queue or the running script to wait for the specified time. If the scheduling algorithm
        does not produce any target, then the Scheduler will keep updating telemetry and requesting targets until
        something is returned to be executed.

        NOTE: This method may either run in the main event loop or in an event loop of a thread. If it is the first
        case, we need to make sure long running tasks are sent to a thread or a process. If the latter, then it
        should be ok to simple execute long running tasks and block the thread event loop.

        Returns
        -------

        """

        self.raw_telemetry['scheduled_targets'] = []

        while True:
            try:
                self.check_scheduled()

                queue = await self.get_queue()

                # Only send targets to queue if it is running, empty and there is nothing executing
                if queue.running and queue.currentSalIndex == 0 and queue.length == 0:
                    # TODO: publish detailed state indicating that the scheduler is selecting a target

                    self.update_telemetry()  # This call will block the event loop for a significant time
                    target = self.driver.select_next_target()  # This call will block the event loop

                    # This method receives a list of targets and return a list of script ids
                    scriptid = await self.put_on_queue([target])

                    if scriptid[0] > 0:
                        self.raw_telemetry['scheduled_targets'].append((target, scriptid[0]))
                    else:
                        self.log.debug('Could not add target to the queue: %s', target)

                    # TODO: publish detailed state indicating that the scheduler has finished the target selection

                else:
                    # TODO: Publish detailed state indicating that the scheduler is waiting.
                    await asyncio.sleep(self.parameters.loop_sleep_time)
            except Exception as e:
                # If there is an exception go to FAULT state, log the exception and break the loop
                self.summary_state = base_csc.State.FAULT
                # TODO: publish detailed state with information on the error?
                self.log.exception(e)
                break
