import logging
from importlib import import_module
import inspect
import asyncio
import concurrent
import time
import traceback
from collections import namedtuple

import SALPY_Scheduler
import SALPY_ScriptQueue

from lsst.ts.salobj import base_csc, base, Remote

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

NO_QUEUE = 300
"""Could not connect to the queue (`int`).

This error code is published in `SALPY_Scheduler.Scheduler_logevent_errorCodeC` if the Scheduler CSC 
can not connect to the queue. 
"""
PUT_ON_QUEUE = 301
"""Failed to put target on the queue (`int`).

This error code is published in `SALPY_Scheduler.Scheduler_logevent_errorCodeC` if the Scheduler CSC 
fails to put a target (or targets) in the queue. 
"""
SIMPLE_LOOP_ERROR = 400
"""Unspecified error on the simple target generation loop (`int`).

This error code is published in `SALPY_Scheduler.Scheduler_logevent_errorCodeC` if there is an
unspecified error while running the simple target generation loop. For instance, if a user defined
scheduling algorithm throws an exception after a call to `Driver.select_next_target` this error 
code will, most likely, be issued (along with the traceback message).
"""

NonFinalStates = frozenset((SALPY_ScriptQueue.script_Loading,
                            SALPY_ScriptQueue.script_Configured,
                            SALPY_ScriptQueue.script_Running))
