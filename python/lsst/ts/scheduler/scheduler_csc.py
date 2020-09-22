import logging
import pathlib
from importlib import import_module
import inspect
import asyncio
import time
import traceback

from lsst.ts import salobj
from lsst.ts.idl.enums import ScriptQueue

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
from lsst.sims.downtimeModel import DowntimeModel
from lsst.sims.downtimeModel import version as downtime_version

import lsst.pex.config as pex_config

__all__ = ["SchedulerCSC", "SchedulerCscParameters"]

NO_QUEUE = 300
"""Could not connect to the queue (`int`).

This error code is published in `Scheduler_logevent_errorCodeC` if the
Scheduler CSC can not connect to the queue.
"""
PUT_ON_QUEUE = 301
"""Failed to put target on the queue (`int`).

This error code is published in `Scheduler_logevent_errorCodeC` if the
Scheduler CSC fails to put a target (or targets) in the queue.
"""
SIMPLE_LOOP_ERROR = 400
"""Unspecified error on the simple target generation loop (`int`).

This error code is published in `Scheduler_logevent_errorCodeC` if there is an
unspecified error while running the simple target generation loop. For
instance, if a user defined scheduling algorithm throws an exception after a
call to `Driver.select_next_target` this error code will, most likely, be
issued (along with the traceback message).
"""

NonFinalStates = frozenset(
    (
        ScriptQueue.ScriptProcessState.LOADING.value,
        ScriptQueue.ScriptProcessState.CONFIGURED.value,
        ScriptQueue.ScriptProcessState.RUNNING.value,
    )
)
"""Stores all non final state for scripts submitted to the queue.
"""


class SchedulerCscParameters(pex_config.Config):
    """Configuration of the LSST Scheduler's Model.
    """

    driver_type = pex_config.Field(
        "Choose a driver to use. This should be an import string that "
        "is passed to `importlib.import_module()`. Model will look for "
        "a subclass of Driver class inside the module.",
        str,
        default="lsst.ts.scheduler.driver.driver",
    )
    night_boundary = pex_config.Field(
        "Solar altitude (degrees) when it is considered night.", float
    )
    new_moon_phase_threshold = pex_config.Field(
        "New moon phase threshold for swapping to dark " "time filter.", float
    )
    startup_type = pex_config.ChoiceField(
        "The method used to startup the scheduler.",
        str,
        default="HOT",
        allowed={
            "HOT": "Hot start, this means the scheduler is " "started up from scratch",
            "WARM": "Reads the scheduler state from a "
            "previously saved internal state.",
            "COLD": "Rebuilds scheduler state from " "observation database.",
        },
    )
    startup_database = pex_config.Field(
        "Path to the file holding scheduler state or observation "
        "database to be used on WARM or COLD start.",
        str,
        default="",
    )
    mode = pex_config.ChoiceField(
        "The mode of operation of the scheduler. This basically chooses "
        "one of the available target production loops. ",
        str,
        default="SIMPLE",
        allowed={
            "SIMPLE": "The Scheduler will publish one target at a "
            "time, no next target published in advance "
            "and no predicted schedule.",
            "ADVANCE": "The Scheduler will pre-compute a predicted "
            "schedule that is published as an event and "
            "will fill the queue with a specified "
            "number of targets. The scheduler will then "
            "monitor the telemetry stream, recompute the "
            "queue and change next target up to a "
            "certain lead time.",
            "DRY": "Once the Scheduler is enabled it won't do "
            "anything. Useful for testing",
        },
    )
    n_targets = pex_config.Field(
        "Number of targets to put in the queue ahead of time.", int, default=1
    )
    predicted_scheduler_window = pex_config.Field(
        "Size of predicted scheduler window, in hours.", float, default=2.0
    )
    loop_sleep_time = pex_config.Field(
        "How long should the target production loop wait when "
        "there is a wait event. Unit = seconds.",
        float,
        default=1.0,
    )
    cmd_timeout = pex_config.Field(
        "Global command timeout. Unit = seconds.", float, default=60.0
    )
    observing_script = pex_config.Field(
        "Name of the observing script.", str, default="standard_visit.py"
    )
    observing_script_is_standard = pex_config.Field(
        "Is observing script standard?", bool, default=True
    )
    max_scripts = pex_config.Field(
        "Maximum number of scripts to keep track of.", int, default=100
    )

    def set_defaults(self):
        """Set defaults for the LSST Scheduler's Driver.
        """
        self.driver_type = "lsst.ts.scheduler.driver.driver"
        self.startup_type = "HOT"
        self.startup_database = ""
        self.mode = "SIMPLE"
        self.n_targets = 1
        self.predicted_scheduler_window = 2.0
        self.loop_sleep_time = 1.0
        self.cmd_timeout = 60.0
        self.observing_script = "standard_visit.py"
        self.observing_script_is_standard = True
        self.max_scripts = 100


