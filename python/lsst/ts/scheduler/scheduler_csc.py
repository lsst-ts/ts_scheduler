# This file is part of ts_scheduler
#
# Developed for the Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

__all__ = [
    "SchedulerCSC",
    "run_scheduler",
]

import asyncio
import contextlib
import dataclasses
import shutil
import time
import traceback
import typing

import numpy as np
from lsst.ts.astrosky.model import version as astrosky_version
from lsst.ts.dateloc import version as dateloc_version
from lsst.ts.idl.enums import ScriptQueue
from lsst.ts.observatory.model import version as obs_mod_version
from rubin_sim.version import __version__ as rubin_sim_version

from lsst.ts import salobj, utils

from . import CONFIG_SCHEMA, __version__
from .driver.driver_target import DriverTarget
from .model import Model
from .utils.csc_utils import (
    OBSERVATION_NAMED_PARAMETERS,
    DetailedState,
    SchedulerModes,
    set_detailed_state,
    support_command,
)
from .utils.error_codes import (
    ADVANCE_LOOP_ERROR,
    NO_QUEUE,
    OBSERVATORY_STATE_UPDATE,
    PUT_ON_QUEUE,
    SIMPLE_LOOP_ERROR,
    UNABLE_TO_FIND_TARGET,
    UPDATE_TELEMETRY_ERROR,
)
from .utils.exceptions import (
    FailedToQueueTargetsError,
    UnableToFindTargetError,
    UpdateTelemetryError,
)
from .utils.parameters import SchedulerCscParameters


