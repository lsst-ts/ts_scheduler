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

__all__ = ["SchedulerCSC"]

import pathlib
import shutil
import asyncio
import functools
import inspect
import logging
import time
import traceback
import dataclasses
import typing

import urllib.request

import numpy as np

from importlib import import_module

from lsst.ts import utils
from lsst.ts import salobj
from lsst.ts.idl.enums import ScriptQueue, Script

from . import __version__
from . import CONFIG_SCHEMA
from .utils.csc_utils import (
    SchedulerModes,
    NonFinalStates,
    is_uri,
    is_valid_efd_query,
)

from .utils.error_codes import (
    NO_QUEUE,
    PUT_ON_QUEUE,
    SIMPLE_LOOP_ERROR,
    ADVANCE_LOOP_ERROR,
    UNABLE_TO_FIND_TARGET,
    OBSERVATORY_STATE_UPDATE,
)
from .utils.parameters import SchedulerCscParameters
from .utils.exceptions import UnableToFindTarget
from .driver import Driver
from .driver.survey_topology import SurveyTopology
from .driver.driver_target import DriverTarget

from . import TelemetryStreamHandler

from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.dateloc import version as dateloc_version
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import version as obs_mod_version
from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.astrosky.model import version as astrosky_version

from rubin_sim.site_models.seeingModel import SeeingModel
from rubin_sim.version import __version__ as rubin_sim_version
from rubin_sim.site_models.cloudModel import CloudModel
from rubin_sim.site_models.downtimeModel import DowntimeModel


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

        # How far to step into the future when there's not targets in seconds
        self.time_delta_no_target = 30.0
        # The maximum tolerable time without targets in seconds.
        self.max_time_no_target = 3600.0

        # How long to wait for target loop to stop before killing it
        self.loop_die_timeout = 5.0

        self.telemetry_stream_handler = None

        # Dictionaries to store information about the scripts put on the queue
        self.models = dict()
        self.raw_telemetry = dict()
        self.script_info = dict()

        # This asyncio.Event is used to control when the scheduling task will
        # be running or not, once the CSC is in enable. By default, the loop
        # will not run once the CSC is enabled, and a "resume" command is
        # needed to start it.
        self.run_target_loop = asyncio.Event()

        # Lock for the event loop. This is used to synchronize actions that
        # will affect the target production loop.
        self.target_loop_lock = asyncio.Lock()

        self.driver = None

        # Stores the coroutine for the target production.
        self.target_production_task = None

        # A flag to indicate that the event loop is running
        self.run_loop = False

        # Add callback to script info
        self.queue_remote.evt_script.callback = self.callback_script_info

        # Telemetry loop. This will take care of observatory state.
        self.telemetry_loop_task = None

        # List of targets used in the ADVANCE target loop
        self.targets_queue = []

        # keep track whether a "no new target" condition was handled by the
        # scheduler.
        self._no_target_handled = False

        # Future to store the results or target_queue check.
        self.targets_queue_condition = utils.make_done_future()

        # Task with a timer to evaluate next target when none is produced by
        # the scheduler.
        self.next_target_timer = utils.make_done_future()

        # Large file object available
        self.s3bucket_name = None  # Set by `configure`.
        self.s3bucket = None  # Set by `handle_summary_state`.

        self.startup_types = dict(
            HOT=self.configure_driver_hot,
            WARM=self.configure_driver_warm,
            COLD=self.configure_driver_cold,
        )

    async def begin_start(self, data):
        try:
            await super().begin_start(data)
        except Exception:
            self.log.exception("Error in beging start")
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

        # Make sure event is not set so loops won't start once the CSC is
        # enabled.
        self.run_target_loop.clear()

        if self.simulation_mode == SchedulerModes.SIMULATION:
            self.log.debug("Running in simulation mode. No target production loop.")
            self.target_production_task = None

        elif self.parameters.mode == "SIMPLE":

            self.target_production_task = asyncio.create_task(
                self.simple_target_production_loop()
            )

        elif self.parameters.mode == "ADVANCE":

            self.target_production_task = asyncio.create_task(
                self.advance_target_production_loop()
            )

        elif self.parameters.mode == "DRY":

            self.target_production_task = None

        else:
            # This will just reject the command
            raise RuntimeError("Unrecognized scheduler mode %s" % self.parameters.mode)

    async def handle_summary_state(self):
        """Handle summary state.

        If the component is DISABLED or ENABLED, it will make sure the
        telemetry loop is running. Shutdown the telemetry loop if in STANDBY.
        """

        if self.disabled_or_enabled and self.telemetry_loop_task is None:
            self.run_loop = True
            self.telemetry_loop_task = asyncio.create_task(self.telemetry_loop())

            await self.reset_handle_no_targets_on_queue()

            if self.s3bucket is None:
                mock_s3 = self.simulation_mode == SchedulerModes.MOCKS3
                self.s3bucket = salobj.AsyncS3Bucket(
                    name=self.s3bucket_name, domock=mock_s3, create=mock_s3
                )

        elif (
            self.summary_state == salobj.State.STANDBY
            and self.telemetry_loop_task is not None
        ):
            self.run_loop = False
            try:
                await asyncio.wait_for(
                    self.telemetry_loop_task, timeout=self.loop_die_timeout
                )
            except asyncio.TimeoutError:
                self.log.debug("Timeout waiting for telemetry loop to finish.")
                self.telemetry_loop_task.cancel()
                try:
                    await self.telemetry_loop_task
                except asyncio.CancelledError:
                    self.log.debug("Telemetry loop cancelled.")
                except Exception:
                    self.log.exception("Unexpected error cancelling telemetry loop.")
            finally:
                self.telemetry_loop_task = None

            if self.s3bucket is not None:
                self.s3bucket.stop_mock()
            self.s3bucket = None

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
                self.run_target_loop.clear()
                self.run_loop = False
                wait_start = time.time()
                while not self.target_production_task.done():
                    await asyncio.sleep(self.parameters.loop_sleep_time)
                    elapsed = time.time() - wait_start
                    self.log.debug(
                        f"Waiting target loop to finish (elapsed: {elapsed:0.2f} s, "
                        f"timeout: {self.loop_die_timeout} s)..."
                    )
                    if elapsed > self.loop_die_timeout:
                        self.log.warning("Target loop not stopping, cancelling it...")
                        self.target_production_task.cancel()
                        break

                try:
                    await self.target_production_task
                except asyncio.CancelledError:
                    self.log.info("Target production task cancelled...")
        except Exception:
            self.log.exception("Error while disabling the Scheduler. Ignoring...")
        finally:
            self.target_production_task = None

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

        self.run_target_loop.clear()

        if data.abort:
            async with self.target_loop_lock:
                await self.remove_from_queue(self.raw_telemetry["scheduled_targets"])

        await self.reset_handle_no_targets_on_queue()

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

        await self._handle_load_snapshot(data.uri)

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
                if (
                    self.summary_state == salobj.State.ENABLED
                    and self.run_target_loop.is_set()
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
                    message_text = (
                        " but not running"
                        if self.summary_state == salobj.State.ENABLED
                        else ""
                    )
                    self.log.warning(
                        "Failed to update observatory state. "
                        f"Ignoring, scheduler in {self.summary_state!r}{message_text}."
                    )

            await self.tel_observatoryState.set_write(
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

    async def handle_observatory_state(self):
        """Handle observatory state."""

        current_target_state = await self.ptg.tel_currentTargetStatus.next(
            flush=True, timeout=self.heartbeat_interval
        )

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

    def init_telemetry(self):
        """Initialized telemetry streams."""

        # List of scheduled targets and script ids
        self.raw_telemetry["scheduled_targets"] = None

        # List of things on the observatory queue
        self.raw_telemetry["observing_queue"] = []

    async def update_telemetry(self):
        """Update data on all the telemetry values."""

        if self.telemetry_stream_handler is not None:
            self.log.debug("Updating telemetry stream.")

            for telemetry in self.telemetry_stream_handler.telemetry_streams:
                telemetry_data = await self.telemetry_stream_handler.retrive_telemetry(
                    telemetry
                )

                self.raw_telemetry[telemetry] = (
                    telemetry_data[0] if len(telemetry_data) == 1 else telemetry_data
                )
        else:
            self.log.debug("Telemetry stream not configured.")

        self.models["observatory_model"].update_state(
            utils.astropy_time_from_tai_unix(utils.current_tai()).unix
        )

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(None, self.driver.update_conditions)

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

        self.log.debug("Configuring telemetry streams.")

        if len(self.raw_telemetry) == 0:
            self.log.warning("Telemetry stream not initialized. Initializing...")
            self.init_telemetry()

        await self.configure_telemetry_streams(config.telemetry)

        self.log.debug("Configuring models.")

        if len(self.models) == 0:
            self.log.warning("Models are not initialized. Initializing...")
            self.init_models()

        for model in self.models:
            # TODO: This check will give us time to implement the required
            # changes on the models.
            if model in config.models:
                self.log.debug(f"Configuring {model}")
                try:
                    self.models[model].configure(config.models[model])
                except Exception:
                    self.log.exception(f"Failed to configure model {model}.")
            else:
                self.log.warning(f"No configuration for {model}. Skipping.")

        self.log.debug("Configuring Driver and Scheduler.")

        survey_topology = await self.configure_driver(config)

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

    async def configure_telemetry_streams(self, config: typing.Dict) -> None:
        """Configure telemetry streams.

        Parameters
        ----------
        config : `dict`
            Telemetry stream configuration.
        """

        if "streams" not in config:
            self.log.warning(
                "No telemetry stream defined in configuration. Skipping configuring telemetry streams."
            )
            return

        self.log.debug(
            f"Configuring telemetry stream handler for {config['efd_name']} efd instance."
        )

        self.telemetry_stream_handler = TelemetryStreamHandler(
            log=self.log, efd_name=config["efd_name"]
        )

        self.log.debug("Configuring telemetry stream.")

        await self.telemetry_stream_handler.configure_telemetry_stream(
            config["streams"]
        )

        for telemetry in self.telemetry_stream_handler.telemetry_streams:
            self.raw_telemetry[telemetry] = np.nan

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
        that it will skip configuring the drive altogether it the driver is
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

        self._load_driver_from(config.driver_type)

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

        self._load_driver_from(config.driver_type)

        survey_topology = await self._handle_driver_configure_scheduler(config)

        await self._handle_startup_database_snapshot(config.startup_database)

        return survey_topology

    async def configure_driver_cold(self, config: typing.Any) -> SurveyTopology:
        """Perform cold start.

        Cold start is the slowest start up and, in general, will only be used
        in cases where the scheduler configuration changed quite drastically
        but one still wants to account previous observations into account. As
        such, cold start will most likely only be used before the night starts
        on some very limited situations.

        In this case the scheduler stars by creating the driver, overriding any
        previous driver.

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

        self._load_driver_from(config.driver_type)

        survey_topology = await self._handle_driver_configure_scheduler(config)

        await self._handle_startup_database_observation_db(config.startup_database)

        return survey_topology

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
                self.log.debug("No state from queue. Requesting...")
                self.queue_remote.evt_queue.flush()
                await self.queue_remote.cmd_showQueue.start(
                    timeout=self.parameters.cmd_timeout
                )
                queue = await self.queue_remote.evt_queue.next(
                    flush=False, timeout=self.parameters.cmd_timeout
                )
        except salobj.AckError as e:
            self.log.error("No response from queue...")
            await self.fault(
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

            if info.scriptState == Script.ScriptState.DONE:
                # Script completed successfully
                self.log.debug(
                    f"{target.note} observation completed successfully. "
                    "Registering observation."
                )
                await self.register_observation(target)
                # Remove related script from the list
                del self.script_info[target.sal_index]
                # target now simply disappears... Should I keep it in for
                # future refs?
            elif info.scriptState in NonFinalStates:
                # script in a non-final state, just put it back on the list.
                self.raw_telemetry["scheduled_targets"].append(target)
            elif info.scriptState == Script.ScriptState.FAILED:
                self.log.warning(
                    f"{target.note} failed. Not registering observation.",
                )
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False
            else:
                self.log.error(
                    "Unrecognized state [%i] for observation %i for target %s.",
                    info.scriptState,
                    target.sal_index,
                    target,
                )
                # Remove related script from the list
                del self.script_info[target.sal_index]
                retval = False

        return retval

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
        self.raw_telemetry["scheduled_targets"] = []

        loop = asyncio.get_event_loop()

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
                    first_pass = not await self.check_scheduled()

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

                        await self.update_telemetry()

                        target = await loop.run_in_executor(
                            None, self.driver.select_next_target
                        )

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
                            self.raw_telemetry["scheduled_targets"].append(target)
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
        self.raw_telemetry["scheduled_targets"] = []

        first_pass = True
        targets_queue_condition_task = utils.make_done_future()

        self.targets_queue = []
        self.targets_queue_condition = utils.make_done_future()

        while self.summary_state == salobj.State.ENABLED and self.run_loop:

            if not self.next_target_timer.done():
                self.log.debug("Waiting next target timer task...")
                await self.next_target_timer

            await self.run_target_loop.wait()

            try:
                if (
                    self.targets_queue_condition.done()
                    and self.targets_queue_condition.result() is None
                ):
                    # The condition in which we have to generate a target queue
                    # is when the targets_queue_condition future is done and
                    # its result is None. If the future is not done, the task
                    # that checks the queue is still ongoing. If the results is
                    # different than None it means the queue is ok and it does
                    # not need to be generated.
                    # Note that this is also the initial condition, so the
                    # target list is generated the first time the loop runs.
                    await self.generate_target_queue()

                async with self.target_loop_lock:

                    # If it is the first pass get the current queue, otherwise
                    # wait for the queue to change or get the latest if there's
                    # some
                    queue = await self.get_queue(first_pass)

                    # This returns False if script failed, in which case next
                    # pass won't wait for queue to change
                    first_pass = not await self.check_scheduled()

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
                        # TODO: publish detailed state indicating that the
                        # scheduler is selecting a target

                        # Take a target from the queue
                        target = self.targets_queue.pop(0)

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
                            self.raw_telemetry["scheduled_targets"].append(target)
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

                        timer_task = asyncio.sleep(self.parameters.loop_sleep_time)
                        # Using the asycio.wait with a timeout will simply
                        # return at the end without cancelling the task. If the
                        # check takes less then the loop_sleep_time, we still
                        # want to wait the remaining of the time, so that is
                        # why we have the additional task.
                        # The following await will not take more or less than
                        # approximately self.parameters.loop_sleep_time.
                        await asyncio.wait(
                            [
                                timer_task,
                                targets_queue_condition_task,
                            ],
                            timeout=self.parameters.loop_sleep_time,
                        )

            except asyncio.CancelledError:
                break
            except UnableToFindTarget:
                # If there is an exception and not in FAULT, go to FAULT state
                # and log the exception...
                if self.summary_state != salobj.State.FAULT:
                    await self.fault(
                        code=UNABLE_TO_FIND_TARGET,
                        report=f"Unable to find target in the next {self.max_time_no_target/60./60.} hours.",
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

    async def generate_target_queue(self):
        """Generate target queue.

        This method will save the current state of the scheduler, play the
        scheduler for the future, generating a list of observations.

        """
        last_scheduler_state_filename = await self.save_scheduler_state()

        self.log.debug(f"Target queue contains {len(self.targets_queue)} targets.")

        loop = asyncio.get_running_loop()

        # Note that here it runs the update_telemetry method from the
        # scheduler. This method will update the telemetry based on most
        # current recent data in the system.
        await self.update_telemetry()

        # Synchronize observatory model state with current observatory state.
        self.models["observatory_model"].set_state(self.models["observatory_state"])
        self.models["observatory_model"].start_tracking(
            self.models["observatory_state"].time
        )

        self.log.debug("Registering current scheduled targets.")

        for target in self.raw_telemetry["scheduled_targets"]:
            self.log.debug(f"Temporarily registering scheduled target: {target.note}.")
            self.driver.register_observed_target(target)
            self.models["observatory_model"].observe(target)

        # For now it will only generate enough targets to send to the queue
        # and leave one extra in the internal queue. In the future we will
        # generate targets to fill the
        # self.parameters.predicted_scheduler_window.
        # But then we will have to improve how we handle the target generation
        # and the check_targets_queue_condition.
        self.log.debug(
            f"Requesting {self.parameters.n_targets + 1} additional targets."
        )

        while len(self.targets_queue) <= self.parameters.n_targets + 1:

            # Inside the loop we are running update_conditions directly from
            # the driver instead if update_telemetry. This bypasses the updates
            # done by the CSC method.
            await loop.run_in_executor(None, self.driver.update_conditions)

            target = await loop.run_in_executor(None, self.driver.select_next_target)

            if target is None:
                self.log.debug(
                    f"No target from the scheduler. Stopping with {len(self.targets_queue)}."
                )
                if len(self.targets_queue) == 0:
                    await self.handle_no_targets_on_queue()
                break
            else:
                await self.reset_handle_no_targets_on_queue()

                self.log.debug(
                    f"Temporarily registering selected target: {target.note}."
                )
                self.driver.register_observed_target(target)

                # The following will playback the observations on the
                # observatory model but will keep the observatory state
                # unchanged
                self.models["observatory_model"].observe(target)

                self.targets_queue.append(target)

        self.log.debug("Resetting scheduler state.")
        self.driver.reset_from_state(last_scheduler_state_filename)
        shutil.os.remove(last_scheduler_state_filename)

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

    async def save_scheduler_state(self):
        """Save scheduler state to S3 bucket and publish event."""

        file_object = self.driver.get_state_as_file_object()

        key = self.s3bucket.make_key(
            salname=self.salinfo.name,
            salindexname=self.salinfo.index,
            generator=f"{self.salinfo.name}:{self.salinfo.index}",
            date=utils.astropy_time_from_tai_unix(utils.current_tai()),
            suffix=".p",
        )

        scheduler_state_filename = "last_scheduler_state.p"
        saved_scheduler_state_filename = self.driver.save_state()

        try:
            await self.s3bucket.upload(fileobj=file_object, key=key)
            url = f"{self.s3bucket.service_resource.meta.client.meta.endpoint_url}/{self.s3bucket.name}/{key}"
            await self.evt_largeFileObjectAvailable.set_write(
                url=url, generator=f"{self.salinfo.name}:{self.salinfo.index}"
            )
        except Exception:
            self.log.exception(
                f"Could not upload file {key} to S3. Keeping file {saved_scheduler_state_filename}."
            )
            return shutil.copy(saved_scheduler_state_filename, scheduler_state_filename)
        else:
            return shutil.move(saved_scheduler_state_filename, scheduler_state_filename)

    async def handle_no_targets_on_queue(self):
        """Handle condition where there are note more targets on the queue."""
        if self._no_target_handled:
            self.log.debug("No targets condition already handled. Ignoring.")
            return

        self.log.warning(
            "Handling no targets on queue condition. "
            "This consist of queuing a stop tracking script and estimating the time until the next target."
        )

        self._no_target_handled = True

        stop_tracking_target = self.driver.get_stop_tracking_target()

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

        loop = asyncio.get_running_loop()

        time_start = self.models["observatory_model"].current_state.time
        time_evaluation = time_start

        self.models["observatory_model"].stop_tracking(time_evaluation)

        target = None
        while (
            target is None and (time_evaluation - time_start) < self.max_time_no_target
        ):
            await loop.run_in_executor(None, self.driver.update_conditions)

            time_evaluation += self.time_delta_no_target
            self.models["observatory_model"].update_state(time_evaluation)

            target = await loop.run_in_executor(None, self.driver.select_next_target)

        if target is None:
            raise UnableToFindTarget(
                f"Could not determine next target in allotted window: {self.max_time_no_target}s."
            )
        else:
            delta_time = time_evaluation - time_start
            self.log.debug(f"Next target: {target}.")
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
            # Removes old entries
            for key in self.script_info:
                del self.script_info[key]
                if len(self.script_info) < self.parameters.max_scripts:
                    break

    async def register_observation(self, target: DriverTarget) -> None:
        """Register observation.

        Parameters
        ----------
        observation : Observation
            Observation to be registered.
        """
        self.driver.register_observation(target=target)
        if hasattr(self, "evt_observation"):
            await self.evt_observation.set_write(
                **dataclasses.asdict(target.get_observation())
            )

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

    async def _handle_load_snapshot(self, uri: str) -> None:
        """Handler loading a scheduler snapshot asynchronously.

        Parameters
        ----------
        uri : str
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

    def _load_driver_from(self, driver_type: str) -> None:
        """Utility method to load a driver from a driver type.

        Parameters
        ----------
        driver_type : str
            A driver module "import string", e.g.
            "lsst.ts.scheduler.driver.driver".

        Raises
        ------
        RuntimeError:
            If a Driver cannot be found in the provided module.

        Notes
        -----

        The `driver_type` parameter must specify a python module which defines
        a subclass of `Driver`. The scheduler ships with a set of standard
        drivers, which are defined in `lsst.ts.scheduler.driver`. For example,
        `lsst.ts.scheduler.driver.feature_scheduler` defines `FeatureScheduler`
        which is a subclass of `Driver` and implements the feature based
        scheduler driver.

        Users can also provide external drivers, as long as they subclass
        `Driver` the CSC will be able to load it.
        """
        self.log.info("Loading driver from %s", driver_type)

        driver_lib = import_module(driver_type)
        members_of_driver_lib = inspect.getmembers(driver_lib)

        driver_type = None
        for member in members_of_driver_lib:
            try:
                if issubclass(member[1], Driver):
                    self.log.debug("Found driver %s%s", member[0], member[1])
                    driver_type = member[1]
            except TypeError:
                pass

        if driver_type is None:
            raise RuntimeError("Could not find Driver on module %s" % driver_type)

        self.driver = driver_type(
            models=self.models, raw_telemetry=self.raw_telemetry, log=self.log
        )

    async def _handle_startup_database_snapshot(self, startup_database: str) -> None:
        """Handle startup database snapshot.

        Parameters
        ----------
        startup_database : str
            Uri of the startup database.

        Raises
        ------
        RuntimeError
            If startup_database is invalid.
        """

        if is_uri(startup_database):
            self.log.info(f"Loading scheduler snapshot from {startup_database}.")
            await self._handle_load_snapshot(startup_database)
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
        startup_database : str
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
        database_path : str
            Path to the local database file.
        """
        observations = await self._parse_observation_database(database_path)

        await self._register_observations(observations)

    async def _handle_load_observations_from_efd(self, efd_query: str) -> None:
        """Handle loading observations from the EFD and playing them back into
        the driver.

        Parameters
        ----------
        efd_query : str
            A valid EFD query that should return a list of observations.
        """
        observations = await self._query_observations_from_efd(efd_query)

        self.log.info(
            "Loading observation history from EFD. "
            f"Query: {efd_query} yield {len(observations)} targets."
        )

        await self._register_observations(observations=observations)

    async def _parse_observation_database(
        self, database_path: str
    ) -> typing.List[DriverTarget]:
        """Parse observations database.

        Parameters
        ----------
        database_path : str
            Path to the local database file.

        Returns
        -------
        list of DriverTargets
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
        efd_query : str
            EFD query to retrieve list of observations.

        Returns
        -------
        observations : list of DriverTarget
            List of observations.
        """
        efd_observations = await self.telemetry_stream_handler.efd_client.query(
            efd_query
        )

        loop = asyncio.get_running_loop()

        convert_efd_observations_to_targets = functools.partial(
            self.driver.convert_efd_observations_to_targets,
            efd_observations=efd_observations,
        )

        return await loop.run_in_executor(None, convert_efd_observations_to_targets)

    async def _register_observations(
        self, observations: typing.List[DriverTarget]
    ) -> None:
        """Register a list of observations.

        Parameters
        ----------
        observations : list of DriverTarget
            List of observations.
        """
        if observations is None:
            self.log.warning("No observations to register")
            return
        self.log.debug(f"Registering {len(observations)} observations.")
        for observation in observations:
            self.driver.register_observed_target(observation)
        self.log.debug("Finished registering observations.")