class SchedulerCSC(salobj.ConfigurableCsc):
    """This class is a reactive component which is SAL aware and delegates
    work.

    The SchedulerCSC is the only layer that is exposed to SAL communication.
    All commands recieved are by the SchedulerCSC then delegated to the
    responsible objects. Along with this the SchedulerCSC maintains a
    statemachine which is taken care of by the inherited class
    `base_csc.BaseCsc`.

    Attributes
    ----------
    log : logging.Log
        Logging mechanism for the SchedulerCSC.
    summary_state : `salobj.base_csc.State`
        Enume type, OFFLINE = 4 STANDBY = 5 DISABLED = 1 ENABLED = 2 FAULT = 3.
    parameters: `lsst.ts.scheduler.scheduler_csc.SchedulerCscParameters`
        Object to contain parameter values to configure the SchedulerCSC.
    configuration_path: `str`
        Absolute path to the configuration location for the validSettings
        event.
    configuration_repo: `str`
        String of comma delimated Git repos that exist at configuration_path.
        ex; "origin/master,origin/develop"
    valid_settings: `list` of `str`
        Shortened and listed names of configuration_repo.
        ex; [master, develop].
    models: `dict`
        Dictionary of the models necessary for the SchedulerCSC to fulfill SAL
        commands.
        - `location` : lsst.ts.datelo.ObservatoryLocation
        - `observatory_model` : lsst.ts.observatory.model.ObservatoryModel
        - `observatory_state` : lsst.ts.observatory.model.ObservatoryState
        - `sky` : lsst.ts.astrosky.model.AstronomicalSkyModel
        - `seeing` : lsst.sims.seeingModel.SeeingModel
        - `scheduled_downtime` : lsst.sims.downtimeModel.ScheduleDowntime
        - `unscheduled_downtime` : lsst.sims.downtimeModel.UnschedulerDowntime
    raw_telemetry: {`str`: :object:}
        Raw, as in unparsed data that is recieved over SAL. The SchedulerCSC
        parses self.raw_telemtry and formats the data into self.models.
    driver: `lsst.ts.scheduler.driver.Driver`
        A worker class that does much of the lower level computation called by
        the SchedulerCSC.
    """

    def __init__(
        self, index, config_dir=None, initial_state=salobj.base_csc.State.STANDBY
    ):
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
            tag. The scheduler will create a remote to communicate with the
            queue with the same index.
        """
        schema_path = (
            pathlib.Path(__file__).parents[4].joinpath("schema", "Scheduler.yaml")
        )

        super().__init__(
            name="Scheduler",
            schema_path=schema_path,
            config_dir=config_dir,
            index=index,
            initial_state=initial_state,
            simulation_mode=0,
        )

        # Communication channel with OCS queue.
        self.queue_remote = salobj.Remote(self.domain, "ScriptQueue", index=index)

        self.parameters = SchedulerCscParameters()

        # How long to wait for target loop to stop before killing it
        self.loop_die_timeout = 5.0

        self.models = {}
        self.raw_telemetry = {}
        self.script_info = (
            {}
        )  # Dictionary to store information about the scripts put on the queue

        self.driver = None

        self.target_production_task = (
            None  # Stores the coroutine for the target production.
        )
        self.run_loop = False  # A flag to indicate that the event loop is running

        # Add callback to script info
        self.queue_remote.evt_script.callback = self.callback_script_info

    # async def begin_start(self, id_data):
    #     """Override superclass method to transition from `State.STANDBY` to
    #     `State.DISABLED`. This is the step where we configure the models,
    #     driver and scheduler, which can take some time. So here we
    # acknowledge
    #     that the task started, start working on the configuration and then
    # make
    #     the state transition.
    #
    #     Parameters
    #     ----------
    #     id_data : `salobj.CommandIdData`
    #         Command ID and data
    #     """
    #     settings_to_apply = id_data.settingsToApply
    #
    #     # check settings_to_apply
    #     if len(settings_to_apply) == 0:
    #         self.log.warning("No settings selected. Using current one: %s",
    #  self.current_setting)
    #         settings_to_apply = self.current_setting
    #
    #     is_valid = False
    #     for valid_setting in self.valid_settings:
    #         await asyncio.sleep(0)  # give control to the event loop for
    # responsiveness
    #         if 'origin/%s' % settings_to_apply == valid_setting:
    #             is_valid = True
    #             break
    #
    #     if not is_valid:
    #         raise salobj.ExpectedError(f"{settings_to_apply} is not a valid
    # settings. "
    # f"Choose one of: {self.valid_settings}.")
    #
    #     self.log.debug("Configuring the scheduler with setting '%s'",
    # settings_to_apply)
    #
    #     await asyncio.sleep(0)  # give control to the event loop for
    # responsiveness
    #
    #     executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    #
    #     await self.run_configuration(settings_to_apply, executor)

    async def begin_enable(self, id_data):
        """Begin do_enable.

        Called before state transition from `State.DISABLED` to
        `State.ENABLED`. This method will start the selected target production
        loop (SIMPLE, ADVANCED or DRY) or raise an exception if the mode is
        unrecognized.

        Parameters
        ----------
        id_data : `CommandIdData`
            Command ID and data
        """

        if self.parameters.mode == "SIMPLE":

            self.target_production_task = asyncio.create_task(
                self.simple_target_production_loop()
            )

        elif self.parameters.mode == "ADVANCE":

            self.target_production_task = None
            # This will just reject the command
            raise NotImplementedError(
                "ADVANCE target production loop not " "implemented."
            )

        elif self.parameters.mode == "DRY":

            self.target_production_task = None

        else:
            # This will just reject the command
            raise IOError("Unrecognized scheduler mode %s" % self.parameters.mode)

    async def begin_disable(self, id_data):
        """Transition from `State.ENABLED` to `State.DISABLED`. This
        transition will be made in a gentle way, meaning that it will wait for
        the target production loop to finalize before making the transition.
        If a more drastic approach is need, the scheduler must be sent to
        `State.FAULT` with an `abort` command.

        Parameters
        ----------
        id_data : `CommandIdData`
            Command ID and data
        """
        try:
            if self.target_production_task is None:
                # Nothing to do, just transition
                self.log.warning("No target production loop running.")
            else:
                # need to cancel target production task before changing state.
                # Note if we are here we must be in enable state. The target
                # production task should always be None if we are not enabled.
                # self.target_production_task.cancel()
                self.log.debug(
                    "Setting run loop flag to False and waiting for "
                    "target loop to finish..."
                )
                # Will set flag to False so the loop will stop at the earliest
                # convenience
                self.run_loop = False
                wait_start = time.time()
                while not self.target_production_task.done():
                    await asyncio.sleep(self.parameters.loop_sleep_time)
                    elapsed = time.time() - wait_start
                    self.log.debug(
                        f"Waiting target loop to finish (elapsed: {elapsed} s, "
                        f"timeout: {self.parameters.cmd_timeout} s)..."
                    )
                    if elapsed > self.loop_die_timeout:
                        self.log.warning("Target loop not stopping, cancelling it...")
                        self.target_production_task.cancel()
                        break

                try:
                    await self.target_production_task
                except asyncio.CancelledError:
                    self.log.info("Target production task cancelled...")
                except Exception as e:
                    # Something else may have happened. I still want to
                    # disable as this will stop the loop on the
                    # target production
                    self.log.exception(e)
                finally:
                    self.target_production_task = None
        except Exception as e:
            self.target_production_task = None
            self.log.exception(e)

    # async def run_configuration(self, setting, executor):
    #     """This coroutine is responsible for executing the entire
    #     configuration set in a worker so the event loop will not block.
    #
    #     Parameters
    #     ----------
    #     setting: str: The selected setting.
    #     executor: concurrent.futures.ThreadPoolExecutor: The executor where
    #     the task will run.
    #
    #     """
    #     loop = asyncio.get_event_loop()
    #
    #     # Run configure method on the executer thus, not blocking the event
    #     # loop.
    #     await loop.run_in_executor(executor, self.configure, setting)

    def init_models(self):
        """Initialize but not configure needed models.

        Returns
        -------

        """
        self.models["location"] = ObservatoryLocation()
        self.models["observatory_model"] = ObservatoryModel(
            self.models["location"], logging.DEBUG
        )
        self.models["observatory_state"] = ObservatoryState()
        self.models["sky"] = AstronomicalSkyModel(self.models["location"])
        self.models["seeing"] = SeeingModel()
        self.models["cloud"] = CloudModel()
        self.models["downtime"] = DowntimeModel()

        # FIXME: The list of raw telemetry should be something that the models
        # return, plus some additional standard telemetry like time.
        # Observatory Time. This is NOT observation time. Observation time
        # will be derived from observatory time by the scheduler and will
        # aways be in the future.
        self.raw_telemetry["timeHandler"] = None
        self.raw_telemetry[
            "scheduled_targets"
        ] = None  # List of scheduled targets and script ids
        self.raw_telemetry[
            "observing_queue"
        ] = None  # List of things on the observatory queue
        self.raw_telemetry["observatoryState"] = None  # Observatory State
        self.raw_telemetry["bulkCloud"] = None  # Transparency measurement
        self.raw_telemetry["seeing"] = None  # Seeing measurement
        self.raw_telemetry["seeing"] = None  # Seeing measurement

    def update_telemetry(self):
        """ Update data on all the telemetry values.

        Returns
        -------
        None

        """
        self.log.debug("Updating telemetry stream.")
        pass

    async def put_on_queue(self, targets):
        """Given a list of targets, append them on the queue to be observed.
        Each target sal_index attribute is updated with the unique identifier
        value (salIndex) returned by the queue.


        Parameters
        ----------
        targets: list(Targets): A list of targets to put on the queue.

        """

        for target in targets:
            self.queue_remote.cmd_add.set(
                path=self.parameters.observing_script,
                config=target.get_script_config(),
                isStandard=self.parameters.observing_script_is_standard,
                location=ScriptQueue.Location.LAST,
            )

            self.log.debug(f"Putting target {target.targetid} on the queue.")
            add_task = await self.queue_remote.cmd_add.start(
                timeout=self.parameters.cmd_timeout
            )

            self.evt_target.set_put(**target.as_evt_topic())  # publishes target event

            target.sal_index = int(add_task.result)

    @staticmethod
    def get_config_pkg():
        return "ts_config_ocs"

    async def configure(self, config):
        """This method is responsible for configuring the scheduler models and
        the scheduler algorithm, given the input setting. It will raise an
        exception if the input setting is not valid.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        None

        """
        self.parameters.driver_type = config.driver_type
        self.parameters.startup_type = config.startup_type
        self.parameters.startup_database = config.startup_database
        self.parameters.mode = config.mode
        self.parameters.n_targets = config.n_targets
        self.parameters.predicted_scheduler_window = config.predicted_scheduler_window
        self.parameters.loop_sleep_time = config.loop_sleep_time
        self.parameters.cmd_timeout = config.cmd_timeout
        self.parameters.observing_script = config.observing_script
        self.parameters.observing_script_is_standard = (
            config.observing_script_is_standard
        )
        self.parameters.max_scripts = config.max_scripts

        # Configuring Models
        if len(self.models) == 0:
            self.log.warning("Models are not initialized. Initializing...")
            self.init_models()

        for model in self.models:
            # TODO: This check will give us time to implement the required
            # changes on the models.
            if hasattr(config, model):
                self.log.debug(f"Configuring {model}")
                self.models[model].configure(getattr(config, model))
            else:
                self.log.warning(f"No configuration for {model}. Skipping.")

        # Configuring Driver and Scheduler

        survey_topology = self.configure_driver(config)

        # Publish topology
        self.tel_surveyTopology.put(
            survey_topology.to_topic(self.tel_surveyTopology.DataType())
        )

        # Publish settingsApplied and appliedSettingsMatchStart

        self.evt_appliedSettingsMatchStart.set_put(
            appliedSettingsMatchStartIsTrue=True, force_output=True
        )

        # Most configurations comes from this single commit hash. I think the
        # other modules could host the version for each one of them
        if hasattr(self, "evt_dependenciesVersions"):
            self.evt_dependenciesVersions.set_put(
                version="",
                scheduler=self.parameters.driver_type,
                observatoryModel=obs_mod_version.__version__,
                observatoryLocation=dateloc_version.__version__,
                seeingModel=seeing_version.__version__,
                cloudModel=cloud_version.__version__,
                skybrightnessModel=astrosky_version.__version__,
                downtimeModel=downtime_version.__version__,
                force_output=True,
            )
        else:
            self.log.warning("No 'dependenciesVersions' event.")

    def configure_driver(self, config):
        """Load driver for selected scheduler and configure its basic
        parameters.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `lsst.ts.scheduler.kernel.SurveyTopology`

        """
        if self.driver is not None:
            self.log.warning("Driver already defined. Overwriting driver.")
            # TODO: It is probably a good idea to tell driver to save its state
            # before overwriting. So it is possible to recover.

        self.log.debug("Loading driver from %s", config.driver_type)
        driver_lib = import_module(config.driver_type)
        members_of_driver_lib = inspect.getmembers(driver_lib)

        driver_type = None
        for member in members_of_driver_lib:
            try:
                if issubclass(member[1], Driver):
                    self.log.debug("Found driver %s%s", member[0], member[1])
                    driver_type = member[1]
                    # break
            except TypeError:
                pass

        if driver_type is None:
            raise RuntimeError(
                "Could not find Driver on module %s" % config.driver_type
            )

        self.driver = driver_type(models=self.models, raw_telemetry=self.raw_telemetry)

        # load_override_configuration(self.driver.parameters,
        #                             self.configuration_path)

        return self.driver.configure_scheduler(config)

    def run(self):
        """ This is the method that runs when the system is in enable state.
        It is responsible for the target production loop, updating telemetry,
        requesting targets from the driver to build a queue and filling
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
        queue: `ScriptQueue_logevent_queueC`
            SAL Topic with information about the queue.

        """

        self.log.debug("Getting queue.")

        self.queue_remote.evt_queue.flush()

        try:
            if request:
                await self.queue_remote.cmd_showQueue.start(
                    timeout=self.parameters.cmd_timeout
                )
            try:
                queue = await self.queue_remote.evt_queue.next(
                    flush=False, timeout=self.parameters.cmd_timeout
                )
            except asyncio.TimeoutError:
                self.log.error("No state from queue. Requesting...")
                self.queue_remote.evt_queue.flush()
                await self.queue_remote.cmd_showQueue.start(
                    timeout=self.parameters.cmd_timeout
                )
                queue = await self.queue_remote.evt_queue.next(
                    flush=False, timeout=self.parameters.cmd_timeout
                )
        except salobj.AckError as e:
            self.log.error("No response from queue...")
            self.fault(
                code=NO_QUEUE,
                report="Error no response from queue.",
                traceback=traceback.format_exc(),
            )
            raise e
        else:
            return queue

    async def check_scheduled(self):
        """Loop through the scheduled targets list, check status and tell
        driver of completed observations.

        Returns
        -------
        bool
            `True` if all checked scripts where Done or in non-final state.
            `False` if no scheduled targets to check or if one or more scripts
            ended up a failed or unrecognized state.

        """
        ntargets = len(self.raw_telemetry["scheduled_targets"])

        if ntargets == 0:
            self.log.debug("No scheduled targets to check.")
            return False

        self.log.debug(f"Checking {ntargets} scheduled targets")

        retval = True
        for i in range(ntargets):
            target = self.raw_telemetry["scheduled_targets"].pop(0)
            if target.sal_index in self.script_info:
                info = self.script_info[target.sal_index]
            else:
                # No information on script on queue, put it back and continue
                self.raw_telemetry["scheduled_targets"].append(target)
                continue

            if info.processState == ScriptQueue.ScriptProcessState.DONE:
                # Script completed I'll assume the observation was successful.
                # TODO: Need to make sure script completed successfully. Can
                # use scriptState from info as a first guess
                # FIXME: we probably need to get updated information about the
                # observed target
                self.driver.register_observation(target)

                # Remove related script from the list
                del self.script_info[target.sal_index]
                # target now simply disappears... Should I keep it in for
                # future refs?
            elif info.processState in NonFinalStates:
                # script in a non-final state, just put it back on the list.
                self.raw_telemetry["scheduled_targets"].append(target)
            elif info.processState == ScriptQueue.ScriptProcessState.CONFIGUREFAILED:
                self.log.warning(
                    "Failed to configure observation for target %s.", target.sal_index
                )
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False
            elif info.processState == ScriptQueue.ScriptProcessState.TERMINATED:
                self.log.warning(
                    "Observation for target %s terminated.", target.sal_index
                )
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False
            else:
                self.log.error(
                    "Unrecognized state [%i] for observation %i for target %s.",
                    info.processState,
                    target.sal_index,
                    target,
                )
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False

        return retval

    async def simple_target_production_loop(self):
        """ This coroutine implements the simple target production loop. It
        will query the status of the queue and, if there is nothing running,
        it will add an observation to the back of the queue. Once Scheduler is
        enabled with simple mode, this coroutine will be added to the event
        loop as a future. While running it will checking the queue and put
        targets to it. If the queue is paused or there is a running script, it
        will not add any target to it. If the Scheduler is disabled this
        method will be cancelled.

        Also, note that the target production loop does not care about if it
        is day or night. It is up to the scheduling algorithm to decide
        whether there is something to observe or not given the input telemetry.
        A
        target produced by the scheduler can have a start time. In this case,
        the task will be sent to the queue and it is up to the queue or the
        running script to wait for the specified time. If the scheduling
        algorithm does not produce any target, then the Scheduler will keep
        updating telemetry and requesting targets until something is returned
        to be executed.

        NOTE: This method may either run in the main event loop or in an event
        loop of a thread. If it is the first case, we need to make sure long
        running tasks are sent to a thread or a process. If the latter, then it
        should be ok to simple execute long running tasks and block the thread
        event loop.

        """

        self.run_loop = True
        self.raw_telemetry["scheduled_targets"] = []

        loop = asyncio.get_event_loop()

        first_pass = True
        while self.summary_state == salobj.State.ENABLED and self.run_loop:
            try:
                # If it is the first pass get the current queue, otherwise
                # wait for the queue to change or get the latest if there's
                # some
                queue = await self.get_queue(first_pass)

                # This return False if script failed, in which case next pass
                # won't wait for queue to change
                first_pass = not await self.check_scheduled()

                # Only send targets to queue if it is running, empty and there
                # is nothing executing
                if queue.running and queue.currentSalIndex == 0 and queue.length == 0:
                    # TODO: publish detailed state indicating that the
                    # scheduler is selecting a target

                    self.log.debug("Queue ready to receive targets.")

                    await loop.run_in_executor(None, self.update_telemetry)

                    target = await loop.run_in_executor(
                        None, self.driver.select_next_target
                    )

                    # This method receives a list of targets and return a list
                    # of script ids
                    await self.put_on_queue([target])

                    if target.sal_index > 0:
                        self.raw_telemetry["scheduled_targets"].append(target)
                    else:
                        self.log.error("Could not add target to the queue: %s", target)
                        self.fault(
                            code=PUT_ON_QUEUE,
                            report=f"Could not add target to the queue: {target}",
                        )

                    # TODO: publish detailed state indicating that the
                    # scheduler has finished the target selection

                else:
                    # TODO: Publish detailed state indicating that the
                    # scheduler is waiting.
                    self.log.debug(
                        "Queue state: [Running:%s][Executing:%s][Empty:%s]",
                        queue.running == 1,
                        queue.currentSalIndex != 0,
                        queue.length == 0,
                    )
                    await asyncio.sleep(self.parameters.loop_sleep_time)
            except asyncio.CancelledError as e:
                self.log.exception(e)
                break
            except Exception as e:
                # If there is an exception go to FAULT state, log the
                # exception and break the loop
                self.fault(
                    code=SIMPLE_LOOP_ERROR,
                    report="Error on simple target production loop.",
                    traceback=traceback.format_exc(),
                )
                self.log.exception(e)
                break

    def callback_script_info(self, data):
        """This callback function will store in a dictionary information about
        the scripts.

        The method will store information about any script that is placed in
        the queue so that the scheduler can access information about those if
        needed. It then, tracks the size of the dictionary where this
        information is stored and deletes them appropriately. Also, note that
        the scripts are removed if they where created by the scheduler and are
        in a final state when `self.check_scheduled()` is called.
        """

        # This method implements a workaround an issue with SAL where Python
        # cannot create copies of topics. So instead, it parse the topic into
        # a named tuple so it is possible to access the data the same way if
        # the topic itself was stored.

        self.script_info[data.salIndex] = data

        # Make sure the size of script info is smaller then the maximum allowed
        script_info_size = len(self.script_info)
        if script_info_size > self.parameters.max_scripts:
            self.log.debug("Cleaning up script info database.")
            # Removes old entries
            for key in self.script_info:
                del self.script_info[key]
                if len(self.script_info) < self.parameters.max_scripts:
                    break
