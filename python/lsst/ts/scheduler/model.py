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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["Model"]

import asyncio
import functools
import io
import logging
import pathlib
import types
import typing
import urllib.request

import numpy as np
from jsonschema import ValidationError
from lsst.ts import observing, utils
from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.idl.enums import Script
from lsst.ts.observatory.model import ObservatoryModel, ObservatoryState
from lsst.ts.salobj.type_hints import BaseDdsDataType
from rubin_sim.site_models.cloud_model import CloudModel
from rubin_sim.site_models.seeing_model import SeeingModel

from .driver import Driver, DriverFactory, DriverType
from .driver.driver_target import DriverTarget
from .driver.survey_topology import SurveyTopology
from .observing_blocks.observing_block_status import ObservingBlockStatus
from .telemetry_stream_handler import TelemetryStreamHandler
from .utils.csc_utils import (
    BlockStatus,
    FailedStates,
    NonFinalStates,
    is_uri,
    is_valid_efd_query,
)
from .utils.exceptions import UpdateTelemetryError
from .utils.scheduled_targets_info import ScheduledTargetsInfo
from .utils.types import ValidationRules


class Model:
    """Scheduler model class.

    This class implements the business logic of the Scheduler. The CSC
    instantiates the model and offload the operations to it, which allows for
    better separation of concerns and cleaner code on the CSC part.

    Parameters
    ----------
    log : `logging.Logger`
        Logger class to create child from.
    config_dir : pathlib.Path
        Directory containing configuration files.

    Attributes
    ----------
    log : `logging.Logger`
        Class logger instance.
    config_dir : `pathlib.Path`
        Directory containing configuration files.
    telemetry_stream_handler : `TelemetryStreamHandler`
        Object to handle telemetry streams.
    time_delta_no_target : `float`
        How far to step into the future when there are no targets, in seconds.
    models : `dict`[`str`, `Any`]
        Dictionary to store the scheduler models.
    raw_telemetry : `dict`[`str`, `Any`]
        Dictionary to store raw telemetry.
    script_info : `dict`[`int`, `BaseDdsDataType`]
        Dictionary to store information about the scripts sent to the
        script queue.
    observing_blocks : `dict`[`str`, `observing.ObservingBlock`]
        Observing blocks.
    driver : `Driver`
        Scheduler driver.
    max_scripts : `int`
        Maximum number of scripts to keep track of.
    startup_type : dict[str, coroutine]
        Dictionary with the startup types and functions.
    """

    def __init__(self, log: logging.Logger, config_dir: pathlib.Path) -> None:
        self.log = log.getChild(type(self).__name__)

        self.config_dir = config_dir

        self.telemetry_stream_handler: TelemetryStreamHandler = None

        # How far to step into the future when there's not targets in seconds
        self.time_delta_no_target = 30.0

        # Dictionary to store the scheduler models
        self.models: dict[str, typing.Any] = dict()

        # Dictionary to store raw telemetry
        self.raw_telemetry: dict[str, typing.Any] = dict()

        # Dictionary to store information about the scripts put on the queue
        self.script_info: dict[int, BaseDdsDataType] = dict()

        # Dictionary to store observing blocks
        self.observing_blocks: dict[str, observing.ObservingBlock] = dict()
        self.observing_blocks_status: dict[str, ObservingBlockStatus] = dict()

        # Scheduler driver instance.
        self.driver: Driver | None = None

        self.max_scripts = 0

        self.startup_types: dict[
            str, typing.Coroutine[typing.Any, typing.Any, SurveyTopology]
        ] = dict(
            HOT=self.configure_driver_hot,
            WARM=self.configure_driver_warm,
            COLD=self.configure_driver_cold,
        )

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure model.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Model configuration.
        """
        self.log.debug("Configuring telemetry streams.")

        self.max_scripts = config.max_scripts

        if len(self.raw_telemetry) == 0:
            self.log.warning("Telemetry stream not initialized. Initializing...")
            self.init_telemetry()

        await self.configure_telemetry_streams(config.telemetry)

        self.log.debug("Configuring models.")

        if len(self.models) == 0:
            self.log.warning("Models are not initialized. Initializing...")
            self.init_models()

        for model in self.models:
            # TODO (DM-36761): This check will give us time to implement the
            # required changes on the models.
            if model in config.models:
                self.log.debug(f"Configuring {model}")
                try:
                    self.models[model].configure(config.models[model])
                except Exception:
                    self.log.exception(f"Failed to configure model {model}.")
            else:
                self.log.warning(f"No configuration for {model}. Skipping.")

        await self.load_observing_blocks(config.path_observing_blocks)

        self.log.debug("Configuring Driver and Scheduler.")

        return await self.configure_driver(config)

    def init_telemetry(self) -> None:
        """Initialize telemetry streams."""

        # List of scheduled targets and script ids
        self.reset_scheduled_targets()

        # List of things on the observatory queue
        self.raw_telemetry["observing_queue"] = []

    def init_models(self) -> None:
        """Initialize but not configure needed models."""
        try:
            self.models["location"] = ObservatoryLocation()
            self.models["observatory_model"] = ObservatoryModel(
                self.models["location"], logging.DEBUG
            )
            self.models["observatory_state"] = ObservatoryState()
            self.models["sky"] = AstronomicalSkyModel(self.models["location"])
            self.models["sky"].sky_brightness_pre.load_length = 7
            self.models["seeing"] = SeeingModel()
            self.models["cloud"] = CloudModel()
        except Exception as e:
            self.log.error("Failed to initialize models, resetting.")
            self.models = dict()
            raise e

    async def configure_telemetry_streams(self, config: dict[str, typing.Any]) -> None:
        """Configure telemetry streams.

        Parameters
        ----------
        config : `dict`
            Telemetry stream configuration.
        """

        efd_name = config["efd_name"]

        self.log.debug(
            f"Configuring telemetry stream handler for {efd_name} efd instance."
        )

        self.telemetry_stream_handler = TelemetryStreamHandler(
            log=self.log, efd_name=efd_name
        )

        if "streams" not in config:
            self.log.warning(
                "No telemetry stream defined in configuration. Skipping configuring telemetry streams."
            )
            await self.telemetry_stream_handler.configure_telemetry_stream(
                telemetry_stream=[]
            )
            return

        self.log.debug("Configuring telemetry stream.")

        await self.telemetry_stream_handler.configure_telemetry_stream(
            telemetry_stream=config["streams"]
        )

        for telemetry in self.telemetry_stream_handler.telemetry_streams:
            self.raw_telemetry[telemetry] = np.nan

    async def load_observing_blocks(self, path: str) -> None:
        """Load observing blocks from the provided path.

        The method will glob the provided path for all json files and load them
        as observing blocks.

        Parameters
        ----------
        path : `str`
            Path to the observing blocks directory relative to the
            configuration path.
        """
        path_observing_blocks = self.config_dir.joinpath(path)

        if not path_observing_blocks.exists():
            raise RuntimeError(
                "Provided observing block directory does not exists. "
                f"Got {path_observing_blocks.absolute()}"
            )
        for observing_block_file in path_observing_blocks.glob("*.json"):
            observing_block = observing.ObservingBlock.parse_file(observing_block_file)
            self.observing_blocks[observing_block.program] = observing_block
            self.observing_blocks_status[
                observing_block.program
            ] = await self._get_block_status(program=observing_block.program)

    async def validate_observing_blocks(
        self, observing_scripts_config_validator: ValidationRules
    ) -> None:
        """Validate observing blocks script configurations.

        Parameters
        ----------
        observing_scripts_config_validator : `ValidationRules`
            Dictionary with script configuration validator.
        """

        for block_id in self.observing_blocks:
            target_validate = DriverTarget(
                observing_block=self.observing_blocks[block_id].copy(deep=True)
            )
            observing_block = target_validate.get_observing_block()
            for script in observing_block.scripts:
                key = (script.name, script.standard)
                try:
                    observing_scripts_config_validator[key].validate(script.parameters)
                except ValidationError as validation_error:
                    self.log.error(
                        f"Script {script.name} from observing block {block_id} failed validation: "
                        f"{validation_error.message}.\n{script.parameters}"
                    )
                    self.observing_blocks_status[block_id].status = BlockStatus.INVALID
                    break
                except Exception:
                    self.log.exception(
                        f"Failed to validate script {script.name} from observing block {block_id} "
                        f"with:\n{script.parameters}"
                    )
                    self.observing_blocks_status[block_id].status = BlockStatus.INVALID
                    break
                else:
                    self.log.debug(
                        f"Successfully validated script {script.name} from {block_id} "
                        f"with:\n{script.parameters}"
                    )
                    self.observing_blocks_status[
                        block_id
                    ].status = BlockStatus.AVAILABLE

    def get_valid_observing_blocks(self) -> list[str]:
        """Get list of valid observing blocks.

        Returns
        -------
        `list`[ `str` ]
            List of valid observing blocks.
        """
        return [
            block_id
            for block_id in self.observing_blocks_status
            if self.observing_blocks_status[block_id].status != BlockStatus.INVALID
        ]

    async def configure_driver(self, config: typing.Any) -> SurveyTopology:
        """Load driver for selected scheduler and configure its basic
        parameters.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `SurveyTopology`
            Survey topology
        """
        return await self.startup_types[config.startup_type](config)

    async def configure_driver_hot(self, config: typing.Any) -> SurveyTopology:
        """Perform hot start.

        This is the most versatile startup mode and is designed to rapidly
        recover the state of the observatory. Nevertheless, it has the caveat
        that it will skip configuring the driver altogether if the driver is
        already configured. If you want to make sure the driver is reconfigured
        use WARM or COLD start instead.

        See https://ts-scheduler.lsst.io/configuration/configuration.html for
        more information.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `SurveyTopology`
            Survey topology
        """
        if self.driver is not None:
            self.log.warning(
                "HOT start: driver already defined. Skipping driver configuration."
            )
            return self.driver.get_survey_topology(config)

        self.load_driver(config.driver_type)

        survey_topology = await self._handle_driver_configure_scheduler(config)

        await self._handle_startup_database_snapshot(config.startup_database)

        return survey_topology

    async def configure_driver_warm(self, config: typing.Any) -> SurveyTopology:
        """Perform warm start.

        This is mode is similar to hot start but with the exception that it
        will always reload the driver, whereas hot start skips reloading the
        driver if it is already defined.

        See https://ts-scheduler.lsst.io/configuration/configuration.html for
        more information.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `SurveyTopology`
            Survey topology
        """
        if self.driver is not None:
            self.log.warning("WARM start: driver already defined. Resetting driver.")

        self.load_driver(config.driver_type)

        survey_topology = await self._handle_driver_configure_scheduler(config)

        await self._handle_startup_database_snapshot(config.startup_database)

        return survey_topology

    async def configure_driver_cold(self, config: typing.Any) -> SurveyTopology:
        """Perform cold start.

        Cold start is the slowest start up and, in general, will only be used
        in cases where the scheduler configuration changed quite drastically
        but one still wants to take previous observations into account. As
        such, cold start will most likely only be used before the night starts
        in some very limited situations.

        In this case the scheduler starts by creating the driver, overriding
        any previous driver.

        Cold start has two ways of recreating playing back observations;
        the user provides the path to a database that the driver can parse or
        an EFD query that will return a series of observations.

        See https://ts-scheduler.lsst.io/configuration/configuration.html for
        more information.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `SurveyTopology`
            Survey topology
        """
        if self.driver is not None:
            self.log.warning("COLD start: driver already defined. Resetting driver.")

        self.load_driver(config.driver_type)

        survey_topology = await self._handle_driver_configure_scheduler(config)

        await self._handle_startup_database_observation_db(config.startup_database)

        return survey_topology

    def load_driver(self, driver_type: str) -> None:
        """Utility method to load a driver from a driver type name.

        Parameters
        ----------
        driver_type : `str`
            Name of the driver type. Available options are in `DriveType`.
        """
        self.log.info(f"Loading driver {driver_type}")

        self.driver = DriverFactory.get_driver(
            driver_type=DriverType(driver_type),
            models=self.models,
            raw_telemetry=self.raw_telemetry,
            observing_blocks=self.observing_blocks,
            log=self.log,
        )

    def reset_scheduled_targets(self) -> None:
        """Reset the list of scheduled targets."""
        self.raw_telemetry["scheduled_targets"] = []

    def add_scheduled_target(self, target: DriverTarget) -> None:
        """Append target to scheduled target list.

        Parameters
        ----------
        target : `DriverTarget`
            Scheduled target.
        """
        self.raw_telemetry["scheduled_targets"].append(target)

    def get_scheduled_targets(self) -> list[DriverTarget]:
        """Return the list of scheduled targets.

        Returns
        -------
        `list`[`DriverTarget`]
            List of currently scheduled targets.
        """
        return self.raw_telemetry["scheduled_targets"]

    async def callback_script_info(self, data: BaseDdsDataType) -> None:
        """This callback function will store in a dictionary information about
        the scripts.

        Parameters
        ----------
        data : `BaseDdsDataType`
            Script info topic data.

        Notes
        -----
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

        self.script_info[data.scriptSalIndex] = data

        script_info_size = len(self.script_info)
        if script_info_size > self.max_scripts:
            # Removes old entries
            items_to_remove = list(self.script_info.keys())[
                : script_info_size - self.max_scripts
            ]
            for key in items_to_remove:
                del self.script_info[key]

    async def check_scheduled_targets(self) -> ScheduledTargetsInfo:
        """Loop through the scheduled targets list, check status and tell
        driver of completed observations.

        Returns
        -------
        scheduled_targets_info : `ScheduledTargetsInfo`
            Information about scheduled targets.
        """
        scheduled_targets = self.get_scheduled_targets()

        number_of_targets = len(scheduled_targets)

        scheduled_targets_info = ScheduledTargetsInfo()

        self.log.debug(f"Checking {number_of_targets} scheduled targets")

        report = ""

        for _ in range(number_of_targets):
            target = scheduled_targets.pop(0)
            sal_indices = target.get_sal_indices()

            script_info = [
                self.script_info[sal_index]
                for sal_index in sal_indices
                if sal_index in self.script_info
            ]

            if not script_info or len(script_info) != len(sal_indices):
                report += f"No information on all scripts on queue, put it back and continue: {target}.\n"
                # No information on all scripts on queue,
                # put it back and continue
                self.raw_telemetry["scheduled_targets"].append(target)
                continue

            scripts_state = [info.scriptState for info in script_info]

            if all([state == Script.ScriptState.DONE for state in scripts_state]):
                # All scripts completed successfully
                report += (
                    f"\n\t{target.note} observation completed successfully. "
                    "Registering observation."
                )

                self.driver.register_observation(target)
                scheduled_targets_info.observed.append(target)
                # Remove related script from the list
                for index in sal_indices:
                    self.script_info.pop(index)
                # target now simply disappears... Should I keep it in for
                # future refs?
            elif any([state in FailedStates for state in scripts_state]):
                # one or more script failed
                report += f"\n\t{target.note} failed. Not registering observation."
                # Remove related script from the list
                scheduled_targets_info.failed.append(target)
                for index in sal_indices:
                    self.script_info.pop(index)
            elif any([state in NonFinalStates for state in scripts_state]):
                # one or more script in a non-final state, just put it back on
                # the list.
                self.raw_telemetry["scheduled_targets"].append(target)
            else:
                report += (
                    (
                        f"\n\tOne or more state unrecognized [{scripts_state}] for observations "
                        f"{sal_indices} for target {target}."
                    ),
                )
                scheduled_targets_info.unrecognized.extend(sal_indices)
                # Remove related script from the list
                for index in sal_indices:
                    self.script_info.pop(index)

        if report:
            self.log.info(f"Check scheduled report:\n\n{report}")
        else:
            self.log.debug("Nothing to report.")

        return scheduled_targets_info

    def get_general_info(self) -> dict[str, bool | float | int | str]:
        """Get general information from the driver.

        Returns
        -------
        `dict`[`str`, `bool` | `float` | `int` | `str`]
            Dictionary with general information.
        """
        return dict(
            isNight=self.driver.is_night,
            night=self.driver.night,
            sunset=self.driver.current_sunset,
            sunrise=self.driver.current_sunrise,
        )

    async def select_next_target(self) -> DriverTarget:
        """Select next target.

        Returns
        -------
        `DriverTarget`
            Next target.
        """
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(None, self.driver.select_next_target)

    async def select_next_targets(self) -> list[DriverTarget]:
        """Select next target.

        Returns
        -------
        `list` [`DriverTarget`]
            List of next targets.
        """
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(None, self.driver.select_next_targets)

    async def update_conditions(self) -> None:
        """Update conditions in the driver."""
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(None, self.driver.update_conditions)

    async def generate_target_queue(self, targets_queue, max_targets):
        """Generate target queue.

        Parameters
        ----------
        targets_queue : `list`[`DriverTarget`]
            List of already queued targets. These are in the scheduler queue
            but not scheduled to run yet.
        max_targets : `int`
            Number of target to generate.

        Yields
        ------
        `tuple`[ `float`, `float`,  `DriverTarget`]
            Tuple with target information. This consist of the observatory time
            when the target was computed, how long to wait to observe the
            target and the target.
        """
        # Note that here it runs the update_telemetry method from the
        # scheduler. This method will update the telemetry based on most
        # current recent data in the system.
        await self.update_telemetry()

        self.synchronize_observatory_model()
        self.register_scheduled_targets(targets_queue)

        # For now it will only generate enough targets to send to the queue
        # and leave one extra in the internal queue. In the future we will
        # generate targets to fill the
        # self.parameters.predicted_scheduler_window.
        # But then we will have to improve how we handle the target
        # generation and the check_targets_queue_condition.
        self.log.debug(f"Requesting {max_targets} additional targets.")

        for _ in range(max_targets):
            # Inside the loop we are running update_conditions directly
            # from the driver instead of update_telemetry. This bypasses
            # the updates done by the CSC method.
            await self.update_conditions()

            await asyncio.sleep(0)

            targets = await self.select_next_targets()

            await asyncio.sleep(0)

            if targets is None:
                n_scheduled_targets = self.get_number_of_scheduled_targets()
                self.log.warning(
                    "No target from the scheduler. "
                    f"Stopping with {len(targets_queue)+n_scheduled_targets}. "
                    f"Number of scheduled targets is {n_scheduled_targets}."
                )
                break
            else:
                for target in targets:
                    if target is None:
                        self.log.debug("No target, skipping...")
                        continue
                    self.log.debug(
                        f"Temporarily registering selected targets: {target.note}."
                    )
                    self.driver.register_observed_target(target)

                    # The following will playback the observations on the
                    # observatory model but will keep the observatory state
                    # unchanged
                    self.models["observatory_model"].observe(target)

                    wait_time = (
                        self.models["observatory_model"].current_state.time
                        - self.models["observatory_state"].time
                    )

                    yield self.models[
                        "observatory_model"
                    ].current_state.time, wait_time, target

            if self.get_number_of_scheduled_targets() >= max_targets:
                self.log.debug(
                    f"Generated {self.get_number_of_scheduled_targets()} targets."
                    f"Max targets: {max_targets}."
                )
                break

    def register_scheduled_targets(self, targets_queue: list[DriverTarget]) -> None:
        """Register scheduled targets.

        Parameters
        ----------
        targets_queue : `list`[`DriverTarget`]
            List of additional targets in the queue to register after scheduled
            targets.
        """
        self.log.debug("Registering current scheduled targets.")

        for target in self.raw_telemetry["scheduled_targets"]:
            self.log.debug(f"Temporarily registering scheduled target: {target.note}.")
            self.driver.register_observed_target(target)
            self.models["observatory_model"].observe(target)

        for target in targets_queue:
            self.log.debug(f"Temporarily registering queued target: {target.note}.")
            self.driver.register_observed_target(target)
            self.models["observatory_model"].observe(target)

    def synchronize_observatory_model(self) -> None:
        """Synchronize observatory model state with current observatory
        state.
        """
        self.models["observatory_model"].set_state(self.models["observatory_state"])
        self.models["observatory_model"].start_tracking(
            self.models["observatory_state"].time
        )

    async def generate_targets_in_time_window(self, max_targets, time_window):
        """Generate targets from the driver in given time window.

        Parameters
        ----------
        max_targets : `int`
            Maximum number of targets.
        time_window : `float`
            Length of time in the future to compute targets (in seconds).

        Returns
        -------
        time_scheduler_evaluation : `float`
            The time when the last evaluation was performed.
        time_start : `float`
            The time when the evaluation started.
        targets : `list` of `Target`
            List of targets.
        """

        loop = asyncio.get_running_loop()

        time_start = self.models["observatory_model"].current_state.time
        time_scheduler_evaluation = time_start

        self.models["observatory_model"].stop_tracking(time_scheduler_evaluation)

        targets = []
        while (
            len(targets) < max_targets
            and (time_scheduler_evaluation - time_start) < time_window
        ):
            await loop.run_in_executor(None, self.driver.update_conditions)

            await asyncio.sleep(0)

            target = await loop.run_in_executor(None, self.driver.select_next_target)

            await asyncio.sleep(0)

            if target is None:
                time_scheduler_evaluation += self.time_delta_no_target
                self.models["observatory_model"].update_state(time_scheduler_evaluation)
            else:
                target.obs_time = self.models["observatory_model"].dateprofile.mjd
                self.models["observatory_model"].observe(target)
                time_scheduler_evaluation = self.models[
                    "observatory_model"
                ].current_state.time
                targets.append(target)

        return time_scheduler_evaluation, time_start, targets

    def get_number_of_scheduled_targets(self) -> int:
        """Get the number of scheduled targets.

        Returns
        -------
        `int`
            Number of target in the scheduled targets list.
        """
        return len(self.raw_telemetry.get("scheduled_targets", []))

    def get_observatory_state(self) -> dict[str, float | int | bool | str]:
        """Get current observatory state.

        Returns
        -------
        `dict`[`str`, `float` | `int` | `bool` | `str`]
            Observatory state.
        """
        return dict(
            timestamp=self.models["observatory_state"].time,
            ra=self.models["observatory_state"].ra,
            declination=self.models["observatory_state"].dec,
            positionAngle=self.models["observatory_state"].ang,
            parallacticAngle=self.models["observatory_state"].pa,
            tracking=self.models["observatory_state"].tracking,
            telescopeAltitude=self.models["observatory_state"].telalt,
            telescopeAzimuth=self.models["observatory_state"].telaz,
            telescopeRotator=self.models["observatory_state"].telrot,
            domeAltitude=self.models["observatory_state"].domalt,
            domeAzimuth=self.models["observatory_state"].domaz,
            filterPosition="",
            filterMounted="",
            filterUnmounted="",
        )

    def set_observatory_state(self, current_target_state) -> None:
        self.models["observatory_state"].time = current_target_state.timestamp
        self.models["observatory_state"].az_rad = np.radians(
            current_target_state.demandAz
        )
        self.models["observatory_state"].alt_rad = np.radians(
            current_target_state.demandEl
        )
        self.models["observatory_state"].rot_rad = np.radians(
            current_target_state.demandRot
        )
        self.models["observatory_state"].ra_rad = np.radians(
            current_target_state.demandRa
        )
        self.models["observatory_state"].dec_rad = np.radians(
            current_target_state.demandDec
        )
        self.models["observatory_state"].pa_rad = np.radians(
            current_target_state.parAngle
        )

    def get_stop_tracking_target(self) -> DriverTarget:
        """Get stop tracking target.

        Returns
        -------
        `DriverTarget`
            Target with information about how to stop tracking.
        """
        return self.driver.get_stop_tracking_target()

    def get_state(self) -> tuple[io.BytesIO, str]:
        """Get driver state.

        Returns
        -------
        `tuple`[`io.BytesIO`, `str`]
            Tuple with driver state and a name of the file with a stored
            version.
        """
        return self.driver.get_state_as_file_object(), self.driver.save_state()

    def reset_state(self, last_scheduler_state_filename: str) -> None:
        """Reset driver state from file.

        Parameters
        ----------
        last_scheduler_state_filename : `str`
            Name of the file with scheduler state.
        """
        self.log.debug(
            f"Resetting scheduler state from {last_scheduler_state_filename}."
        )
        self.driver.reset_from_state(last_scheduler_state_filename)

    async def _handle_driver_configure_scheduler(
        self, config: typing.Any
    ) -> SurveyTopology:
        """Handle configuring the scheduler asynchronously.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `SurveyTopology`
            Survey topology
        """

        configure_scheduler = functools.partial(
            self.driver.configure_scheduler, config=config
        )

        return await asyncio.get_running_loop().run_in_executor(
            None, configure_scheduler
        )

    async def _handle_startup_database_snapshot(self, startup_database: str) -> None:
        """Handle startup database snapshot.

        Parameters
        ----------
        startup_database : `str`
            Uri of the startup database.

        Raises
        ------
        RuntimeError
            If startup_database is invalid.
        """

        if is_uri(startup_database):
            self.log.info(f"Loading scheduler snapshot from {startup_database}.")
            await self.handle_load_snapshot(startup_database)
        elif startup_database.strip():
            raise RuntimeError(
                f"Invalid startup_database: {startup_database.strip()}. "
                "Make sure it is a valid and accessible URI."
            )
        else:
            self.log.debug("No scheduler snapshot provided.")

    async def _handle_startup_database_observation_db(
        self, startup_database: str
    ) -> None:
        """Handle startup database for observation database.

        Parameters
        ----------
        startup_database : `str`
            Path to a local database or EFD query.

        Raises
        ------
        RuntimeError
            If startup_database is invalid.
        """

        if not startup_database.strip():
            self.log.info("No observation history information provided.")
        elif pathlib.Path(startup_database).exists():
            self.log.info(
                f"Loading observation history from database: {startup_database}."
            )
            await self._handle_load_observations_from_db(database_path=startup_database)
        elif is_valid_efd_query(startup_database):
            await self._handle_load_observations_from_efd(efd_query=startup_database)
        else:
            error_msg = (
                "Specified startup database does not exists and does not classify as an EFD query. "
                f"Received: {startup_database}. "
                "If this was supposed to be a path, it must be local to the CSC environment. "
                "If this was supposed to be an EFD query, it should have the format: "
                'SELECT * FROM "efd"."autogen"."lsst.sal.Scheduler.logevent_observation" WHERE '
                "time >= '2021-06-09T00:00:00.000+00:00' AND time <= '2021-06-12T00:00:00.000+00:00'"
            )
            self.log.error(error_msg)
            raise RuntimeError(error_msg)

    async def _handle_load_observations_from_db(self, database_path: str) -> None:
        """Handle loading observations from a database and playing them back
        into the driver.

        Parameters
        ----------
        database_path : `str`
            Path to the local database file.
        """
        observations = await self._parse_observation_database(database_path)

        await self.register_observations(observations)

    async def _handle_load_observations_from_efd(self, efd_query: str) -> None:
        """Handle loading observations from the EFD and playing them back into
        the driver.

        Parameters
        ----------
        efd_query : `str`
            A valid EFD query that should return a list of observations.
        """
        observations = await self._query_observations_from_efd(efd_query)

        self.log.info(
            "Loading observation history from EFD. "
            f"Query: {efd_query} yield {len(observations)} targets."
        )

        await self.register_observations(observations=observations)

    async def handle_load_snapshot(self, uri: str) -> None:
        """Handler loading a scheduler snapshot asynchronously.

        Parameters
        ----------
        uri : `str`
            Uri with the address of the snapshot.
        """
        loop = asyncio.get_running_loop()

        try:
            retrieve = functools.partial(
                urllib.request.urlretrieve, url=uri, filename=""
            )
            dest, _ = await loop.run_in_executor(None, retrieve)
        except urllib.request.URLError:
            raise RuntimeError(
                f"Could not retrieve {uri}. Make sure it is a valid and accessible URI."
            )

        self.log.debug(f"Loading user-define configuration from {uri} -> {dest}.")

        load = functools.partial(self.driver.load, config=dest)
        await loop.run_in_executor(None, load)

    async def register_observations(
        self, observations: typing.List[DriverTarget]
    ) -> None:
        """Register a list of observations.

        Parameters
        ----------
        observations : `list`[`DriverTarget`]
            List of observations.
        """
        if observations is None:
            self.log.warning("No observations to register")
            return
        self.log.debug(f"Registering {len(observations)} observations.")
        for observation in observations:
            self.driver.register_observed_target(observation)
        self.log.debug("Finished registering observations.")

    async def _parse_observation_database(
        self, database_path: str
    ) -> typing.List[DriverTarget]:
        """Parse observations database.

        Parameters
        ----------
        database_path : `str`
            Path to the local database file.

        Returns
        -------
        `list`[`DriverTargets`]
            List of observations.
        """
        loop = asyncio.get_running_loop()

        parse_observation_database = functools.partial(
            self.driver.parse_observation_database,
            filename=database_path,
        )

        return await loop.run_in_executor(None, parse_observation_database)

    async def _query_observations_from_efd(
        self, efd_query: str
    ) -> typing.List[DriverTarget]:
        """Query observations from EFD.

        Parameters
        ----------
        efd_query : `str`
            EFD query to retrieve list of observations.

        Returns
        -------
        observations : `list`[`DriverTargets`]
            List of observations.
        """
        efd_observations = (
            await self.telemetry_stream_handler.efd_client.influx_client.query(
                efd_query
            )
        )

        loop = asyncio.get_running_loop()

        convert_efd_observations_to_targets = functools.partial(
            self.driver.convert_efd_observations_to_targets,
            efd_observations=efd_observations,
        )

        return await loop.run_in_executor(None, convert_efd_observations_to_targets)

    async def _get_block_status(self, program: str) -> ObservingBlockStatus:
        """Get block status.

        Parameters
        ----------
        program : `str`
            Name of the program.

        Returns
        -------
        `ObservingBlockStatus`
            Block status.

        Notes
        -----
        This method will query the EFD for the latest status of the input
        program and return an `ObservingBlockStatus` built with the
        appropriate information. If no block is found return a new empty one.
        """

        topic = '"efd"."autogen"."lsst.sal.Scheduler.logevent_blockStatus"'
        query = (
            f"SELECT * FROM {topic} WHERE id = '{program}' ORDER BY time DESC LIMIT 1"
        )
        query_res = await self.telemetry_stream_handler.efd_client.influx_client.query(
            query
        )

        if len(query_res) == 0:
            return ObservingBlockStatus(
                executions_completed=0,
                executions_total=0,
                status=BlockStatus.AVAILABLE,
            )
        else:
            return ObservingBlockStatus(
                executions_completed=query_res["executionsCompleted"][0],
                executions_total=query_res["executionsTotal"][0],
                status=BlockStatus(query_res["statusId"][0]),
            )

    async def update_telemetry(self):
        """Update data on all the telemetry values."""

        try:
            if self.telemetry_stream_handler is not None:
                self.log.debug("Updating telemetry stream.")

                for telemetry in self.telemetry_stream_handler.telemetry_streams:
                    telemetry_data = (
                        await self.telemetry_stream_handler.retrieve_telemetry(
                            telemetry
                        )
                    )

                    self.raw_telemetry[telemetry] = (
                        telemetry_data[0]
                        if len(telemetry_data) == 1
                        else telemetry_data
                    )
            else:
                self.log.debug("Telemetry stream not configured.")

            self.models["observatory_model"].update_state(
                utils.astropy_time_from_tai_unix(utils.current_tai()).unix
            )

            loop = asyncio.get_event_loop()

            await loop.run_in_executor(None, self.driver.update_conditions)

        except Exception as exception:
            raise UpdateTelemetryError("Failed to update telemetry.") from exception