class SchedulerCSC(salobj.ConfigurableCsc):
    """This class is a reactive component which is SAL aware and delegates
    work.

    The SchedulerCSC is the only layer that is exposed to SAL communication.
    All commands recieved are by the SchedulerCSC then delegated to the
    responsible objects. Along with this the SchedulerCSC maintains a
    statemachine which is taken care of by the inherited class
    `base_csc.BaseCsc`.

    Parameters
    ----------
    index : `int`
        Scheduler SAL component index. This also defines the index of the
        ScriptQueue the Scheduler will communicate with.

        * 1 for the Main telescope.
        * 2 for AuxTel.
        * Any allowed value (see ``Raises``) for unit tests.

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

    Notes
    -----
    **Simulation Modes**

    Supported simulation modes:

    * `SchedulerModes.NORMAL`: Regular operation
    * `SchedulerModes.MOCKS3`: Semi-operation mode. Normal operation but mock
        s3 bucket for large file object.
    * `SchedulerModes.SIMULATION`: Simulation mode. Do not initialize driver
        and other operational components.

    **Error Codes**

    * 300: Could not connect to the queue. This error code is published
           if the Scheduler CSC can not connect to the queue.

    * 301: Failed to put target on the queue.

    * 400: Unspecified error on the simple target generation loop. This error
           code is published if there is an unspecified error while running the
           simple target generation loop. For instance, if a user defined
           scheduling algorithm throws an exception after a call to
           `Driver.select_next_target` this error code will, most likely, be
           issued (along with the traceback message).

    * 401: Unspecified error on advanced target generation loop.

    * 500: Error updating observatory state.
    """

    valid_simulation_modes = tuple([mode.value for mode in SchedulerModes])
    version = __version__

    def __init__(
        self,
        index,
        config_dir=None,
        initial_state=salobj.base_csc.State.STANDBY,
        simulation_mode=0,
    ):

        compatibility_commands = dict(
            computePredictedSchedule=self._do_computePredictedSchedule,
            addBlock=self._do_addBlock,
            getBlockStatus=self._do_getBlockStatus,
            removeBlock=self._do_removeBlock,
            validateBlock=self._do_validateBlock,
        )

        for command_name, command_method in compatibility_commands.items():
            if support_command(command_name):
                setattr(self, f"do_{command_name}", command_method)

        super().__init__(
            name="Scheduler",
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            index=index,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

        # Communication channel with OCS queue.
        self.queue_remote = salobj.Remote(
            self.domain, "ScriptQueue", index=index, include=["script", "queue"]
        )

        # Communication channel with pointing component to get observatory
        # state
        self.ptg = salobj.Remote(
            self.domain,
            "MTPtg" if index == 1 else "ATPtg",
            include=["currentTargetStatus"],
        )

        self.no_observatory_state_warning = False

        self.parameters = SchedulerCscParameters()

        # The maximum tolerable time without targets in seconds.
        self.max_time_no_target = 3600.0

        # The maximum number of targets in the predicted schedule.
        self.max_predicted_targets = 1000

        # Default command response timeout, in seconds.
        self.default_command_timeout = 60.0

        # How long to wait for target loop to stop before killing it, in
        # seconds.
        self.loop_die_timeout = 5.0

        self.telemetry_stream_handler = None

        # This asyncio.Event is used to control when the scheduling task will
        # be running or not, once the CSC is in enable. By default, the loop
        # will not run once the CSC is enabled, and a "resume" command is
        # needed to start it.
        self.run_target_loop = asyncio.Event()

        # Lock for the event loop. This is used to synchronize actions that
        # will affect the target production loop.
        self.target_loop_lock = asyncio.Lock()

        self.scheduler_state_lock = asyncio.Lock()

        self._detailed_state_lock = asyncio.Lock()

        # dictionary to store background tasks
        self._tasks = dict()

        # Stores the coroutine for the target production.
        self._tasks["target_production_task"] = None

        # A flag to indicate that the event loop is running
        self.run_loop = False

        # Telemetry loop. This will take care of observatory state.
        self._tasks["telemetry_loop_task"] = None

        # List of targets used in the ADVANCE target loop
        self.targets_queue = []

        # keep track whether a "no new target" condition was handled by the
        # scheduler.
        self._no_target_handled = False

        # Future to store the results or target_queue check.
        self.targets_queue_condition = utils.make_done_future()
        self._should_compute_predicted_schedule = False

        # Task with a timer to evaluate next target when none is produced by
        # the scheduler.
        self.next_target_timer = utils.make_done_future()

        # Large file object available
        self.s3bucket_name = None  # Set by `configure`.
        self.s3bucket = None  # Set by `handle_summary_state`.

        self.model = Model(self.log)
        # Add callback to script info
        self.queue_remote.evt_script.callback = self.model.callback_script_info

    async def begin_start(self, data):

        await self.cmd_start.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Starting CSC.",
        )

        try:
            await super().begin_start(data)
        except Exception:
            self.log.exception("Error in begin start")
            raise

    async def begin_enable(self, data):
        """Begin do_enable.

        Called before state transition from `State.DISABLED` to
        `State.ENABLED`. This method will start the selected target production
        loop (SIMPLE, ADVANCED or DRY) or raise an exception if the mode is
        unrecognized.

        Parameters
        ----------
        data : `DataType`
            Command data

        """

        await self.cmd_enable.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Enabling CSC.",
        )

        # Make sure event is not set so loops won't start once the CSC is
        # enabled.
        self.run_target_loop.clear()

        if (
            self.simulation_mode == SchedulerModes.SIMULATION
            or self.parameters.mode == "DRY"
        ):

            self.log.info(
                "Running with no target production loop. "
                f"Operation mode: {self.parameters.mode}. "
                f"Simulation mode: {self.simulation_mode}. "
            )
            self._tasks["target_production_task"] = None

        elif self.parameters.mode == "SIMPLE":

            self._tasks["target_production_task"] = asyncio.create_task(
                self.simple_target_production_loop()
            )

        elif self.parameters.mode == "ADVANCE":

            self._tasks["target_production_task"] = asyncio.create_task(
                self.advance_target_production_loop()
            )

        else:
            # This will just reject the command
            raise RuntimeError("Unrecognized scheduler mode %s" % self.parameters.mode)

    async def handle_summary_state(self):
        """Handle summary state.

        If the component is DISABLED or ENABLED, it will make sure the
        telemetry loop is running. Shutdown the telemetry loop if in STANDBY.
        """

        if self.disabled_or_enabled and self._tasks["telemetry_loop_task"] is None:
            self.run_loop = True
            self._tasks["telemetry_loop_task"] = asyncio.create_task(
                self.telemetry_loop()
            )

            await self.reset_handle_no_targets_on_queue()

            if self.s3bucket is None:
                mock_s3 = self.simulation_mode == SchedulerModes.MOCKS3
                self.s3bucket = salobj.AsyncS3Bucket(
                    name=self.s3bucket_name, domock=mock_s3, create=mock_s3
                )

        elif self.summary_state == salobj.State.STANDBY:

            await self._stop_all_background_tasks()

            if self.s3bucket is not None:
                self.s3bucket.stop_mock()
            self.s3bucket = None

        await self.evt_detailedState.set_write(
            substate=DetailedState.IDLE, force_output=True
        )

    async def begin_disable(self, data):
        """Transition from `State.ENABLED` to `State.DISABLED`. This
        transition will be made in a gentle way, meaning that it will wait for
        the target production loop to finalize before making the transition.
        If a more drastic approach is need, the scheduler must be sent to
        `State.FAULT` with an `abort` command.

        Parameters
        ----------
        data : `DataType`
            Command data

        """
        await self.cmd_disable.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Disabling CSC.",
        )

        await self._stop_all_background_tasks()

    async def do_resume(self, data):
        """Resume target production loop.

        Parameters
        ----------
        data : `DataType`
            Command data

        Raises
        ------
        RuntimeError
            If target production loop is already running.

        """

        self.assert_enabled()

        if self.run_target_loop.is_set():
            raise RuntimeError("Target production loop already running.")

        await self._transition_idle_to_running()

        self.run_target_loop.set()

    async def do_stop(self, data):
        """Stop target production loop.

        Parameters
        ----------
        data : `DataType`
            Command data

        """

        self.assert_enabled()

        if not self.run_target_loop.is_set():
            raise RuntimeError("Target production loop is not running.")

        await self.cmd_stop.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Stopping Scheduler execution.",
        )

        self.run_target_loop.clear()

        if data.abort:
            async with self.target_loop_lock:
                await self.remove_from_queue(self.raw_telemetry["scheduled_targets"])

        await self.reset_handle_no_targets_on_queue()

        await self._transition_running_to_idle()

    async def stop_next_target_timer_task(self):

        if not self.next_target_timer.done():
            self.log.debug("Cancelling next target timer.")
            self.next_target_timer.cancel()
            try:
                await self.next_target_timer
            except asyncio.CancelledError:
                pass
            except Exception:
                self.log.exception(
                    "Error in waiting for next target timer to complete."
                )

    async def do_load(self, data):
        """Load user-defined schedule definition from URI.

        The file is passed on to the driver to load. It must be compatible with
        the currently configured scheduling algorithm or the load will fail,
        and the command will be rejected.

        Parameters
        ----------
        data : `DataType`
            Command data

        """

        self.assert_enabled()

        if self.run_target_loop.is_set():
            raise RuntimeError(
                "Target production loop is running. Stop it before loading a file."
            )

        await self.cmd_load.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Loading snapshot.",
        )

        await self.model.handle_load_snapshot(data.uri)

    async def _do_computePredictedSchedule(self, data):
        """Compute and publish the predicted schedule.

        This command can only be executed if the Scheduler is idle. It is
        currently running, the command will be rejected.

        Parameters
        ----------
        data : `DataType`
            Command data.
        """

        self.assert_enabled()

        if self.run_target_loop.is_set():
            raise RuntimeError(
                "Scheduler is currently running. Note that the predicted schedule "
                "is computed automatically while the Scheduler is running."
            )

        await self.cmd_computePredictedSchedule.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Computing predicted schedule.",
        )

        try:
            # Need to be running to compute predicted schedule
            await self._transition_idle_to_running()

            self._tasks["compute_predicted_schedule"] = asyncio.create_task(
                self.compute_predicted_schedule()
            )
            await self._tasks["compute_predicted_schedule"]
        finally:
            # Going back to idle.
            await self._transition_running_to_idle()

    async def _do_addBlock(self, data):
        """Implement add block command.

        Parameters
        ----------
        data : `DataType`
            Command data.

        Raises
        ------
        NotImplementedError
            Command not implemented yet.
        """
        self.assert_enabled()
        raise NotImplementedError("Command not implemented yet.")

    async def _do_getBlockStatus(self, data):
        """Implement get block status command.

        Parameters
        ----------
        data : `DataType`
            Command data.

        Raises
        ------
        NotImplementedError
            Command not implemented yet.
        """
        self.assert_enabled()
        raise NotImplementedError("Command not implemented yet.")

    async def _do_removeBlock(self, data):
        """Implement remove block command.

        Parameters
        ----------
        data : `DataType`
            Command data.

        Raises
        ------
        NotImplementedError
            Command not implemented yet.
        """
        self.assert_enabled()
        raise NotImplementedError("Command not implemented yet.")

    async def _do_validateBlock(self, data):
        """Implement validate block command.

        Parameters
        ----------
        data : `DataType`
            Command data.

        Raises
        ------
        NotImplementedError
            Command not implemented yet.
        """
        self.assert_enabled()
        raise NotImplementedError("Command not implemented yet.")

    async def telemetry_loop(self):
        """Scheduler telemetry loop.

        This method will monitor and process the observatory state and publish
        the information to SAL.

        """

        failed_observatory_state_logged = False
        while self.run_loop:

            # Update observatory state and sleep at the same time.
            try:
                await asyncio.gather(
                    self.handle_observatory_state(),
                    asyncio.sleep(self.heartbeat_interval),
                )
                failed_observatory_state_logged = False
            except Exception:
                queue = await self.get_queue(request=False)
                if (
                    self.summary_state == salobj.State.ENABLED
                    and self.run_target_loop.is_set()
                    and queue.running
                ):
                    self.log.exception("Failed to update observatory state.")
                    await self.fault(
                        code=OBSERVATORY_STATE_UPDATE,
                        report="Failed to update observatory state.",
                        traceback=traceback.format_exc(),
                    )
                    return
                elif not failed_observatory_state_logged:
                    failed_observatory_state_logged = True
                    additional_messages: typing.List[str] = []
                    additional_messages.append(
                        " not running"
                        if self.summary_state == salobj.State.ENABLED
                        and not self.run_target_loop.is_set()
                        else ""
                    )
                    additional_messages.append(
                        " queue not running"
                        if self.summary_state == salobj.State.ENABLED
                        and not queue.running
                        else ""
                    )

                    message_text = ""

                    n_message = 0
                    for message in additional_messages:
                        if len(message) > 0:
                            if n_message == 0:
                                message_text += " but"
                            else:
                                message_text += " and"
                            n_message += 1
                            message_text += message

                    self.log.warning(
                        "Failed to update observatory state. "
                        f"Ignoring, scheduler in {self.summary_state!r}{message_text}."
                    )

            await self.tel_observatoryState.set_write(
                **self.model.get_observatory_state()
            )

            try:
                await asyncio.wait_for(
                    self._publish_general_info(),
                    timeout=self.heartbeat_interval,
                )
            except asyncio.TimeoutError:
                self.log.debug("Timeout computing general info.")
            except Exception:
                self.log.exception("Error computing general info. Ignoring...")

    async def handle_observatory_state(self):
        """Handle observatory state."""

        current_target_state = await self.ptg.tel_currentTargetStatus.next(
            flush=True, timeout=self.heartbeat_interval
        )

        self.model.set_observatory_state(current_target_state=current_target_state)

    async def put_on_queue(self, targets):
        """Given a list of targets, append them on the queue to be observed.
        Each target sal_index attribute is updated with the unique identifier
        value (salIndex) returned by the queue.


        Parameters
        ----------
        targets : `list`
            A list of targets to put on the queue.

        """

        for target in targets:
            (
                observing_script,
                observing_script_is_standard,
            ) = target.get_observing_script()

            self.queue_remote.cmd_add.set(
                path=observing_script,
                config=target.get_script_config(),
                isStandard=observing_script_is_standard,
                location=ScriptQueue.Location.LAST,
                logLevel=self.log.getEffectiveLevel(),
            )

            self.log.debug(f"Putting target {target.targetid} on the queue.")
            add_task = await self.queue_remote.cmd_add.start(
                timeout=self.parameters.cmd_timeout
            )

            # publishes target event
            await self.evt_target.set_write(**target.as_dict())

            target.sal_index = int(add_task.result)

    async def remove_from_queue(self, targets):
        """Given a list of targets, remove them from the queue.

        Parameters
        ----------
        targets: `list`
            A list of targets to put on the queue.

        """

        stop_scripts = self.queue_remote.cmd_stopScripts.DataType()

        stop_scripts.length = len(targets)
        stop_scripts.terminate = False

        for i in range(stop_scripts.length):
            stop_scripts.salIndices[i] = targets[i].sal_index

        await self.queue_remote.cmd_stopScripts.start(
            stop_scripts, timeout=self.parameters.cmd_timeout
        )

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

        self.s3bucket_name = salobj.AsyncS3Bucket.make_bucket_name(
            s3instance=config.s3instance,
        )

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

        survey_topology = await self.model.configure(config)

        await self.evt_surveyTopology.set_write(**survey_topology.as_dict())

        # Most configurations comes from this single commit hash. I think the
        # other modules could host the version for each one of them
        if hasattr(self, "evt_dependenciesVersions"):
            await self.evt_dependenciesVersions.set_write(
                version="",
                scheduler=self.parameters.driver_type,
                observatoryModel=obs_mod_version.__version__,
                observatoryLocation=dateloc_version.__version__,
                seeingModel=rubin_sim_version,
                cloudModel=rubin_sim_version,
                skybrightnessModel=astrosky_version.__version__,
                downtimeModel=rubin_sim_version,
                force_output=True,
            )
        else:
            self.log.warning("No 'dependenciesVersions' event.")

        await self.evt_obsSiteConfig.set_write(
            observatoryName=config.models["location"]["obs_site"]["name"],
            latitude=config.models["location"]["obs_site"]["latitude"],
            longitude=config.models["location"]["obs_site"]["longitude"],
            height=config.models["location"]["obs_site"]["height"],
        )

        await self.evt_telescopeConfig.set_write(
            altitudeMinpos=config.models["observatory_model"]["telescope"][
                "altitude_minpos"
            ],
            altitudeMaxpos=config.models["observatory_model"]["telescope"][
                "altitude_maxpos"
            ],
            azimuthMinpos=config.models["observatory_model"]["telescope"][
                "azimuth_minpos"
            ],
            azimuthMaxpos=config.models["observatory_model"]["telescope"][
                "azimuth_maxpos"
            ],
            altitudeMaxspeed=config.models["observatory_model"]["telescope"][
                "altitude_maxspeed"
            ],
            altitudeAccel=config.models["observatory_model"]["telescope"][
                "altitude_accel"
            ],
            altitudeDecel=config.models["observatory_model"]["telescope"][
                "altitude_decel"
            ],
            azimuthMaxspeed=config.models["observatory_model"]["telescope"][
                "azimuth_maxspeed"
            ],
            azimuthAccel=config.models["observatory_model"]["telescope"][
                "azimuth_accel"
            ],
            azimuthDecel=config.models["observatory_model"]["telescope"][
                "azimuth_decel"
            ],
            settleTime=config.models["observatory_model"]["telescope"]["settle_time"],
        )

        await self.evt_rotatorConfig.set_write(
            positionMin=config.models["observatory_model"]["rotator"]["minpos"],
            positionMax=config.models["observatory_model"]["rotator"]["maxpos"],
            positionFilterChange=config.models["observatory_model"]["rotator"][
                "filter_change_pos"
            ],
            speedMax=config.models["observatory_model"]["rotator"]["maxspeed"],
            accel=config.models["observatory_model"]["rotator"]["accel"],
            decel=config.models["observatory_model"]["rotator"]["decel"],
            followSky=config.models["observatory_model"]["rotator"]["follow_sky"],
            resumeAngle=config.models["observatory_model"]["rotator"]["resume_angle"],
        )

        await self.evt_domeConfig.set_write(
            altitudeMaxspeed=config.models["observatory_model"]["dome"][
                "altitude_maxspeed"
            ],
            altitudeAccel=config.models["observatory_model"]["dome"]["altitude_accel"],
            altitudeDecel=config.models["observatory_model"]["dome"]["altitude_decel"],
            altitudeFreerange=config.models["observatory_model"]["dome"][
                "altitude_freerange"
            ],
            azimuthMaxspeed=config.models["observatory_model"]["dome"][
                "azimuth_maxspeed"
            ],
            azimuthAccel=config.models["observatory_model"]["dome"]["azimuth_accel"],
            azimuthDecel=config.models["observatory_model"]["dome"]["azimuth_decel"],
            azimuthFreerange=config.models["observatory_model"]["dome"][
                "azimuth_freerange"
            ],
            settleTime=config.models["observatory_model"]["dome"]["settle_time"],
        )

        await self.evt_slewConfig.set_write(
            prereqDomalt=config.models["observatory_model"]["slew"]["prereq_domalt"],
            prereqDomaz=config.models["observatory_model"]["slew"]["prereq_domaz"],
            prereqDomazSettle=config.models["observatory_model"]["slew"][
                "prereq_domazsettle"
            ],
            prereqTelalt=config.models["observatory_model"]["slew"]["prereq_telalt"],
            prereqTelaz=config.models["observatory_model"]["slew"]["prereq_telaz"],
            prereqTelOpticsOpenLoop=config.models["observatory_model"]["slew"][
                "prereq_telopticsopenloop"
            ],
            prereqTelOpticsClosedLoop=config.models["observatory_model"]["slew"][
                "prereq_telopticsclosedloop"
            ],
            prereqTelSettle=config.models["observatory_model"]["slew"][
                "prereq_telsettle"
            ],
            prereqTelRot=config.models["observatory_model"]["slew"]["prereq_telrot"],
            prereqFilter=config.models["observatory_model"]["slew"]["prereq_filter"],
            prereqExposures=config.models["observatory_model"]["slew"][
                "prereq_exposures"
            ],
            prereqReadout=config.models["observatory_model"]["slew"]["prereq_readout"],
        )

        await self.evt_opticsLoopCorrConfig.set_write(
            telOpticsOlSlope=config.models["observatory_model"]["optics_loop_corr"][
                "tel_optics_ol_slope"
            ],
            telOpticsClAltLimit=config.models["observatory_model"]["optics_loop_corr"][
                "tel_optics_cl_alt_limit"
            ],
            telOpticsClDelay=config.models["observatory_model"]["optics_loop_corr"][
                "tel_optics_cl_delay"
            ],
        )

        await self.evt_parkConfig.set_write(
            telescopeAltitude=config.models["observatory_model"]["park"][
                "telescope_altitude"
            ],
            telescopeAzimuth=config.models["observatory_model"]["park"][
                "telescope_azimuth"
            ],
            telescopeRotator=config.models["observatory_model"]["park"][
                "telescope_rotator"
            ],
            domeAltitude=config.models["observatory_model"]["park"]["dome_altitude"],
            domeAzimuth=config.models["observatory_model"]["park"]["dome_azimuth"],
            filterPosition=config.models["observatory_model"]["park"][
                "filter_position"
            ],
        )

    async def get_queue(self, request: bool = True) -> salobj.type_hints.BaseMsgType:
        """Utility method to get the queue.

        Parameters
        ----------
        request : `bool`
            Issue request for queue state?

        Returns
        -------
        queue: `ScriptQueue_logevent_queueC`
            SAL Topic with information about the queue.
        """

        self.log.debug("Getting queue.")

        self.queue_remote.evt_queue.flush()

        queue: typing.Union[salobj.type_hints.BaseMsgType, None] = None

        try:
            if request:
                queue = await self._request_queue_state()
            else:
                try:
                    queue = await self.queue_remote.evt_queue.aget(
                        timeout=self.parameters.cmd_timeout
                    )
                except asyncio.TimeoutError:
                    self.log.debug("No state from queue. Requesting...")
                    queue = await self._request_queue_state()
        except salobj.AckError as e:
            self.log.error("No response from queue...")
            await self.fault(
                code=NO_QUEUE,
                report="No response from queue.",
                traceback=traceback.format_exc(),
            )
            raise e
        else:
            assert queue is not None
            return queue

    async def _request_queue_state(self) -> salobj.type_hints.BaseMsgType:
        """Request queue state.

        Returns
        -------
        queue : `ScriptQueue.logevent_queue`
            Queue state.
        """
        self.queue_remote.evt_queue.flush()

        await self.queue_remote.cmd_showQueue.start(timeout=self.parameters.cmd_timeout)
        queue = await self.queue_remote.evt_queue.next(
            flush=False, timeout=self.parameters.cmd_timeout
        )

        return queue

    async def check_scheduled_targets(self):
        """Loop through the scheduled targets list, check status and tell
        driver of completed observations.

        Returns
        -------
        bool
            `True` if all checked scripts where Done or in non-final state.
            `False` if no scheduled targets to check or if one or more scripts
            ended up a failed or unrecognized state.
        """

        if self.model.get_number_of_scheduled_targets() == 0:
            self.log.debug("No scheduled targets to check.")
            return False
        scheduled_targets_info = await self.model.check_scheduled_targets()

        for target in scheduled_targets_info.observed:
            await self.register_observation(target)

        return (
            len(scheduled_targets_info.failed) == 0
            and len(scheduled_targets_info.unrecognized) == 0
        )

    async def simple_target_production_loop(self):
        """This coroutine implements the simple target production loop. It
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
        A target produced by the scheduler can have a start time. In this case,
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
        self.model.reset_scheduled_targets()
        first_pass = True

        while self.summary_state == salobj.State.ENABLED and self.run_loop:

            await self.run_target_loop.wait()

            try:
                async with self.target_loop_lock:

                    # If it is the first pass get the current queue, otherwise
                    # wait for the queue to change or get the latest if there's
                    # some
                    queue = await self.get_queue(first_pass)

                    # This returns False if script failed, in which case next
                    # pass won't wait for queue to change
                    first_pass = not await self.check_scheduled_targets()

                    # Only send targets to queue if it is running, empty and
                    # there is nothing executing
                    if (
                        queue.running
                        and queue.currentSalIndex == 0
                        and queue.length == 0
                    ):
                        # TODO: publish detailed state indicating that the
                        # scheduler is selecting a target

                        self.log.debug("Queue ready to receive targets.")

                        await self.model.update_telemetry()

                        target = await self.model.select_next_target()

                        current_tai = utils.current_tai()

                        if target.obs_time > current_tai:
                            delta_t = current_tai - target.obs_time
                            self.log.debug(
                                f"Target observing time in the future. Waiting {delta_t}s"
                            )
                            await asyncio.sleep(delta_t)

                        # This method receives a list of targets and return a
                        # list of script ids
                        await self.put_on_queue([target])

                        if target.sal_index > 0:
                            self.model.add_scheduled_target(target)
                        else:
                            self.log.error(
                                "Could not add target to the queue: %s", target
                            )
                            await self.fault(
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
            except asyncio.CancelledError:
                break
            except Exception:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=SIMPLE_LOOP_ERROR,
                        report="Error on simple target production loop.",
                        traceback=traceback.format_exc(),
                    )
                    self.log.exception("Error on simple target production loop.")
                #  ...and break the loop
                break

    async def advance_target_production_loop(self):
        """Advance target production loop.

        This method will schedule targets ahead of time and send them to the
        ScriptQueue according to the configuration parameters. This initial
        implementation is simply blindly scheduling targets ahead of time and
        not checking for post conditions. Further improvements will involve
        dealing with different post conditions, generating the predicted queue
        and further verifying that the schedule is keeping up.
        """
        self.run_loop = True
        self.model.reset_scheduled_targets()

        first_pass = True
        targets_queue_condition_task = utils.make_done_future()

        self.targets_queue = []
        self.targets_queue_condition = utils.make_done_future()
        self._should_compute_predicted_schedule = False

        self.log.info("Starting target production loop.")

        while self.summary_state == salobj.State.ENABLED and self.run_loop:

            if not self.next_target_timer.done():
                self.log.debug("Waiting next target timer task...")
                async with self.detailed_state(
                    detailed_state=DetailedState.WAITING_NEXT_TARGET_TIMER_TASK
                ):
                    await self.next_target_timer

            await self.run_target_loop.wait()

            try:
                if self.need_to_generate_target_queue:

                    await self.generate_target_queue()

                async with self.target_loop_lock:

                    # If it is the first pass get the current queue, otherwise
                    # wait for the queue to change or get the latest if there's
                    # some
                    queue = await self.get_queue(first_pass)

                    # This returns False if script failed, in which case next
                    # pass won't wait for queue to change
                    first_pass = not await self.check_scheduled_targets()

                    # The advance loop will always leave
                    # self.parameters.n_targets additional target
                    # in the queue. So we will schedule if the queue is running
                    # and there is less than self.parameters.n_targets targets
                    # in the queue. Basically, one target is executing and the
                    # next will be waiting.
                    if (
                        queue.running
                        and queue.length < self.parameters.n_targets + 1
                        and len(self.targets_queue) > 0
                    ):
                        await self.queue_targets()
                    elif self._should_compute_predicted_schedule:
                        await self.compute_predicted_schedule()
                    else:
                        # Now it would be time for the scheduler to sleep while
                        # it waits for the targets in the queue to execute. We
                        # can take this time to check that the targets in the
                        # queue are still good. We need to to this in the
                        # background and keep track of the time. If we can
                        # check this quick enough we continue waiting the
                        # remaining time, otherwise we leave the check
                        # running in the background.

                        self.log.debug(
                            "Queue state: [Running:%s][Executing:%s][length:%d]",
                            queue.running == 1,
                            queue.currentSalIndex != 0,
                            queue.length,
                        )

                        if targets_queue_condition_task.done():
                            # Task to check the targets_queue condition.
                            targets_queue_condition_task = asyncio.create_task(
                                self.check_targets_queue_condition(),
                                name="check_targets_queue_condition",
                            )

                        loop_sleep_task = asyncio.create_task(
                            asyncio.sleep(self.parameters.loop_sleep_time)
                        )
                        # Using the asyncio.wait with a timeout will simply
                        # return at the end without cancelling the task. If the
                        # check takes less then the loop_sleep_time, we still
                        # want to wait the remaining time, so that is why we
                        # have the additional task.
                        # The following await will not take more or less than
                        # approximately self.parameters.loop_sleep_time.

                        await asyncio.wait(
                            [
                                loop_sleep_task,
                                targets_queue_condition_task,
                            ],
                            timeout=self.parameters.loop_sleep_time,
                        )

            except asyncio.CancelledError:
                break
            except UnableToFindTargetError:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=UNABLE_TO_FIND_TARGET,
                        report=f"Unable to find target in the next {self.max_time_no_target/60./60.} hours.",
                        traceback=traceback.format_exc(),
                    )
                break
            except UpdateTelemetryError:
                if self.summary_state != salobj.State.FAULT:
                    self.log.exception("Failed to update telemetry.")
                    await self.fault(
                        code=UPDATE_TELEMETRY_ERROR,
                        report="Failed to update telemetry.",
                        traceback=traceback.format_exc(),
                    )
                break
            except FailedToQueueTargetsError:
                if self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=PUT_ON_QUEUE,
                        report="Could not add target to the queue",
                        traceback=traceback.format_exc(),
                    )
                break
            except Exception:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=ADVANCE_LOOP_ERROR,
                        report="Error on advance target production loop.",
                        traceback=traceback.format_exc(),
                    )
                self.log.exception("Error on advance target production loop.")
                break

    @property
    def need_to_generate_target_queue(self) -> bool:
        """Check if we need to generate target queue.

        The condition in which we have to generate a target queue is when the
        `targets_queue_condition` future is done and its result is `None`. If
        the future is not done, the task that checks the queue is still
        ongoing. If the results is different than `None` it means the queue is
        ok and it does not need to be generated.

        Note that this is also the initial condition, so the target list is
        generated the first time the loop runs.

        Returns
        -------
        `bool`
            `True` if we need to call generate target queue, `False` otherwise.
        """
        return (
            self.targets_queue_condition.done()
            and self.targets_queue_condition.result() is None
        )

    @set_detailed_state(detailed_state=DetailedState.GENERATING_TARGET_QUEUE)
    async def generate_target_queue(self):
        """Generate target queue.

        This method will save the current state of the scheduler, play the
        scheduler for the future, generating a list of observations.
        """

        async with self.current_scheduler_state(publish_lfoa=True):

            self.log.debug(f"Target queue contains {len(self.targets_queue)} targets.")

            async for observatory_time, wait_time, target in self.model.generate_target_queue(
                targets_queue=self.targets_queue,
                max_targets=self.parameters.n_targets + 1,
            ):
                self.targets_queue.append(target)

                await self._publish_time_to_next_target(
                    current_time=observatory_time,
                    wait_time=wait_time,
                    ra=target.ra,
                    dec=target.dec,
                    rot_sky_pos=target.ang,
                )

            if len(self.targets_queue) > 0:
                self._should_compute_predicted_schedule = True
                await self.reset_handle_no_targets_on_queue()
            elif len(self.targets_queue) == 0:
                await self.handle_no_targets_on_queue()

        await self.check_targets_queue_condition()

        self.log.debug(f"Generated queue with {len(self.targets_queue)} targets.")

    async def check_targets_queue_condition(self):
        """Check targets queue condition.

        For now the check is only verifying if more targets need to be added
        to the internal queue. In the future this method will be responsible
        for verifying that the predicted schedule is still fine and requesting
        a re-scheduling if needed.
        """
        if self.targets_queue_condition.done():
            self.targets_queue_condition = asyncio.Future()

        if len(self.targets_queue) == 0:
            self.targets_queue_condition.set_result(None)

    async def save_scheduler_state(self, publish_lfoa):
        """Save scheduler state to S3 bucket and publish event.

        Parameters
        ----------
        publish_lfoa : `bool`
            Publish current state to large file annex?

        Returns
        -------
        `str`
            Path to the current scheduler state snapshot.
        """

        file_object, saved_scheduler_state_filename = self.model.get_state()

        if publish_lfoa:
            scheduler_state_filename = "last_scheduler_state.p"
            try:
                await self._handle_lfoa(file_object=file_object)
            except Exception:
                self.log.exception(
                    f"Could not upload file to S3 bucket. Keeping file {saved_scheduler_state_filename}."
                )
                return shutil.copy(
                    saved_scheduler_state_filename, scheduler_state_filename
                )
            else:
                return shutil.move(
                    saved_scheduler_state_filename, scheduler_state_filename
                )

        else:
            return saved_scheduler_state_filename

    async def _handle_lfoa(self, file_object):
        """Handle publishing large file object available (LFOA)."""

        key = self.s3bucket.make_key(
            salname=self.salinfo.name,
            salindexname=self.salinfo.index,
            generator=f"{self.salinfo.name}:{self.salinfo.index}",
            date=utils.astropy_time_from_tai_unix(utils.current_tai()),
            suffix=".p",
        )

        await self.s3bucket.upload(fileobj=file_object, key=key)

        url = f"{self.s3bucket.service_resource.meta.client.meta.endpoint_url}/{self.s3bucket.name}/{key}"

        await self.evt_largeFileObjectAvailable.set_write(
            url=url, generator=f"{self.salinfo.name}:{self.salinfo.index}"
        )

    async def handle_no_targets_on_queue(self):
        """Handle condition when there are no more targets on the queue."""
        if self._no_target_handled:
            self.log.debug(
                "No targets condition already handled, "
                "estimating time to next target."
            )
        else:
            self.log.warning(
                "Handling no targets on queue condition. "
                "This consist of queuing a stop tracking script and estimating "
                "the time until the next target."
            )

            self._no_target_handled = True

            stop_tracking_target = self.model.get_stop_tracking_target()

            await self.put_on_queue([stop_tracking_target])

        await self.estimate_next_target()

    async def reset_handle_no_targets_on_queue(self):
        """Reset conditions that no targets on queue were handled."""
        self._no_target_handled = False
        await self.stop_next_target_timer_task()

    async def estimate_next_target(self):
        """Estimate how long until the next target become available."""

        if not self.next_target_timer.done():
            self.log.warning(
                "Next target timer not done. Skipping estimate next target."
            )
            return

        (
            time_evaluation,
            time_start,
            targets,
        ) = await self.model.generate_targets_in_time_window(
            max_targets=1, time_window=self.max_time_no_target
        )

        if len(targets) == 0:
            raise UnableToFindTargetError(
                f"Could not determine next target in allotted window: {self.max_time_no_target}s."
            )
        else:
            delta_time = time_evaluation - time_start
            self.log.debug(f"Next target: {targets[0]}.")

            await self._publish_time_to_next_target(
                current_time=time_evaluation,
                wait_time=delta_time,
                ra=targets[0].ra,
                dec=targets[0].dec,
                rot_sky_pos=targets[0].ang,
            )

            if delta_time > self.parameters.loop_sleep_time:
                self.log.info(
                    f"Next target will be observable in {delta_time}s. Creating timer task."
                )
                self.next_target_timer = asyncio.create_task(
                    asyncio.sleep(delta_time / 2)
                )
            else:
                self.log.info(
                    f"Next target will be observable in {delta_time}s, "
                    f"less than looptime ({self.parameters.loop_sleep_time}s). Skip creating timer task."
                )

            return delta_time

    @set_detailed_state(detailed_state=DetailedState.COMPUTING_PREDICTED_SCHEDULE)
    async def compute_predicted_schedule(self):
        """Compute the predicted schedule.

        This method will start from the current time, play any target in the
        queue, then compute targets for the next
        config.predicted_scheduler_window hours.
        """

        if not hasattr(self, "evt_predictedSchedule"):
            self.log.debug("No support for predicted scheduler.")
            return

        self.log.info("Computing predicted schedule.")

        self._should_compute_predicted_schedule = False

        async with self.current_scheduler_state(publish_lfoa=False):

            self.model.synchronize_observatory_model()
            self.model.register_scheduled_targets(targets_queue=self.targets_queue)

            (_, _, targets,) = await self.model.generate_targets_in_time_window(
                max_targets=self.max_predicted_targets,
                time_window=self.parameters.predicted_scheduler_window * 60.0 * 60.0,
            )

            targets_info = [
                dataclasses.asdict(target.get_observation()) for target in targets
            ]

            extra_nans = [np.nan] * (self.max_predicted_targets - len(targets))

            predicted_schedule = dict(
                [
                    (
                        param,
                        np.array(
                            [target[param] for target in targets_info] + extra_nans
                        ),
                    )
                    for param in OBSERVATION_NAMED_PARAMETERS
                    if param
                    not in {
                        "targetId",
                    }
                ]
            )

            predicted_schedule["numberOfTargets"] = len(targets_info)
            predicted_schedule["instrumentConfiguration"] = ",".join(
                predicted_schedule.pop("filter")[
                    : predicted_schedule["numberOfTargets"]
                ]
            )

            await self.evt_predictedSchedule.set_write(**predicted_schedule)

        self.log.debug("Finished computing predicted schedule.")

    @set_detailed_state(detailed_state=DetailedState.QUEUEING_TARGET)
    async def queue_targets(self):
        """Send targets to the script queue.

        Raises
        ------
        `FailedToQueueTargetsError`
            If fails to add target to the queue.
        """
        # Take a target from the queue
        target = self.targets_queue.pop(0)

        current_tai = utils.current_tai()

        if target.obs_time > current_tai:
            delta_t = current_tai - target.obs_time
            self.log.debug(f"Target observing time in the future. Waiting {delta_t}s")
            await asyncio.sleep(delta_t)

        await self.put_on_queue([target])

        if target.sal_index > 0:
            self.model.add_scheduled_target(target)
        else:
            raise FailedToQueueTargetsError(
                f"Could not add target to the queue: {target}"
            )

    def assert_idle(self):
        """Assert detailed state is idle."""
        assert self.evt_detailedState.data.substate == DetailedState.IDLE, (
            "Detailed state must be IDLE, currently in "
            f"{DetailedState(self.evt_detailedState.data.substate)!r}."
        )

    def assert_running(self):
        """Assert detailed state is running."""
        assert self.evt_detailedState.data.substate == DetailedState.RUNNING, (
            "Detailed state must be RUNNING, currently in "
            f"{DetailedState(self.evt_detailedState.data.substate)!r}."
        )

    async def register_observation(self, target: DriverTarget) -> None:
        """Register observation.

        Parameters
        ----------
        observation : Observation
            Observation to be registered.
        """
        if hasattr(self, "evt_observation"):
            await self.evt_observation.set_write(
                **dataclasses.asdict(target.get_observation())
            )

    async def _publish_time_to_next_target(
        self, current_time, wait_time, ra, dec, rot_sky_pos
    ):
        """Publish next target event.

        Parameters
        ----------
        current_time : `float`
            Time when the next target was estimated.
        wait_time : `float`
            How long until the next target. This is zero if queue is operating
            normally.
        ra : `float`
            Estimated RA of the target (in degrees).
        dec : `float`
            Estimated Declination of the target (in degrees).
        rot_sky_pos : `float`
            Estimated rotation angle (in degrees).
        """

        # TODO: (DM-34905) Remove backward compatibility.
        if hasattr(self, "evt_timeToNextTarget"):
            await self.evt_timeToNextTarget.set_write(
                currentTime=current_time,
                waitTime=wait_time,
                ra=ra,
                decl=dec,
                rotSkyPos=rot_sky_pos,
            )

    async def _publish_general_info(self):
        """Publish general info event."""

        if self.evt_detailedState.data.substate == DetailedState.IDLE:
            async with self._detailed_state_lock:
                await self.model.update_telemetry()

        general_info = self.model.get_general_info()

        # TODO: (DM-34905) Remove backward compatibility.
        if hasattr(self, "evt_generalInfo"):
            await self.evt_generalInfo.set_write(**general_info)

    async def _transition_idle_to_running(self) -> None:
        """Transition detailed state from idle to running."""

        async with self._detailed_state_lock:

            self.assert_idle()

            await self.evt_detailedState.set_write(substate=DetailedState.RUNNING)

    async def _transition_running_to_idle(self) -> None:
        """Transition detailed state from idle to running."""

        async with self._detailed_state_lock:

            self.assert_running()

            await self.evt_detailedState.set_write(substate=DetailedState.IDLE)

    async def _stop_all_background_tasks(self) -> None:
        """Stop all background tasks."""

        self.log.debug(
            "Setting run loop flag to False and waiting for tasks to finish..."
        )

        # Will set flag to False so the loop will stop at the earliest
        # convenience
        self.run_target_loop.clear()
        self.run_loop = False

        await asyncio.gather(
            *[
                self._stop_background_task(task_name=task_name)
                for task_name in self._tasks
            ]
        )

    async def _stop_background_task(self, task_name) -> None:
        """Stop a background task.

        Parameters
        ----------
        task_name : str
            Name of the background task.
        """
        try:
            task = self._tasks.get(task_name)

            if task is None:
                # Nothing to do
                self.log.info(f"No {task_name} task.")
            else:
                wait_start = time.time()
                while not task.done():
                    await asyncio.sleep(self.parameters.loop_sleep_time)
                    elapsed = time.time() - wait_start
                    self.log.debug(
                        f"Waiting {task_name} to finish (elapsed: {elapsed:0.2f} s, "
                        f"timeout: {self.loop_die_timeout} s)..."
                    )
                    if elapsed > self.loop_die_timeout:
                        self.log.warning(
                            f"Task {task_name} not stopping, cancelling it..."
                        )
                        task.cancel()
                        break

                try:
                    await task
                except asyncio.CancelledError:
                    self.log.info(f"{task_name} cancelled...")
        except Exception:
            self.log.exception(
                f"Error while stopping background task {task_name}. Ignoring..."
            )
        finally:
            self._tasks[task_name] = None

    @contextlib.asynccontextmanager
    async def detailed_state(self, detailed_state):
        """Context manager to set the detailed state for an operation then
        return it to the initial value after it executes.

        This method will acquire a lock to prevent executing a detailed state
        operation inside another.

        Parameters
        ----------
        detailed_state : `DetailedState`
            Detailed state value.
        """
        async with self._detailed_state_lock:

            initial_detailed_state = self.evt_detailedState.data.substate

            self.assert_running()

            await self.evt_detailedState.set_write(substate=detailed_state)

            try:
                yield
            finally:
                await self.evt_detailedState.set_write(substate=initial_detailed_state)

    @contextlib.asynccontextmanager
    async def current_scheduler_state(self, publish_lfoa):
        """A context manager to handle storing the current scheduler state,
        performing some operations on it and then resetting it to the
        previous state.

        Parameters
        ----------
        publish_lfoa : bool
            Publish current state to large file annex?
        """

        async with self.scheduler_state_lock:

            last_scheduler_state_filename = await self.save_scheduler_state(
                publish_lfoa=publish_lfoa
            )

            try:
                yield
            finally:
                self.model.reset_state(last_scheduler_state_filename)
                shutil.os.remove(last_scheduler_state_filename)


def run_scheduler() -> None:
    """Run the Scheduler CSC."""
    asyncio.run(SchedulerCSC.amain(index=True))