"""Stores a non final state for scripts submitted to the queue.
"""


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
                                                     "change next target up to a certain lead time.",
                                          "DRY": "Once the Scheduler is enabled it won't do anything. Useful for"
                                                 "testing",
                                          })
    n_targets = pexConfig.Field('Number of targets to put in the queue ahead of time.', int, default=1)
    predicted_scheduler_window = pexConfig.Field('Size of predicted scheduler window, in hours.', float, default=2.)
    loop_sleep_time = pexConfig.Field('How long should the target production loop wait when there is '
                                      'a wait event. Unit = seconds.', float, default=1.)
    cmd_timeout = pexConfig.Field('Global command timeout. Unit = seconds.', float, default=60.)
    observing_script = pexConfig.Field("Name of the observing script.", str, default='standard_visit.py')
    observing_script_is_standard = pexConfig.Field("Is observing script standard?", bool, default=True)
    max_scripts = pexConfig.Field('Maximum number of scripts to keep track of.', int, default=100)

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
        self.loop_sleep_time = 1.
        self.cmd_timeout = 60.
        self.observing_script = 'standard_visit.py'
        self.observing_script_is_standard = True
        self.max_scripts = 100


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
            tag. The scheduler will create a remote to communicate with the queue
            with the same index.
        """
        self.log = logging.getLogger("SchedulerCSC")

        super().__init__(SALPY_Scheduler, index)

        # Communication channel with OCS queue.
        self.queue_remote = Remote(SALPY_ScriptQueue, index)

        self.parameters = SchedulerCscParameters()

        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))

        self.models = {}
        self.raw_telemetry = {}
        self.script_info = {}  # Dictionary to store information about the scripts put on the queue

        self.driver = None

        self.target_production_task = None  # Stores the coroutine for the target production.
        self.run_loop = False  # A flag to indicate that the event loop is running

        # Add callback to script info
        self.queue_remote.evt_script.callback = self.callback_script_info

        # Publish valid settings
        self.send_valid_settings()

    async def end_standby(self, id_data):
        """End do_standby.

        Called after state transition from `State.DISABLED` or `State.FAULT` to `State.STANDBY`
        but before command acknowledged.

        Parameters
        ----------
        id_data : `CommandIdData`
            Command ID and data
         """
        self.send_valid_settings()  # Send valid settings

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

    async def begin_enable(self, id_data):
        """Begin do_enable.

        Called before state transition from `State.DISABLED` to `State.ENABLED`. This method will
        start the selected target production loop (SIMPLE, ADVANCED or DRY) or raise an exception if
        the mode is unrecognized.

        Parameters
        ----------
        id_data : `CommandIdData`
            Command ID and data
        """

        if self.parameters.mode == 'SIMPLE':

            self.target_production_task = asyncio.ensure_future(self.simple_target_production_loop())

        elif self.parameters.mode == 'ADVANCE':

            self.target_production_task = None
            # This will just reject the command
            raise NotImplementedError('ADVANCE target production loop not implemented.')

        elif self.parameters.mode == 'DRY':

            self.target_production_task = None

        else:
            # This will just reject the command
            raise IOError("Unrecognized scheduler mode %s" % self.parameters.mode)

    async def do_disable(self, id_data):
        """Transition to from `State.ENABLED` to `State.DISABLED`. This transition will be made in a gentle way,
        meaning that it will wait for the target production loop to finalize before making the transition. If a more
        drastic approach is need, the scheduler must be sent to `State.FAULT` with an `abort` command.

        Parameters
        ----------
        id_data : `CommandIdData`
            Command ID and data
        """
        if self.target_production_task is None:
            # Nothing to do, just transition
            self._do_change_state(id_data, "disable", [base_csc.State.ENABLED], base_csc.State.DISABLED)
            self.log.debug('No target production loop running.')
        else:
            # need to cancel target production task before changing state. Note if we are here we must be in
            # enable state. The target production task should always be None if we are not enabled.
            # self.target_production_task.cancel()
            self.log.log(WORDY, 'Setting run loop flag to False and waiting for target loop to finish...')
            self.run_loop = False  # Will set flag to False so the loop will stop at the earliest convenience
            wait_start = time.time()
            while not self.target_production_task.done():
                await asyncio.sleep(self.parameters.loop_sleep_time)
                elapsed = time.time() - wait_start
                self.log.log(WORDY, 'Waiting target loop to finish (elapsed: %.2f s, timeout: %.2f s)...',
                             elapsed,
                             self.parameters.cmd_timeout)
                if elapsed > self.parameters.cmd_timeout:
                    self.log.warning('Target loop not stopping, cancelling it...')
                    self.target_production_task.cancel()
                    break

            try:
                await self.target_production_task
            except asyncio.CancelledError:
                self.log.info('Target production task cancelled...')
            except Exception as e:
                # Something else may have happened. I still want to disable as this will stop the loop on the
                # target production
                self.log.exception(e)
            finally:
                self._do_change_state(id_data, "disable", [base_csc.State.ENABLED], base_csc.State.DISABLED)
                self.target_production_task = None

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
        self.log.log(WORDY, 'Updating telemetry stream.')
        pass

    async def put_on_queue(self, targets):
        """Given a list of targets, append them on the queue to be observed. Each target
        sal_index attribute is updated with the unique identifier value (salIndex) returned
        by the queue.


        Parameters
        ----------
        targets: list(Targets): A list of targets to put on the queue.

        """

        for target in targets:
            load_script_topic = self.queue_remote.cmd_add.DataType()
            load_script_topic.path = self.parameters.observing_script
            load_script_topic.config = target.get_script_config()
            load_script_topic.isStandard = self.parameters.observing_script_is_standard
            load_script_topic.location = SALPY_ScriptQueue.add_Last

            self.log.log(WORDY, 'Putting target %i on the queue', target.targetid)
            add_task = await self.queue_remote.cmd_add.start(load_script_topic,
                                                             timeout=self.parameters.cmd_timeout)

            self.evt_target.put(target.as_evt_topic())  # publishes target event

            target.sal_index = int(add_task.ack.result)

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

    async def get_queue(self, request=True):
        """Utility method to get the queue.


        Parameters
        ----------
        request: bool
            Issue request for queue state?

        Returns
        -------
        queue: SALPY_ScriptQueue.ScriptQueue_logevent_queueC
            SAL Topic with information about the queue.

        """

        self.log.log(WORDY, 'Getting queue.')

        queue_coro = self.queue_remote.evt_queue.next(flush=True,
                                                      timeout=self.parameters.cmd_timeout)

        try:
            if request:
                topic = self.queue_remote.cmd_showQueue.DataType()
                request_queue = await self.queue_remote.cmd_showQueue.start(topic,
                                                                            timeout=self.parameters.cmd_timeout)
            try:
                queue = await queue_coro
            except asyncio.TimeoutError as e:
                self.log.error('No state from queue. Requesting...')
                queue_coro = self.queue_remote.evt_queue.next(flush=True,
                                                              timeout=self.parameters.cmd_timeout)
                topic = self.queue_remote.cmd_showQueue.DataType()
                request_queue = await self.queue_remote.cmd_showQueue.start(topic,
                                                                            timeout=self.parameters.cmd_timeout)
                queue = await queue_coro

        except base.AckError as e:
            self.log.error('No response from queue...')
            error_topic = self.evt_errorCode.DataType()
            error_topic.errorCode = NO_QUEUE
            error_topic.errorReport = 'Error no response from queue.'
            error_topic.traceback = traceback.format_exc()
            self.evt_errorCode.put(error_topic)
            self.summary_state = base_csc.State.FAULT
            raise e
        else:
            return queue

    async def check_scheduled(self):
        """ Loop through the scheduled targets list, check status and tell driver of completed observations.

        Returns
        -------
        bool
            `True` if all checked scripts where Done or in non-final state. `False` if no scheduled targets to check or
            if one or more scripts ended up a failed or unrecognized state.

        """
        ntargets = len(self.raw_telemetry['scheduled_targets'])

        if ntargets == 0:
            self.log.log(WORDY, 'No scheduled targets to check.')
            return False

        self.log.log(WORDY, 'Checking %i scheduled targets', ntargets)

        retval = True
        for i in range(ntargets):
            target = self.raw_telemetry['scheduled_targets'].pop(0)
            if target.sal_index in self.script_info:
                info = self.script_info[target.sal_index]
            else:
                # No information on script on queue, put it back and continue
                self.raw_telemetry['scheduled_targets'].append(target)
                continue

            if info.processState == SALPY_ScriptQueue.script_Done:
                # Script completed I'll assume the observation was successful.
                # TODO: Need to make sure script completed successfully. Can use scriptState from info as a first guess
                # FIXME: we probably need to get updated information about the observed target
                self.driver.register_observation(target)

                # Remove related script from the list
                del self.script_info[target.sal_index]
                # target now simply disappears... Should I keep it in for future refs?
            elif info.processState in NonFinalStates:
                # script in a non-final state, just put it back on the list.
                self.raw_telemetry['scheduled_targets'].append(target)
            elif info.processState == SALPY_ScriptQueue.script_ConfigureFailed:
                self.log.warning('Failed to configure observation for target %s.', target.sal_index)
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False
            elif info.processState == SALPY_ScriptQueue.script_Terminated:
                self.log.warning('Observation for target %s terminated.', target.sal_index)
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False
            else:
                self.log.error('Unrecognized state [%i] for observation %i for target %s.',
                               info.processState,
                               target.sal_index,
                               target)
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False

        return retval

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

        """

        self.run_loop = True
        self.raw_telemetry['scheduled_targets'] = []

        loop = asyncio.get_event_loop()

        first_pass = True
        while self.summary_state == base_csc.State.ENABLED and self.run_loop:
            try:
                # If it is the first pass get the current queue, otherwise wait for the queue to change
                # or get the latest if there's some
                # if first_pass:
                #     queue = self.queue_remote.evt_queue.get()
                # else:
                #     queue = await self.queue_remote.evt_queue.next(flush=False)
                queue = await self.get_queue(first_pass)

                # This return False if script failed, in which case next pass won't wait for queue to change
                first_pass = not await self.check_scheduled()

                # Only send targets to queue if it is running, empty and there is nothing executing
                if queue.running and queue.currentSalIndex == 0 and queue.length == 0:
                    # TODO: publish detailed state indicating that the scheduler is selecting a target

                    self.log.log(WORDY, 'Queue ready to receive targets.')

                    await loop.run_in_executor(None, self.update_telemetry)

                    target = await loop.run_in_executor(None, self.driver.select_next_target)

                    # This method receives a list of targets and return a list of script ids
                    await self.put_on_queue([target])

                    if target.sal_index > 0:
                        self.raw_telemetry['scheduled_targets'].append(target)
                    else:
                        self.log.error('Could not add target to the queue: %s', target)
                        error_topic = self.evt_errorCode.DataType()
                        error_topic.errorCode = PUT_ON_QUEUE
                        error_topic.errorReport = f'Could not add target to the queue: {target}'
                        self.evt_errorCode.put(error_topic)
                        self.summary_state = base_csc.State.FAULT

                    # TODO: publish detailed state indicating that the scheduler has finished the target selection

                else:
                    # TODO: Publish detailed state indicating that the scheduler is waiting.
                    self.log.log(WORDY, 'Queue state: [Running:%s][Executing:%s][Empty:%s]',
                                 queue.running == 1,
                                 queue.currentSalIndex != 0,
                                 queue.length == 0)
                    await asyncio.sleep(self.parameters.loop_sleep_time)
            except Exception as e:
                # If there is an exception go to FAULT state, log the exception and break the loop
                error_topic = self.evt_errorCode.DataType()
                error_topic.errorCode = SIMPLE_LOOP_ERROR
                error_topic.errorReport = 'Error on simple target production loop.'
                error_topic.traceback = traceback.format_exc()
                self.evt_errorCode.put(error_topic)

                self.summary_state = base_csc.State.FAULT
                self.log.exception(e)
                break

    def callback_script_info(self, data):
        """This callback function will store in a dictionary information about the scripts.

        The method will store information about any script that is placed in the queue so that the
        scheduler can access information about those if needed. It then, tracks the size of the
        dictionary where this information is stored and deletes them appropriately. Also,
        note that the scripts are removed if they where created by the scheduler and
        are in a final state when `self.check_scheduled()` is called.
        """

        # This method implements a workaround an issue with SAL where Python cannot create
        # copies of topics. So instead, it parse the topic into a named tuple so it is possible
        # to access the data the same way if the topic itself was stored.
        content = {}
        for item in dir(data):
            if not item.startswith('__'):
                content[item] = getattr(data, item)
        Topic = namedtuple("Topic", content)

        self.script_info[data.salIndex] = Topic(**content)

        # Make sure the size of script info is smaller then the maximum allowed
        script_info_size = len(self.script_info)
        if script_info_size > self.parameters.max_scripts:
            self.log.log(WORDY, "Cleaning up script info database.")
            # Removes old entries
            for key in self.script_info:
                del self.script_info[key]
                if len(self.script_info) < self.parameters.max_scripts:
                    break
