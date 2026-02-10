# This file is part of ts_scheduler.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = [
    "SchedulerCSC",
    "run_scheduler",
]

import asyncio
import contextlib
import dataclasses
import functools
import os
import shutil
import subprocess
import time
import traceback
import types
import typing
import uuid
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import yaml
from lsst.ts import salobj, utils
from lsst.ts.astrosky.model import version as astrosky_version
from lsst.ts.dateloc import version as dateloc_version

try:
    from lsst.ts.observatory.model import version as obs_mod_version
except ImportError:
    obs_mod_version = types.SimpleNamespace(__version__="?")

from lsst.ts.observing import ObservingBlock, ObservingScript
from lsst.ts.xml.enums import Scheduler, ScriptQueue
from rubin_scheduler import __version__ as rubin_scheduler_version

from . import CONFIG_SCHEMA, __version__
from .driver.driver_target import DriverTarget
from .exceptions.exceptions import (
    FailedToQueueTargetsError,
    InvalidStatusError,
    NonConsecutiveIndexError,
    TargetScriptFailedError,
    UnableToFindTargetError,
    UpdateStatusError,
    UpdateTelemetryError,
)
from .model import Model
from .utils.csc_utils import (
    OBSERVATION_NAMED_PARAMETERS,
    BlockStatus,
    DetailedState,
    SchedulerModes,
    SchedulerObservatoryStatus,
    set_detailed_state,
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
from .utils.parameters import ObservatoryStatus, SchedulerCscParameters
from .utils.s3_utils import handle_lfoa
from .utils.types import ValidationRules


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
        - `seeing` : rubin_scheduler.site_models.SeeingModel
        - `downtime` : rubin_scheduler.site_models.DowntimeModel
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

        super().__init__(
            name="Scheduler",
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            index=index,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            extra_commands=["flush", "reschedule", "updateObservatoryStatus"],
        )

        self._queue_name = f"scriptqueue:{index}"
        self._ptg_name = ("mtptg" if index % 2 == 1 else "atpg",)

        self._remotes = dict()

        self._remotes[self._queue_name] = salobj.Remote(
            self.domain,
            "ScriptQueue",
            index=index,
            include=["script", "queue", "configSchema", "summaryState"],
        )

        self._remotes[self._ptg_name] = salobj.Remote(
            self.domain,
            "MTPtg" if index % 2 == 1 else "ATPtg",
            include=["currentTargetStatus", "summaryState"],
        )

        self._current_instrument_name = None

        self.no_observatory_state_warning = False

        self.parameters = SchedulerCscParameters()
        self.filter_band_mapping = dict()
        self.filter_names_separator = ","

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
        self.telemetry_in_sync = asyncio.Event()

        # Lock for the event loop. This is used to synchronize actions that
        # will affect the target production loop.
        self.target_loop_lock = asyncio.Lock()

        self.scheduler_state_lock = asyncio.Lock()

        self._detailed_state_lock = asyncio.Lock()

        # Semaphore to limit the number of scripts added to the ScriptQueue.
        self._max_queue_capacity = 10
        self._queue_capacity = asyncio.Semaphore(self._max_queue_capacity)

        # dictionary to store background tasks
        self._tasks = dict()

        # Stores the coroutine for the target production.
        self._tasks["target_production_task"] = None

        # A flag to indicate that the event loop is running
        self.run_loop = False

        # Telemetry loop. This will take care of observatory state.
        self._tasks["telemetry_loop_task"] = None

        # List of targets used in the ADVANCE target loop
        self.targets_queue: list[DriverTarget] = []

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

        # Path to the standard and external scripts. This is used
        # to validate blocks. If not defined it will fallback to
        # request from the ScriptQueue.
        self.script_paths = None

        self.model = Model(log=self.log, config_dir=self.config_dir)

        # Add callback to script info
        self.queue_remote.evt_script.callback = self.check_script_info

        # Future to store the task to monitor observatory status.
        self._observatory_status_task = utils.make_done_future()

        # Dictionary to store the state of the components
        # being monitored for observatory status.
        self._components_summary_state = dict()

        self.max_status = 0
        for observatory_status in SchedulerObservatoryStatus:
            self.max_status = self.max_status ^ observatory_status

        self.enable_observatory_status_monitor = False

    @property
    def queue_remote(self):
        """Access the remote for the script queue."""
        return self._remotes[self._queue_name]

    @property
    def ptg(self):
        """Access the remote for the pointing component."""
        return self._remotes[self._ptg_name]

    @property
    def camera(self):
        """Access the remote for the camera."""
        return (
            self._remotes.get(self._current_instrument_name, None)
            if self._current_instrument_name is not None
            else None
        )

    async def start(self):
        """Override the start method to publish some additional events
        at startup time.
        """

        await super().start()
        await self.set_observatory_status(
            status=SchedulerObservatoryStatus.UNKNOWN,
            note=(
                "Scheduler CSC started; "
                "need to be in DISABLED or ENABLED to monitor observatory status."
            ),
        )

    async def close(self):
        await super().close()
        self.model.close()

    async def begin_start(self, data):
        self.log.info("Starting Scheduler CSC...")

        self._tasks["ack_in_progress_task"] = asyncio.create_task(
            self._cmd_start_ack_in_progress(data)
        )

        try:
            await asyncio.sleep(self.heartbeat_interval * 2.0)
            await super().begin_start(data)
        except Exception:
            self.log.exception("Error in begin start")
            self._tasks["ack_in_progress_task"].cancel()
            raise

    async def end_start(self, data):
        self._tasks["ack_in_progress_task"].cancel()

        try:
            await self._tasks["ack_in_progress_task"]
        except asyncio.CancelledError:
            pass
        except Exception:
            self.log.exception("Error stopping ack in progress task.")
        finally:
            self._tasks.pop("ack_in_progress_task", None)

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

        self.log.info("Enabling Scheduler CSC...")
        self.telemetry_in_sync.clear()

        await asyncio.sleep(self.heartbeat_interval / 2.0)

        await self.cmd_enable.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result="Enabling CSC.",
        )

        await self._start_target_production_task()

    async def _start_target_production_task(self):
        """Start target production task.

        Raises
        ------
        RuntimeError
            If scheduler mode is not recognized.
        """
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

        elif self.summary_state == salobj.State.STANDBY:
            self.enable_observatory_status_monitor = False
            await self._stop_all_background_tasks()
            for component in self.parameters.observatory_status.components_to_monitor:
                component_reference_name = component.lower()
                if component_reference_name not in self._remotes:
                    components_list = ",".join(self._remotes.keys())
                    self.log.warning(
                        f"{component_reference_name} not in the list of remotes. "
                        f"Must be one of: {components_list}."
                    )
                else:
                    self._remotes[
                        component_reference_name
                    ].evt_summaryState.callback = None
            await self.set_observatory_status(
                status=SchedulerObservatoryStatus.UNKNOWN,
                note=(
                    "Scheduler CSC in STANDBY; "
                    "need to be in DISABLED or ENABLED to monitor observatory status."
                ),
            )

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

        await asyncio.sleep(self.heartbeat_interval / 2)

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

        async with self.target_loop_lock:
            if self.run_target_loop.is_set():
                raise RuntimeError("Target production loop already running.")

            self.log.info("Resuming Scheduler operations...")

            await asyncio.sleep(self.heartbeat_interval)

            await self.cmd_resume.ack_in_progress(
                data,
                timeout=self.default_command_timeout,
                result="Resuming Scheduler operation.",
            )

            target_production_task = self._tasks.get(
                "target_production_task", utils.make_done_future()
            )

            if target_production_task is not None and target_production_task.done():
                self.log.warning("Target production task not running. Starting it.")
                await self._start_target_production_task()

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

        await asyncio.sleep(self.heartbeat_interval / 2)

        await self.cmd_stop.ack_in_progress(
            data,
            timeout=self.default_command_timeout * 2.0,
            result="Stopping Scheduler execution.",
        )

        self.run_target_loop.clear()

        self.log.info("Waiting for target loop execution.")

        try:
            await asyncio.wait_for(
                self.stop_target_loop_execution(),
                timeout=self.loop_die_timeout,
            )
        except asyncio.TimeoutError:
            self.log.info("Timeout waiting for the target loop to stop. Cancelling it.")
            await self.cmd_stop.ack_in_progress(
                data,
                timeout=self.default_command_timeout + self.heartbeat_interval,
                result="Stopping target production task.",
            )
            await self._stop_background_task("target_production_task")
            await self._cleanup_queue_targets()
            await self.reset_handle_no_targets_on_queue()
            await self._transition_running_to_idle()
            await self._start_target_production_task()

        self.log.info(
            f"Cleaning up targets queue. Discarding {len(self.targets_queue)} targets."
        )
        self.targets_queue = []

    async def stop_target_loop_execution(self) -> None:
        """Stop target production loop execution."""
        async with self.target_loop_lock:
            self.log.info("Stopping scheduler.")

            await self._cleanup_queue_targets()

            await self.reset_handle_no_targets_on_queue()

            await self._transition_running_to_idle()

    async def _cleanup_queue_targets(self) -> None:
        """Cleanup queued targets."""
        scheduled_targets = self.model.get_scheduled_targets()
        for target in scheduled_targets:
            await self.model.mark_block_done(target.get_observing_block().id)
            await self.model.remove_block_done_scripts(target.get_observing_block().id)
        self.model.reset_scheduled_targets()
        await self.remove_from_queue(scheduled_targets)

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

    async def do_computePredictedSchedule(self, data):
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

        async with self.idle_to_running():
            self._tasks["compute_predicted_schedule"] = asyncio.create_task(
                self.compute_predicted_schedule()
            )
            await self._tasks["compute_predicted_schedule"]

    async def do_addBlock(self, data):
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

        await self.cmd_addBlock.ack_in_progress(
            data,
            timeout=self.default_command_timeout,
            result=f"Adding block {data.id}.",
        )

        if data.id not in self.model.observing_blocks:
            observing_blocks = ",".join(self.model.observing_blocks)
            raise salobj.ExpectedError(
                f"Block {data.id} is not in the list of observing blocks. "
                f"Current observing blocks are: {observing_blocks}."
            )
        elif data.id not in (
            valid_observing_blocks := self.model.get_valid_observing_blocks()
        ):
            valid_blocks = ",".join(valid_observing_blocks)
            raise salobj.ExpectedError(
                f"Block {data.id} is not in the list of valid blocks. "
                f"Current valid blocks are: {valid_blocks}."
            )

        obs_block = self.model.observing_blocks[data.id].dict()
        obs_block.pop("id")
        block_target = DriverTarget(
            observing_block=ObservingBlock(
                **obs_block,
            ),
            block_configuration=yaml.safe_load(data.override),
            log=self.log,
        )

        await self._update_block_status(
            data.id, BlockStatus.STARTED, block_target.get_observing_block()
        )

        async with self.target_loop_lock:
            self.log.debug(f"Queueing block target: {block_target!s}.")

            if not self.run_target_loop.is_set():
                self.log.warning(
                    "Target production loop is not running. "
                    "Inserting block at the top of the queue and executing."
                )
                task_name = f"block-{block_target.observing_block.id}"
                if task_name in self._tasks and not self._tasks[task_name].done():
                    RuntimeError(
                        f"A Block with the same id is already executing: {task_name}."
                    )
                self.targets_queue.insert(0, block_target)
                self._tasks[task_name] = asyncio.create_task(self.execute_block())
            else:
                self.log.info("Scheduler is running, appending target to the queue.")
                self.targets_queue.append(block_target)

    async def _update_block_status(
        self,
        block_id: str,
        block_status: BlockStatus,
        observing_block: ObservingBlock,
    ) -> None:
        if block_id not in self.model.observing_blocks_status:
            self.log.warning(
                f"Block {block_id} not in list of observing blocks. Ignoring."
            )
            return
        self.model.observing_blocks_status[block_id].status = block_status
        if block_status == BlockStatus.COMPLETED:
            self.model.observing_blocks_status[block_id].executions_completed += 1

        # publish block event
        await self.evt_blockStatus.set_write(
            id=block_id,
            statusId=block_status.value,
            status=block_status.name,
            executionsCompleted=self.model.observing_blocks_status[
                block_id
            ].executions_completed,
            executionsTotal=self.model.observing_blocks_status[
                block_id
            ].executions_total,
            hash=str(observing_block.id),
            definition=observing_block.json(),
        )

    async def do_getBlockStatus(self, data):
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

    async def do_removeBlock(self, data):
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

    async def do_validateBlock(self, data):
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

    async def do_flush(self, data):
        """Implement validate flush command.

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

    async def do_reschedule(self, data):
        """Implement validate reschedule command.

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

    async def do_updateObservatoryStatus(self, data):
        """Implement the update observatory status command.

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
        self.validate_observatory_status(data.status)
        note = self.generate_status_note(user_note=data.note)
        await self.set_observatory_status(
            status=data.status,
            note=note,
        )

    async def telemetry_loop(self):
        """Scheduler telemetry loop.

        This method will monitor and process the observatory state and publish
        the information to SAL.

        """

        failed_observatory_state_logged = False
        while self.run_loop:
            # Update observatory state and sleep at the same time.
            timer_task = asyncio.create_task(asyncio.sleep(self.heartbeat_interval))
            try:
                await self.handle_observatory_state()
                failed_observatory_state_logged = False
            except Exception:
                self.telemetry_in_sync.clear()
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
            else:
                self.telemetry_in_sync.set()

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

            await self._cleanup_script_tasks()

            await timer_task

    async def _cleanup_script_tasks(self) -> None:
        """Cleanup completed script tasks."""
        script_tasks_done = [
            task_name
            for task_name in self._tasks
            if "script_task" in task_name
            and self._tasks[task_name] is not None
            and self._tasks[task_name].done()
        ]
        if len(script_tasks_done) > self.parameters.max_scripts:
            self.log.debug(
                f"Cleaning up {self.parameters.max_scripts} done script tasks."
            )
            for script_task in script_tasks_done[: self.parameters.max_scripts]:
                del self._tasks[script_task]

    async def handle_observatory_state(self):
        """Handle observatory state."""

        current_target_state = await self.ptg.tel_currentTargetStatus.next(
            flush=True, timeout=self.loop_die_timeout
        )
        current_filter = None
        mounted_filters = None
        if self.salinfo.index % 2 == 1 and self.camera is not None:
            try:
                current_filter = (
                    await self.camera.evt_endSetFilter.aget(
                        timeout=self.loop_die_timeout
                    )
                ).filterName
                if self.filter_band_mapping:
                    if current_filter not in self.filter_band_mapping:
                        mapped_filters = ",".join(self.filter_band_mapping.keys())
                        raise ValueError(
                            f"Filter {current_filter} not in the filter band mapping: {mapped_filters}."
                        )
                    current_filter = self.filter_band_mapping[current_filter]
            except asyncio.TimeoutError:
                self.log.warning("Could not get current camera filter.")
            try:
                mounted_filters = (
                    await self.camera.evt_availableFilters.aget(
                        timeout=self.loop_die_timeout
                    )
                ).filterNames.split(self.filter_names_separator)
                if self.filter_band_mapping:
                    missing_filter_map = set(mounted_filters).difference(
                        set(self.filter_band_mapping)
                    )
                    if missing_filter_map:
                        raise ValueError(
                            "The following filters are missing in the filter map configuration: "
                            f"{missing_filter_map}."
                        )
                    mounted_filters = [
                        self.filter_band_mapping[filter_name]
                        for filter_name in mounted_filters
                    ]
            except asyncio.TimeoutError:
                self.log.warning("Could not get available filters.")

        self.model.set_observatory_state(
            current_target_state=current_target_state,
            current_filter=current_filter,
            mounted_filters=mounted_filters,
        )

    async def put_on_queue(self, targets: list[DriverTarget]) -> None:
        """Given a list of targets, append them on the queue to be observed.
        Each target sal_index attribute is updated with the unique identifier
        value (salIndex) returned by the queue.


        Parameters
        ----------
        targets : `list` [`DriverTarget`]
            A list of targets to put on the queue.
        """

        for target in targets:
            observing_block = target.get_observing_block()

            self.log.info(f"Adding {target=!s} scripts on the queue.")

            self.model.register_new_block(id=observing_block.id)
            initial_sal_index = None
            async for sal_index in self._queue_block_scripts(observing_block):
                self.log.info(f"{observing_block.name}::{sal_index=}.")
                if initial_sal_index is None:
                    initial_sal_index = sal_index
                try:
                    target.add_sal_index(sal_index)
                except NonConsecutiveIndexError:
                    self.log.exception(
                        f"Non consecutive salindex for block {observing_block.name}::{observing_block.id}. "
                        "Marking block as failed."
                    )
                    await self.remove_from_queue(targets=[target])
                    await self._update_block_status(
                        block_id=observing_block.program,
                        block_status=BlockStatus.ERROR,
                        observing_block=observing_block,
                    )
                    return
                finally:
                    await asyncio.sleep(self.heartbeat_interval)

            # publishes target event
            target_data = target.as_dict()
            target_data["blockId"] = initial_sal_index
            await self.evt_target.set_write(**target_data)

            await self._update_block_status(
                block_id=observing_block.program,
                block_status=BlockStatus.EXECUTING,
                observing_block=observing_block,
            )

    async def _queue_block_scripts(
        self, observing_block: ObservingBlock
    ) -> typing.Generator[int, None, None]:
        """Queue block scripts in the ScriptQueue.

        Parameters
        ----------
        observing_block : `ObservingBlock`
            Observing block to queue scripts from.

        Yields
        ------
        sal_index : `int`
            A sequence of SAL indices of Scripts.

        Notes
        -----
        This method will use `_queue_one_script` to queue the scripts by
        creating a list of background tasks and waiting for them to finish.
        The background tasks will acquire a semaphore that will limit the
        number of consecutive scripts running in the ScriptQueue. If the limit
        is not met, the method will return soon after all scripts are
        scheduled. If the limit is reached, the method will block and only
        make progress once the scripts finish executing.
        """
        start_block = True
        block_size = len(observing_block.scripts)
        for script in observing_block.scripts:
            sal_index = await self._queue_one_script(
                block_uid=observing_block.id,
                script=script,
                block_name=observing_block.program,
                start_block=start_block,
                block_size=block_size,
            )
            start_block = False
            yield sal_index

    async def _queue_one_script(
        self,
        block_uid: uuid.UUID,
        script: ObservingScript,
        block_name: str,
        start_block: bool,
        block_size: int,
    ) -> int:
        """Queue one script to the script queue.

        Parameters
        ----------
        block_uid : `uuid.UUID`
            The uid of the block.
        script : `ObservingScript`
            Observing script to queue.
        block_name : `str`
            Name of the block (e.g. BLOCK-1).
        start_block : `bool`
            Start a new block?
            Should be `True` for the first script of a block,
            `False` otherwise.
        block_size : `int`
            How many scripts are part of this block?

        Returns
        -------
        sal_index : `int`
            SAL index of the script.

        Notes
        -----
        This method will acquire the semaphore that limits the number of
        scripts that can be queued, add a script to the script queue and
        schedule a background task that will also acquire the semaphore and
        wait for the script to finish.

        If a script execution fails, this raises an exception that is then
        propagated to this method call, and will interrupt adding further
        scripts.
        """
        async with self._queue_capacity:
            # Make sure previous scripts added haven't failed, if one
            # failed this will raise an exception and stop adding more
            # scripts
            await self.model.check_block_scripts(id=block_uid)
            n_retries = 3
            for retry in range(n_retries):
                try:
                    add_task = await self.queue_remote.cmd_add.set_start(
                        path=script.name,
                        config=script.get_script_configuration(),
                        isStandard=script.standard,
                        location=ScriptQueue.Location.LAST,
                        logLevel=self.log.getEffectiveLevel(),
                        block=block_name,
                        blockSize=block_size,
                        startBlock=start_block,
                        timeout=self.parameters.cmd_timeout,
                    )
                    break
                except salobj.AckError as ack:
                    if "Bad Gateway" in ack.ackcmd.result:
                        self.log.warning(
                            f"Failed to add script to queue due to name server error: {ack!r}. "
                            f"Waiting {self.heartbeat_interval*(retry+1)}s and trying again. "
                            f"Attempt {retry+1} of {n_retries}."
                        )
                        await asyncio.sleep(self.heartbeat_interval * (retry + 1))
                    else:
                        raise
            else:
                raise RuntimeError(
                    "Failed to add scripts to the script queue. "
                    "This is usually related to the camera name server not working correctly "
                    "as the ScriptQueue used it to query for block ids. "
                    "Contact support from camera team."
                )
            sal_index = int(add_task.result)
            script_final_state_future = await self.model.add_scheduled_script(
                id=block_uid, sal_index=sal_index
            )
            self._tasks[f"script_task::{block_uid}::{sal_index}"] = asyncio.create_task(
                self._wait_script_final_state(script_final_state_future)
            )
        return sal_index

    async def _wait_script_final_state(
        self, script_final_state: asyncio.Future
    ) -> None:
        """Coroutine to acquire the queue semaphore and wait for a script to
        finish executing.

        Parameters
        ----------
        script_final_state : `asyncio.Future`
            Future with the script final state.
        """
        async with self._queue_capacity:
            self.log.trace("Waiting Script final state.")
            await script_final_state
            self.log.trace(f"Script final state: {script_final_state.result()!r}")

    async def remove_from_queue(self, targets: list[DriverTarget]) -> None:
        """Given a list of targets, remove them from the queue.

        Parameters
        ----------
        targets: `list`
            A list of targets to put on the queue.

        """

        sal_indices_to_remove = [target.get_sal_indices() for target in targets]

        # exclude the script that is currently running.
        queue = await self.queue_remote.evt_queue.aget(
            timeout=self.parameters.cmd_timeout
        )

        current_sal_index = queue.currentSalIndex

        scripts_to_stop = [
            sal_index
            for sal_indices in sal_indices_to_remove
            for sal_index in sal_indices
            if sal_index != current_sal_index
        ]

        stop_scripts = self.queue_remote.cmd_stopScripts.DataType()

        stop_scripts.length = len(scripts_to_stop)
        stop_scripts.terminate = False

        for i, sal_index in enumerate(scripts_to_stop):
            stop_scripts.salIndices[i] = sal_index

        if stop_scripts.length > 0:
            await self.queue_remote.cmd_stopScripts.start(
                stop_scripts, timeout=self.parameters.cmd_timeout
            )

        for target in targets:
            await self.model.mark_block_done(target.get_observing_block().id)

    @staticmethod
    def get_config_pkg():
        return "ts_config_scheduler"

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

        self.script_paths = getattr(config, "script_paths", None)

        instance = Scheduler.SalIndex(self.salinfo.index)

        if instance == Scheduler.SalIndex.MAIN_TEL:
            settings = types.SimpleNamespace(**config.maintel)
        elif instance == Scheduler.SalIndex.AUX_TEL:
            settings = types.SimpleNamespace(**config.auxtel)
        elif hasattr(config, instance.name.lower()):
            settings = types.SimpleNamespace(**getattr(config, instance.name.lower()))
        else:
            available_instances = [i for i in dir(config) if not i.startswith("__")]
            raise RuntimeError(
                "Could not find configuration for current instance of the Scheduler. "
                f"This instance has index {self.salinfo.index}, "
                f"which is labeled {instance.name}. Expected to find a configuration"
                f"session named {instance.name.lower()} but only found "
                f"{available_instances}. Make sure the configuration is updated to include "
                "a session for this instance of the Scheduler."
            )

        self.log.info(f"Settings for {instance!r}: {settings}")

        if hasattr(settings, "instrument_name"):
            self._current_instrument_name = settings.instrument_name.lower()
            if settings.instrument_name in {"MTCamera", "CCCamera"}:
                self.log.info(
                    f"Starting remote for {settings.instrument_name} to update instrument configuration."
                )
                if self._current_instrument_name not in self._remotes:
                    self._remotes[self._current_instrument_name] = salobj.Remote(
                        self.domain,
                        settings.instrument_name,
                        include=["endSetFilter", "availableFilters"],
                        readonly=True,
                    )
                    await self.camera.start_task
                else:
                    self.log.info(
                        f"Remote for {settings.instrument_name} already created."
                    )

        self.parameters.driver_type = settings.driver_type
        self.parameters.startup_type = settings.startup_type
        self.parameters.startup_database = settings.startup_database
        self.parameters.mode = settings.mode
        self.parameters.n_targets = settings.n_targets
        self.parameters.predicted_scheduler_window = settings.predicted_scheduler_window
        self.parameters.loop_sleep_time = settings.loop_sleep_time
        self.parameters.cmd_timeout = settings.cmd_timeout
        self.parameters.max_scripts = settings.max_scripts
        self.parameters.observatory_status = ObservatoryStatus(
            **settings.observatory_status
        )
        if self.parameters.observatory_status.enable:
            if not hasattr(self, "evt_observatoryStatus"):
                raise salobj.ExpectedError(
                    "CSC interface does not support observatory status. "
                    "Ensure 'observatory_status.enable: false' in the configuration."
                )
            await self.set_observatory_status(
                status=SchedulerObservatoryStatus.UNKNOWN,
                note=(
                    "Observatory status feature enabled; "
                    "observatory status will be monitored and updated while "
                    "CSC is in DISABLED or ENABLED."
                ),
            )
            if not self._observatory_status_task.done():
                self.log.info("Observatory status task still running. Cancelling it.")
                self._observatory_status_task.cancel()
                try:
                    await self._observatory_status_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    self.log.info(
                        "Skipping exception while waiting for observatory status task to finish.",
                        exc_info=True,
                    )
            self.enable_observatory_status_monitor = True
            self._observatory_status_task = asyncio.create_task(
                self.monitor_observatory_status()
            )
        else:
            self.enable_observatory_status_monitor = False
            await self.set_observatory_status(
                status=SchedulerObservatoryStatus.UNKNOWN,
                note="Observatory status feature disabled; will not monitor observatory status.",
            )

        self.filter_band_mapping = getattr(settings, "filter_band_mapping", dict())
        self.filter_names_separator = getattr(
            settings, "filter_names_separator", self.filter_names_separator
        )

        survey_topology = await self.model.configure(settings)

        await self.evt_surveyTopology.set_write(**survey_topology.as_dict())

        self.log.info("Validating observing blocks.")

        try:
            await self.validate_observing_blocks()
        except Exception:
            self.log.exception("Failed to validate observing blocks.")
            raise RuntimeError(
                "Failed to validate observing blocks. Check CSC traceback for more information."
            )

        # Most configurations comes from this single commit hash. I think the
        # other modules could host the version for each one of them
        if hasattr(self, "evt_dependenciesVersions"):
            await self.evt_dependenciesVersions.set_write(
                version="",
                scheduler=self.parameters.driver_type,
                observatoryModel=obs_mod_version.__version__,
                observatoryLocation=dateloc_version.__version__,
                seeingModel=rubin_scheduler_version,
                cloudModel=rubin_scheduler_version,
                skybrightnessModel=astrosky_version.__version__,
                downtimeModel=rubin_scheduler_version,
                force_output=True,
            )
        else:
            self.log.warning("No 'dependenciesVersions' event.")

        await self._publish_settings(settings)

    async def validate_observing_blocks(self) -> None:
        """Validate observing blocks.

        Notes
        -----
        This method will walk through the observing blocks defined in the model
        and validate their configuration. This includes validating the script
        configuration.
        """

        observing_scripts_config_validator = (
            await self.get_observing_scripts_config_validator()
        )

        await self.model.validate_observing_blocks(observing_scripts_config_validator)

        await self._publish_block_info()

    async def get_observing_scripts_config_validator(
        self,
    ) -> ValidationRules:
        """Get observing scripts configuration validator.

        Returns
        -------
        observing_scripts_config_validator : `ValidationRules`
            Dictionary with the script name and a boolean indicating if the
            script is standard or external as key and a configuration
            validator as value.
        """
        observing_scripts_config_validator: ValidationRules = dict()

        for block_id in self.model.observing_blocks:
            for script in self.model.observing_blocks[block_id].scripts:
                key = (script.name, script.standard)
                if key not in observing_scripts_config_validator:
                    observing_scripts_config_validator[key] = await asyncio.wait_for(
                        self._get_script_config_validator(
                            script_name=script.name, standard=script.standard
                        ),
                        timeout=self.parameters.cmd_timeout,
                    )

        return observing_scripts_config_validator

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

    async def check_script_info(self, data: salobj.BaseDdsDataType) -> None:
        """A callback method to check script info.

        This method will first update the model with the incoming script info
        then check the scheduled targets. This should allow the Scheduler to
        cleanup remaining scripts from the ScriptQueue when one Script of
        a block fails.

        Parameters
        ----------
        data : `BaseDdsDataType`
            Script info topic data.
        """
        await self.model.callback_script_info(data=data)

        task_name = "lock_target_loop_and_check_targets"

        task = self._tasks.get(task_name, utils.make_done_future())

        if task.done():
            self._tasks[task_name] = asyncio.create_task(
                self.lock_target_loop_and_check_targets()
            )

    async def lock_target_loop_and_check_targets(self):
        async with self.target_loop_lock:
            await self.check_scheduled_targets()

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
            self.log.info("No scheduled targets to check.")
            return False
        scheduled_targets_info = await self.model.check_scheduled_targets()

        for target in scheduled_targets_info.observed:
            await self.register_observation(target)

        if len(scheduled_targets_info.failed) > 0:
            await self.remove_from_queue(scheduled_targets_info.failed)
            for target in scheduled_targets_info.failed:
                observing_block = target.get_observing_block()
                await self._update_block_status(
                    block_id=observing_block.program,
                    block_status=BlockStatus.ERROR,
                    observing_block=observing_block,
                )

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

                        if target.get_sal_indices():
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
                if self.run_loop and self.summary_state != salobj.State.FAULT:
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

        self.targets_queue: list[DriverTarget] = []
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

            await self.telemetry_in_sync.wait()
            await self.run_target_loop.wait()

            try:
                async with self.target_loop_lock:
                    if self.need_to_generate_target_queue:
                        await self.generate_target_queue()

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
                        and self.model.get_number_of_scheduled_targets()
                        < self.parameters.n_targets + 1
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

                        if not loop_sleep_task.done():
                            self.log.debug(
                                "Checking targets condition finished ahead of time. "
                                "Waiting remaining sleep time."
                            )
                            await loop_sleep_task
                        else:
                            self.log.warning(
                                "Checking targets condition took longer than expected. "
                                "Continuing without waiting."
                            )

            except asyncio.CancelledError:
                break
            except UnableToFindTargetError:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.run_loop and self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=UNABLE_TO_FIND_TARGET,
                        report=f"Unable to find target in the next {self.max_time_no_target/60./60.} hours.",
                        traceback=traceback.format_exc(),
                    )
                break
            except UpdateTelemetryError:
                if self.run_loop and self.summary_state != salobj.State.FAULT:
                    self.log.exception("Failed to update telemetry.")
                    await self.fault(
                        code=UPDATE_TELEMETRY_ERROR,
                        report="Failed to update telemetry.",
                        traceback=traceback.format_exc(),
                    )
                break
            except FailedToQueueTargetsError:
                if self.run_loop and self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=PUT_ON_QUEUE,
                        report="Could not add target to the queue",
                        traceback=traceback.format_exc(),
                    )
                break
            except Exception:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.run_loop and self.summary_state != salobj.State.FAULT:
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

        for n in range(self.parameters.n_targets + 1):

            async with self.current_scheduler_state(
                publish_lfoa=True,
                reset_state=False,
            ) as last_scheduler_state_filename:

                async for (
                    observatory_time,
                    wait_time,
                    target,
                ) in self.model.generate_target_queue():
                    target.set_snapshot_uri(self.evt_largeFileObjectAvailable.data.url)
                    target.set_scheduler_state_filename(last_scheduler_state_filename)
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
                elif (
                    len(self.targets_queue) == 0
                    and self.model.get_number_of_scheduled_targets() == 0
                ):
                    await self.handle_no_targets_on_queue()
                else:
                    self.log.info(
                        "No targets generated, but still have scheduled targets."
                    )

            await self.check_targets_queue_condition()

            if len(self.targets_queue) > self.parameters.n_targets + 1:
                self.log.info(
                    f"Target queue contains {len(self.targets_queue)}. "
                    f"Current scheduled targets: {self.model.get_number_of_scheduled_targets()}. "
                    "Stop generating targets."
                )
                break

            self.log.debug(
                f"Generated queue with {len(self.targets_queue)} targets. "
                f"Current scheduled targets: {self.model.get_number_of_scheduled_targets()}."
            )

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

        saved_scheduler_state_filename = self.model.get_state(
            targets_queue=self.targets_queue
        )

        if publish_lfoa:
            try:
                await self._handle_lfoa(saved_scheduler_state_filename)
            except Exception:
                self.log.exception(
                    f"Could not upload file to S3 bucket. Keeping file {saved_scheduler_state_filename}."
                )
        return saved_scheduler_state_filename

    async def _handle_lfoa(self, file_name):
        """Handle publishing large file object available (LFOA)."""

        with ProcessPoolExecutor(max_workers=1) as pool:
            loop = asyncio.get_running_loop()

            url = await loop.run_in_executor(
                pool,
                functools.partial(
                    handle_lfoa,
                    self.s3bucket_name,
                    self.simulation_mode == SchedulerModes.MOCKS3,
                    self.salinfo.name,
                    self.salinfo.index,
                    file_name,
                ),
            )

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

            needed_targets = max(
                [self.max_predicted_targets - len(self.targets_queue), 0]
            )

            (
                _,
                _,
                targets,
            ) = await self.model.generate_targets_in_time_window(
                max_targets=needed_targets,
                time_window=self.parameters.predicted_scheduler_window * 60.0 * 60.0,
            )

            targets_info = [
                dataclasses.asdict(target.get_observation())
                for target in self.targets_queue
            ] + [dataclasses.asdict(target.get_observation()) for target in targets]

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

    async def execute_block(self):
        """Execute an individual block when the Scheduler is not running.

        This method will transition the Scheduler from idle to running,
        queue a single target and go back to idle.
        """
        async with self.idle_to_running():
            await self.queue_targets()

    @set_detailed_state(detailed_state=DetailedState.QUEUEING_TARGET)
    async def queue_targets(self):
        """Send targets to the script queue.

        Raises
        ------
        `FailedToQueueTargetsError`
            If fails to add target to the queue.
        """
        targets_queue = "\n\t".join([f"{target!s}" for target in self.targets_queue])
        self.log.debug(f"Current targets in the queue:\n\t{targets_queue}.")
        # Take a target from the queue
        target = self.targets_queue.pop(0)

        current_tai = utils.current_tai()

        if target.obs_time > current_tai:
            delta_t = current_tai - target.obs_time
            self.log.debug(f"Target observing time in the future. Waiting {delta_t}s")
            await asyncio.sleep(delta_t)

        try:
            await self.put_on_queue([target])
        except TargetScriptFailedError:
            self.log.warning(
                "One or more scripts for this target failed to execute while still "
                "adding targets to the queue. Cleaning block scripts and continuing."
            )
            await self.remove_from_queue(targets=[target])
            await self.model.remove_block_done_scripts(target.get_observing_block().id)
        else:
            if target.get_sal_indices():
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
        await self.evt_observation.set_write(
            **dataclasses.asdict(target.get_observation()),
            force_output=True,
        )
        observing_block = target.get_observing_block()
        await self._update_block_status(
            block_id=target.observing_block.program,
            block_status=BlockStatus.COMPLETED,
            observing_block=observing_block,
        )
        await self.model.remove_block_done_scripts(observing_block.id)
        target.remove_scheduler_state()

    async def _publish_settings(self, settings) -> None:
        """Publish settings."""

        await self.evt_obsSiteConfig.set_write(
            observatoryName=settings.models["location"]["obs_site"]["name"],
            latitude=settings.models["location"]["obs_site"]["latitude"],
            longitude=settings.models["location"]["obs_site"]["longitude"],
            height=settings.models["location"]["obs_site"]["height"],
        )

        await self.evt_cameraConfig.set_write(
            readoutTime=settings.models["observatory_model"]["camera"]["readout_time"],
            shutterTime=settings.models["observatory_model"]["camera"]["shutter_time"],
            filterChangeTime=settings.models["observatory_model"]["camera"][
                "filter_change_time"
            ],
            filterMounted=",".join(
                settings.models["observatory_model"]["camera"]["filter_mounted"]
            ),
            filterRemovable=",".join(
                settings.models["observatory_model"]["camera"]["filter_removable"]
            ),
            filterUnmounted=",".join(
                settings.models["observatory_model"]["camera"]["filter_unmounted"]
            ),
        )

        await self.evt_telescopeConfig.set_write(
            altitudeMinpos=settings.models["observatory_model"]["telescope"][
                "altitude_minpos"
            ],
            altitudeMaxpos=settings.models["observatory_model"]["telescope"][
                "altitude_maxpos"
            ],
            azimuthMinpos=settings.models["observatory_model"]["telescope"][
                "azimuth_minpos"
            ],
            azimuthMaxpos=settings.models["observatory_model"]["telescope"][
                "azimuth_maxpos"
            ],
            altitudeMaxspeed=settings.models["observatory_model"]["telescope"][
                "altitude_maxspeed"
            ],
            altitudeAccel=settings.models["observatory_model"]["telescope"][
                "altitude_accel"
            ],
            altitudeDecel=settings.models["observatory_model"]["telescope"][
                "altitude_decel"
            ],
            azimuthMaxspeed=settings.models["observatory_model"]["telescope"][
                "azimuth_maxspeed"
            ],
            azimuthAccel=settings.models["observatory_model"]["telescope"][
                "azimuth_accel"
            ],
            azimuthDecel=settings.models["observatory_model"]["telescope"][
                "azimuth_decel"
            ],
            settleTime=settings.models["observatory_model"]["telescope"]["settle_time"],
        )

        await self.evt_rotatorConfig.set_write(
            positionMin=settings.models["observatory_model"]["rotator"]["minpos"],
            positionMax=settings.models["observatory_model"]["rotator"]["maxpos"],
            positionFilterChange=settings.models["observatory_model"]["rotator"][
                "filter_change_pos"
            ],
            speedMax=settings.models["observatory_model"]["rotator"]["maxspeed"],
            accel=settings.models["observatory_model"]["rotator"]["accel"],
            decel=settings.models["observatory_model"]["rotator"]["decel"],
            followSky=settings.models["observatory_model"]["rotator"]["follow_sky"],
            resumeAngle=settings.models["observatory_model"]["rotator"]["resume_angle"],
        )

        await self.evt_domeConfig.set_write(
            altitudeMaxspeed=settings.models["observatory_model"]["dome"][
                "altitude_maxspeed"
            ],
            altitudeAccel=settings.models["observatory_model"]["dome"][
                "altitude_accel"
            ],
            altitudeDecel=settings.models["observatory_model"]["dome"][
                "altitude_decel"
            ],
            altitudeFreerange=settings.models["observatory_model"]["dome"][
                "altitude_freerange"
            ],
            azimuthMaxspeed=settings.models["observatory_model"]["dome"][
                "azimuth_maxspeed"
            ],
            azimuthAccel=settings.models["observatory_model"]["dome"]["azimuth_accel"],
            azimuthDecel=settings.models["observatory_model"]["dome"]["azimuth_decel"],
            azimuthFreerange=settings.models["observatory_model"]["dome"][
                "azimuth_freerange"
            ],
            settleTime=settings.models["observatory_model"]["dome"]["settle_time"],
        )

        await self.evt_slewConfig.set_write(
            prereqDomalt=",".join(
                settings.models["observatory_model"]["slew"]["prereq_domalt"]
            ),
            prereqDomaz=",".join(
                settings.models["observatory_model"]["slew"]["prereq_domaz"]
            ),
            prereqDomazSettle=",".join(
                settings.models["observatory_model"]["slew"]["prereq_domazsettle"]
            ),
            prereqTelalt=",".join(
                settings.models["observatory_model"]["slew"]["prereq_telalt"]
            ),
            prereqTelaz=",".join(
                settings.models["observatory_model"]["slew"]["prereq_telaz"]
            ),
            prereqTelOpticsOpenLoop=",".join(
                settings.models["observatory_model"]["slew"]["prereq_telopticsopenloop"]
            ),
            prereqTelOpticsClosedLoop=",".join(
                settings.models["observatory_model"]["slew"][
                    "prereq_telopticsclosedloop"
                ]
            ),
            prereqTelSettle=",".join(
                settings.models["observatory_model"]["slew"]["prereq_telsettle"]
            ),
            prereqTelRot=",".join(
                settings.models["observatory_model"]["slew"]["prereq_telrot"]
            ),
            prereqFilter=",".join(
                settings.models["observatory_model"]["slew"]["prereq_filter"]
            ),
            prereqExposures=",".join(
                settings.models["observatory_model"]["slew"]["prereq_exposures"]
            ),
            prereqReadout=",".join(
                settings.models["observatory_model"]["slew"]["prereq_readout"]
            ),
        )

        await self.evt_opticsLoopCorrConfig.set_write(
            telOpticsOlSlope=settings.models["observatory_model"]["optics_loop_corr"][
                "tel_optics_ol_slope"
            ],
            telOpticsClAltLimit=settings.models["observatory_model"][
                "optics_loop_corr"
            ]["tel_optics_cl_alt_limit"],
            telOpticsClDelay=settings.models["observatory_model"]["optics_loop_corr"][
                "tel_optics_cl_delay"
            ],
        )

        await self.evt_parkConfig.set_write(
            telescopeAltitude=settings.models["observatory_model"]["park"][
                "telescope_altitude"
            ],
            telescopeAzimuth=settings.models["observatory_model"]["park"][
                "telescope_azimuth"
            ],
            telescopeRotator=settings.models["observatory_model"]["park"][
                "telescope_rotator"
            ],
            domeAltitude=settings.models["observatory_model"]["park"]["dome_altitude"],
            domeAzimuth=settings.models["observatory_model"]["park"]["dome_azimuth"],
            filterPosition=settings.models["observatory_model"]["park"][
                "filter_position"
            ],
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

        if not self.enable_observatory_status_monitor:
            return

        if general_info["isNight"]:
            await self.handle_observatory_status_nighttime()
        else:
            await self.handle_observatory_status_daytime()

    async def _publish_block_info(self) -> None:
        """Publish block information."""

        await self.evt_blockInventory.set_write(
            ids=",".join(self.model.observing_blocks),
            status=",".join(
                [
                    observing_blocks.status.name
                    for observing_blocks in self.model.observing_blocks_status.values()
                ]
            ),
        )

    async def _get_script_config_validator(
        self, script_name: str, standard: bool
    ) -> salobj.DefaultingValidator | None:
        """Get a script configuration validator.

        Parameters
        ----------
        script_name : `str`
            Name of the SAL Script.
        standard : `bool`
            Is the script standard?

        Returns
        -------
        `salobj.DefaultingValidator`
            Script configuration validator.
        """
        if self.script_paths is not None:
            return await self._get_script_config_validator_from_path(
                script_name=script_name, standard=standard
            )
        else:
            return await self._get_script_config_validator_from_script_queue(
                script_name=script_name, standard=standard
            )

    async def _get_script_config_validator_from_path(
        self, script_name: str, standard: bool
    ) -> salobj.DefaultingValidator | None:
        """Get a script configuration validator by getting the schema
        directly from the script executable.

        Parameters
        ----------
        script_name : `str`
            Name of the SAL Script.
        standard : `bool`
            Is the script standard?

        Returns
        -------
        `salobj.DefaultingValidator`
            Script configuration validator.
        """

        script_path = os.path.join(
            (
                self.script_paths["standard"]
                if standard
                else self.script_paths["external"]
            ),
            script_name,
        )
        process = await asyncio.create_subprocess_exec(
            script_path, "0", "--schema", stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20)

            script_schema_str = stdout.decode()

            return (
                salobj.DefaultingValidator(schema=yaml.safe_load(script_schema_str))
                if script_schema_str
                else None
            )
        except Exception:
            if process.returncode is None:
                process.terminate()
                self.log.warning(
                    "showSchema killed a process that was not properly terminated"
                )
            raise

    async def _get_script_config_validator_from_script_queue(
        self, script_name: str, standard: bool
    ) -> salobj.DefaultingValidator:
        """Get a script configuration validator by requesting the script
        schema from the ScriptQueue.

        Parameters
        ----------
        script_name : `str`
            Name of the SAL Script.
        standard : `bool`
            Is the script standard?

        Returns
        -------
        `salobj.DefaultingValidator`
            Script configuration validator.
        """

        self.queue_remote.evt_configSchema.flush()

        await self.queue_remote.cmd_showSchema.set_start(
            isStandard=standard,
            path=script_name,
            timeout=self.default_command_timeout,
        )

        script_schema = await self.queue_remote.evt_configSchema.next(
            flush=False, timeout=self.default_command_timeout
        )
        while not (
            script_schema.path == script_name and script_schema.isStandard == standard
        ):
            script_schema = await self.queue_remote.evt_configSchema.next(
                flush=False, timeout=self.default_command_timeout
            )

        return (
            salobj.DefaultingValidator(
                schema=yaml.safe_load(script_schema.configSchema)
            )
            if script_schema.configSchema
            else None
        )

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

    async def _cmd_start_ack_in_progress(
        self, data: salobj.type_hints.BaseDdsDataType
    ) -> None:
        """Continuously send in progress acknowledgements.

        This coroutine is supposed to run in the background while the start
        command is running to make sure it is continuously informing the
        requestor that the command is still active. This is required because
        the start command may take a long time to execute as it performs
        several tasks. Instead of providing a really long timeout, it is
        more robust to simply continuously send in progress. If the CSC gets
        stuck or crashes the ack's will stop and the command will timeout.

        Parameters
        ----------
        data : `salobj.type_hints.BaseDdsDataType`
            Command payload.
        """
        while True:
            await self.cmd_start.ack_in_progress(
                data,
                timeout=self.default_command_timeout,
                result="Start command still in progress.",
            )
            await asyncio.sleep(0.5)

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
            if "script_task" in task_name:
                del self._tasks[task_name]
            else:
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
    async def current_scheduler_state(self, publish_lfoa, reset_state=True):
        """A context manager to handle storing the current scheduler state,
        performing some operations on it and then resetting it to the
        previous state.

        Parameters
        ----------
        publish_lfoa : bool
            Publish current state to large file annex?
        reset_state : bool, optional
            Reset state at the end? Default: True.
        """

        async with self.scheduler_state_lock:
            self.model.synchronize_observatory_model()
            await self.model.update_telemetry()
            await self.model.update_conditions()
            last_scheduler_state_filename = await self.save_scheduler_state(
                publish_lfoa=publish_lfoa
            )

            try:
                yield last_scheduler_state_filename
            finally:
                if reset_state:
                    self.model.reset_state(last_scheduler_state_filename)
                shutil.os.remove(last_scheduler_state_filename)

    @contextlib.asynccontextmanager
    async def idle_to_running(self):
        """Context manager to handle transitioning from idle to running then
        back to idle.
        """
        try:
            await self._transition_idle_to_running()
            yield
        finally:
            # Going back to idle.
            await self._transition_running_to_idle()

    async def fault(self, code: int | None, report: str, traceback: str = "") -> None:
        """Override default fault state method.

        Before transitioning to FAULT, try to cleanup the queue.

        Parameters
        ----------
        code : `int`
            Error code for the ``errorCode`` event.
            If `None` then ``errorCode`` is not output and you should
            output it yourself. Specifying `None` is deprecated;
            please always specify an integer error code.
        report : `str`
            Description of the error.
        traceback : `str`, optional
            Description of the traceback, if any.
        """

        try:
            await self._cleanup_queue_targets()
        except Exception:
            self.log.exception(
                "Error trying to cleanup queue targets while going to FAULT. Ignoring."
            )

        await super().fault(code=code, report=report, traceback=traceback)

    async def set_observatory_status(self, status, note):
        """Set observatory status.

        Parameters
        ----------
        status : `int`
            Status value to set.
        note : `str`, optional
            Note to add to the status event.
        """
        if not hasattr(self, "evt_observatoryStatus"):
            return

        await self.evt_observatoryStatus.set_write(
            status=status,
            statusLabels=(
                " | ".join(
                    [
                        observatory_status.name
                        for observatory_status in SchedulerObservatoryStatus
                        if observatory_status & status > 0
                    ]
                )
                if status > 0
                else SchedulerObservatoryStatus.UNKNOWN.name
            ),
            note=note,
        )

    async def monitor_observatory_status(self):
        """Monitor and set the observatory status."""

        for component in self.parameters.observatory_status.components_to_monitor:
            component_reference_name = component.lower()
            if component_reference_name not in self._remotes:
                self.log.info(f"Creating remote to monitor {component} state.")
                name, index = salobj.name_to_name_index(component)
                self._remotes[component_reference_name] = salobj.Remote(
                    domain=self.domain,
                    name=name,
                    index=index,
                    include=["summaryState"],
                    readonly=True,
                )

                await self._remotes[component_reference_name].start_task

            if (
                self._remotes[component_reference_name].evt_summaryState.callback
                is None
            ):

                monitor_component_state_func = functools.partial(
                    self._monitor_component_state,
                    component_name=component,
                )
                try:
                    summary_state = await self._remotes[
                        component_reference_name
                    ].evt_summaryState.aget(timeout=self.parameters.loop_sleep_time)
                    await monitor_component_state_func(data=summary_state)
                except asyncio.TimeoutError:
                    pass
                self._remotes[component_reference_name].evt_summaryState.callback = (
                    monitor_component_state_func
                )

    async def _monitor_component_state(self, data, component_name):
        """Monitor and update the summary state of a specific component.

        This method processes the incoming state data for a component, updates
        the internal state tracking dictionary, and triggers an
        observatory-level fault status update if the component enters a
        FAULT state.

        Parameters
        ----------
        data : `lsst.ts.salobj.topics.ReadTopic`
            The data object containing the component's telemetry or event
            information. It must possess a `summaryState` attribute.
        component_name : `str`
            The unique identifier or name of the component being monitored.

        See Also
        --------
        set_observatory_status_fault : Method called when a FAULT state is
            detected.
        unset_observatory_status_fault : Method called for non-FAULT states.

        Notes
        -----
        The method utilizes `salobj.State` to cast the raw `summaryState`
        integer into a readable enumeration.
        """
        self.log.debug(
            f"Processing state for {component_name}: salobj.State(data.summaryState)."
        )
        component_state = salobj.State(data.summaryState)
        self._components_summary_state[component_name] = component_state

        if component_state == salobj.State.FAULT:
            await self.set_observatory_status_fault()
        else:
            await self.unset_observatory_status_fault()

    async def set_observatory_status_fault(self):
        """Transition the observatory status to a FAULT state.

        This method modifies the current observatory status by removing the
        OPERATIONAL flag (if present) and ensuring the FAULT flag is set. It
        then publishes the updated status and a generated status note.

        See Also
        --------
        generate_status_note : Generates the descriptive text for the status
            update.
        set_observatory_status : The underlying method that publishes the
            status change.
        unset_observatory_status_fault : The inverse operation to clear fault
            states.

        Notes
        -----
        The status management uses bitwise flags from
        `SchedulerObservatoryStatus`:

        * **Bitwise XOR (`^`)**: Used to flip the `OPERATIONAL` bit to 0 if it
          was previously 1.
        * **Bitwise OR (`|`)**: Used to set the `FAULT` bit to 1.
        * **Bitwise AND (`&`)**: Used to check the current state of specific
          flags before applying changes.
        """

        status = self.evt_observatoryStatus.data.status
        status_note = self.generate_status_note()
        if status & SchedulerObservatoryStatus.OPERATIONAL:
            self.log.debug("Disable operational.")
            status = status ^ SchedulerObservatoryStatus.OPERATIONAL

        if (
            self.evt_observatoryStatus.data.status & SchedulerObservatoryStatus.FAULT
            > 0
        ):
            self.log.debug("Status is already FAULT, nothing to do.")
            await self.set_observatory_status(
                status=status,
                note=status_note,
            )
        else:
            status = status | SchedulerObservatoryStatus.FAULT
            await self.set_observatory_status(
                status=status,
                note=status_note,
            )

    async def unset_observatory_status_fault(self):
        """Attempt to clear the observatory FAULT status.

        This method evaluates if the observatory-level FAULT flag can be safely
        removed. It checks the internal state of all components; if any single
        component remains in a FAULT state, the global FAULT status is
        preserved. Otherwise, the FAULT flag is cleared.

        See Also
        --------
        set_observatory_status_fault : The inverse operation to set the fault
            state.
        _monitor_component_state : Updates the component states evaluated here.

        Notes
        -----
        The clearing logic follows a specific hierarchy:
        1. If the FAULT bit is already 0, no change is made.
        2. A list comprehension scans `self._components_summary_state`. If any
           component has a state equal to `salobj.State.FAULT`, the clearing
           process is aborted to ensure safety.
        3. If no components are in FAULT, the bitwise XOR (`^`) operator is
           used to flip the `FAULT` bit to 0.
        """
        status = self.evt_observatoryStatus.data.status
        status_note = self.generate_status_note()
        if (
            self.evt_observatoryStatus.data.status & SchedulerObservatoryStatus.FAULT
            == 0
        ):
            self.log.debug("Fault status already cleared, nothing to do.")
            return
        elif any(
            state == salobj.State.FAULT
            for state in self._components_summary_state.values()
        ):
            await self.set_observatory_status(
                status=status,
                note=status_note,
            )
        else:
            self.log.debug(
                "No more components in fault, updating note but leaving status as FAULT."
            )
            await self.set_observatory_status(
                status=status,
                note=status_note,
            )

    def generate_status_note(self, user_note=None):
        """Construct a descriptive string summarizing the current system
        health.

        This method aggregates an optional user-provided message with an
        automatically generated list of all components currently reporting
        a FAULT state.

        Parameters
        ----------
        user_note : `str`, optional
            A custom message to prepend to the status note. If None, only
            the component fault information is returned.

        Returns
        -------
        note : `str`
            A combined string containing the user note (if provided) and
            the list of components in a FAULT state.

        Notes
        -----
        The method iterates through `self._components_summary_state` to
        identify components where the state matches `salobj.State.FAULT`.
        The resulting string uses the formal representation (`!r`) of
        the `salobj.State` enumeration for clarity.
        """
        note = ""
        if user_note is not None:
            note += user_note
        components_in_fault = [
            component
            for component, state in self._components_summary_state.items()
            if state == salobj.State.FAULT
        ]
        if components_in_fault:
            if note and not note[-1].isspace():
                note += " "
            note += f"The following components are in {salobj.State.FAULT!r} state: {components_in_fault}."
        return note

    def validate_observatory_status(self, status):
        """Given an input status, check if it is a valid new status.

        Parameters
        ----------
        status : `int`
            Status to validate.

        Raises
        ------
        `InvalidStatusError`
            If input status is invalid.
        `UpdateStatusError`
            If applying the input status cannot be applied. For
            example if input status clears the fault flags but
            there are systems still in fault and, as such, flag cannot
            be cleared.
        """
        if status < 0 or status > self.max_status:
            raise InvalidStatusError(
                f"Cannot set status to {status}. "
                f"Must be equal to or larger than zero and smaller or equal to {self.max_status}."
            )

        if (
            components_in_fault := [
                component
                for component, state in self._components_summary_state.items()
                if state == salobj.State.FAULT
            ]
        ) and (status & Scheduler.ObservatoryStatus.FAULT == 0):

            components_in_fault_str = ", ".join(components_in_fault)
            raise UpdateStatusError(
                "Cannot clear FAULT status, "
                "the following components are still in fault: "
                f"{components_in_fault_str}. "
                "Make sure they are recovered before resetting the Fault flag."
            )

        if status & Scheduler.ObservatoryStatus.OPERATIONAL and (
            status & Scheduler.ObservatoryStatus.DAYTIME
            or status & Scheduler.ObservatoryStatus.FAULT
            or status & Scheduler.ObservatoryStatus.DOWNTIME
        ):
            invalid_status_str = " | ".join(
                [s.name for s in Scheduler.ObservatoryStatus if s & status]
            )
            raise InvalidStatusError(f"Invalid status: {invalid_status_str}.")

        general_info = self.model.get_general_info()
        if (
            not general_info["isNight"]
            and not status & Scheduler.ObservatoryStatus.DAYTIME
        ):
            status_str = (
                " | ".join([s.name for s in Scheduler.ObservatoryStatus if s & status])
                if status > 0
                else Scheduler.ObservatoryStatus.UNKNOWN.name
            )

            raise UpdateStatusError(
                f"Cannot set status to {status_str}; daytime flag is active. "
                "Status must include DAYTIME."
            )

    async def handle_observatory_status_nighttime(self):
        if not hasattr(self, "evt_observatoryStatus"):
            return

        status = self.evt_observatoryStatus.data.status
        if status & SchedulerObservatoryStatus.DAYTIME:
            status = status ^ SchedulerObservatoryStatus.DAYTIME
            note = self.generate_status_note(user_note="Nighttime started.")
            await self.set_observatory_status(status=status, note=note)

    async def handle_observatory_status_daytime(self):
        if not hasattr(self, "evt_observatoryStatus"):
            return

        status = self.evt_observatoryStatus.data.status
        if not status & SchedulerObservatoryStatus.DAYTIME:
            status = status | SchedulerObservatoryStatus.DAYTIME
            if status & SchedulerObservatoryStatus.OPERATIONAL:
                status = status ^ SchedulerObservatoryStatus.OPERATIONAL
            note = self.generate_status_note(user_note="Daytime started.")
            await self.set_observatory_status(
                status=status,
                note=note,
            )


def run_scheduler() -> None:
    """Run the Scheduler CSC."""
    asyncio.run(SchedulerCSC.amain(index=Scheduler.SalIndex))
