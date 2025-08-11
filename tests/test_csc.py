# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
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

import asyncio
import contextlib
import glob
import logging
import os
import pathlib
import unittest

import numpy as np
from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.mock import ObservatoryStateMock
from lsst.ts.scheduler.utils import SchedulerModes
from lsst.ts.scheduler.utils.csc_utils import DetailedState
from lsst.ts.scheduler.utils.error_codes import OBSERVATORY_STATE_UPDATE

SHORT_TIMEOUT = 10.0
LONG_TIMEOUT = 30.0
LONG_LONG_TIMEOUT = 120.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class TestSchedulerCSC(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestSchedulerCSC")

    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        self.assertEqual(initial_state, salobj.State.STANDBY)

        return SchedulerCSC(
            index=1, config_dir=config_dir, simulation_mode=simulation_mode
        )

    async def test_bin_script(self):
        await self.check_bin_script("Scheduler", 1, "run_scheduler")

    async def test_no_observatory_state_ok_in_disabled(self):
        """Test CSC goes to FAULT if no observatory state."""

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), self.make_script_queue(running=True):
            await self.assert_next_sample(topic=self.remote.evt_errorCode, errorCode=0)
            try:
                self.remote.evt_summaryState.flush()

                with self.assertLogs(self.csc.log) as csc_logs:
                    await self.remote.cmd_start.set_start(timeout=LONG_TIMEOUT)

                    await self.remote.tel_observatoryState.next(
                        flush=True, timeout=SHORT_TIMEOUT
                    )

                assert (
                    "WARNING:Scheduler:Failed to update observatory state. "
                    f"Ignoring, scheduler in {salobj.State.DISABLED!r}."
                ) in csc_logs.output

                await self.assert_next_summary_state(salobj.State.DISABLED, flush=False)
                with self.assertRaises(asyncio.TimeoutError):
                    await self.assert_next_summary_state(
                        salobj.State.FAULT,
                        flush=False,
                        timeout=SHORT_TIMEOUT,
                    )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_no_observatory_state_ok_in_enabled_not_running(self):
        """Test CSC goes to FAULT if no observatory state."""

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), self.make_script_queue(running=True):
            await self.assert_next_sample(topic=self.remote.evt_errorCode, errorCode=0)
            try:
                self.remote.evt_summaryState.flush()

                with self.assertLogs(self.csc.log) as csc_logs:
                    await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

                    await self.remote.tel_observatoryState.next(flush=True)

                assert (
                    "WARNING:Scheduler:Failed to update observatory state. "
                    f"Ignoring, scheduler in {salobj.State.ENABLED!r} but not running."
                ) in csc_logs.output

                await self.assert_next_summary_state(salobj.State.DISABLED, flush=False)
                await self.assert_next_summary_state(salobj.State.ENABLED, flush=False)
                with self.assertRaises(asyncio.TimeoutError):
                    await self.assert_next_summary_state(
                        salobj.State.FAULT,
                        flush=False,
                        timeout=SHORT_TIMEOUT,
                    )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_no_observatory_state_fault_in_enabled_running_queue_running(self):
        """Test CSC goes to FAULT if no observatory state."""

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), self.make_script_queue(running=True):
            await self.assert_next_sample(topic=self.remote.evt_errorCode, errorCode=0)
            try:
                self.remote.evt_summaryState.flush()

                await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

                await self.remote.cmd_resume.start(timeout=SHORT_TIMEOUT)

                await self.assert_next_summary_state(salobj.State.DISABLED, flush=False)
                await self.assert_next_summary_state(salobj.State.ENABLED, flush=False)
                await self.assert_next_summary_state(salobj.State.FAULT, flush=False)

                # Check error code
                await self.assert_next_sample(
                    topic=self.remote.evt_errorCode, errorCode=OBSERVATORY_STATE_UPDATE
                )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_no_observatory_state_ok_in_enabled_running_queue_pause(self):
        """Test CSC goes to FAULT if no observatory state."""

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), self.make_script_queue(running=False):
            await self.assert_next_sample(topic=self.remote.evt_errorCode, errorCode=0)
            try:
                self.remote.evt_summaryState.flush()

                await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

                await self.remote.cmd_resume.start(timeout=SHORT_TIMEOUT)

                await self.assert_next_summary_state(salobj.State.DISABLED, flush=False)
                await self.assert_next_summary_state(salobj.State.ENABLED, flush=False)
                with self.assertRaises(asyncio.TimeoutError):
                    await self.assert_next_summary_state(
                        salobj.State.FAULT,
                        flush=False,
                        timeout=SHORT_TIMEOUT,
                    )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_standard_state_transitions(self):
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            self.remote.evt_detailedState.flush()

            await self.check_standard_state_transitions(
                enabled_commands=[
                    "resume",
                    "stop",
                    "load",
                    "computePredictedSchedule",
                    "addBlock",
                    "removeBlock",
                    "validateBlock",
                    "getBlockStatus",
                ]
            )
            await self.assert_next_sample(
                self.remote.evt_detailedState,
                flush=False,
                substate=DetailedState.IDLE,
            )
            await self.assert_next_sample(
                self.remote.evt_cameraConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_telescopeConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_rotatorConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_domeConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_slewConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_opticsLoopCorrConfig,
                flush=False,
            )
            await self.assert_next_sample(
                self.remote.evt_parkConfig,
                flush=False,
            )

    async def test_configuration_invalid(self):
        """Test basic configuration."""
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            try:
                invalid_files = glob.glob(
                    os.path.join(TEST_CONFIG_DIR, "invalid_*.yaml")
                )
                bad_config_names = [os.path.basename(name) for name in invalid_files]
                bad_config_names.append("no_such_file.yaml")
                for bad_config_name in bad_config_names:
                    with self.subTest(
                        bad_config_name=bad_config_name,
                        msg=f"Testing bad configuration: {bad_config_name}.",
                    ):
                        with salobj.testutils.assertRaisesAckError():
                            await self.remote.cmd_start.set_start(
                                configurationOverride=bad_config_name,
                                timeout=SHORT_TIMEOUT,
                            )
                self.remote.evt_summaryState.flush()
                await self.remote.cmd_start.set_start(
                    configurationOverride="", timeout=SHORT_TIMEOUT
                )
                assert salobj.State(self.csc.summary_state) == salobj.State.DISABLED
                state = await self.remote.evt_summaryState.next(
                    flush=False, timeout=SHORT_TIMEOUT
                )
                assert salobj.State(state.summaryState) == salobj.State.DISABLED
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    @unittest.mock.patch(
        "lsst.ts.scheduler.too_client.TooClient.get_too_alerts", dict()
    )
    async def test_configuration_valid(self):
        """Test basic configuration."""
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            try:
                test_files = glob.glob(os.path.join(TEST_CONFIG_DIR, "valid_*.yaml"))
                valid_config_names = [os.path.basename(name) for name in test_files]
                for valid_config in valid_config_names:
                    await salobj.set_summary_state(self.remote, salobj.State.STANDBY)
                    self.log.info(f"Testing good configuration: {valid_config}.")
                    with self.subTest(good_config_name=valid_config):
                        self.remote.evt_summaryState.flush()
                        await self.remote.cmd_start.set_start(
                            configurationOverride=valid_config,
                            timeout=SHORT_TIMEOUT,
                        )
                        assert (
                            salobj.State(self.csc.summary_state)
                            == salobj.State.DISABLED
                        )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_custom_filters(self):

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            try:
                configuration_override = os.path.join(
                    TEST_CONFIG_DIR, "custom_filters.yaml"
                )
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)
                self.remote.evt_summaryState.flush()
                await self.remote.cmd_start.set_start(
                    configurationOverride=configuration_override,
                    timeout=SHORT_TIMEOUT,
                )
                expected_current_filter = "r_57"
                expected_filter_mounted = "g_6,r_57,y_10,,"
                expected_filter_removable = "u,g_6,r_57,i,y_10,z"
                expected_filter_unmounted = "u,i,z"
                await self.assert_next_sample(
                    self.remote.evt_cameraConfig,
                    filterMounted=expected_filter_mounted,
                    filterRemovable=expected_filter_removable,
                    filterUnmounted=expected_filter_unmounted,
                    flush=False,
                )
                self.log.info(f"{self.csc.model.models['observatory_model']}")
                await self.remote.cmd_enable.start(timeout=SHORT_TIMEOUT)
                observatory_state = await self.assert_next_sample(
                    self.remote.tel_observatoryState,
                    flush=True,
                    filterMounted=expected_filter_mounted,
                    filterUnmounted=expected_filter_unmounted,
                    filterPosition=expected_current_filter,
                )
                self.log.info(f"{observatory_state=}")
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_filter_band_mapping(self):

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTCamera"
        ) as camera:
            try:
                # Publish available filters from instrument, should pick this
                # up when enabled.
                await camera.evt_availableFilters.set_write(
                    filterNames="NONE,g_6,u_24,i_39,r_57"
                )
                await camera.evt_endSetFilter.set_write(filterName="r_57")
                configuration_override = os.path.join(
                    TEST_CONFIG_DIR, "filter_band_mapping.yaml"
                )
                await salobj.set_summary_state(
                    self.remote, salobj.State.ENABLED, override=configuration_override
                )
                expected_current_filter = "r"
                expected_filter_mounted = ",g,u,i,r"

                await self.assert_next_sample(
                    self.remote.tel_observatoryState,
                    flush=True,
                    filterMounted=expected_filter_mounted,
                    filterPosition=expected_current_filter,
                )

                await self.remote.cmd_resume.start(timeout=SHORT_TIMEOUT)

                # Publish a filter that is not mapped should cause
                # the Scheduler to go to fault.
                self.remote.evt_summaryState.flush()

                await camera.evt_endSetFilter.set_write(filterName="Pinhole")
                await self.assert_next_summary_state(salobj.State.FAULT)

                # Publish a valid filter again.
                await camera.evt_endSetFilter.set_write(filterName="r_57")

                await salobj.set_summary_state(
                    self.remote, salobj.State.ENABLED, override=configuration_override
                )

                await self.remote.cmd_resume.start(timeout=SHORT_TIMEOUT)

                self.remote.evt_summaryState.flush()

                await camera.evt_availableFilters.set_write(
                    filterNames="NONE,Pinhole,u_24,i_39,r_57"
                )

                await self.assert_next_summary_state(salobj.State.FAULT)

                # Now publish a smaller number of filters.
                await camera.evt_availableFilters.set_write(
                    filterNames="NONE,g_6,u_24,i_39"
                )

                await salobj.set_summary_state(
                    self.remote, salobj.State.ENABLED, override=configuration_override
                )

                self.remote.evt_summaryState.flush()

                await self.remote.cmd_resume.start(timeout=SHORT_TIMEOUT)

                # CSC should not go to Fault.
                with self.assertRaises(asyncio.TimeoutError):
                    await self.assert_next_summary_state(
                        salobj.State.FAULT, timeout=SHORT_TIMEOUT
                    )

            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_load(self):
        """Test load command."""
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            config = (
                pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "test_observing_list.yaml")
            )

            bad_config = (
                pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "bad_config.yaml")
            )

            try:
                await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

                await self.remote.cmd_load.set_start(
                    uri=config.as_uri(), timeout=SHORT_TIMEOUT
                )

                with salobj.assertRaisesAckError():
                    await self.remote.cmd_load.set_start(
                        uri=bad_config.as_uri(), timeout=SHORT_TIMEOUT
                    )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_compute_predicted_schedule(self):
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.MOCKS3,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            try:
                await salobj.set_summary_state(
                    self.remote,
                    salobj.State.ENABLED,
                    override="advance_target_loop_fbs.yaml",
                )

                await self.remote.cmd_computePredictedSchedule.start(
                    timeout=SHORT_TIMEOUT
                )

                predicted_schedule = await self.assert_next_sample(
                    topic=self.remote.evt_predictedSchedule
                )
                exptimes = np.array(predicted_schedule.exptime)
                predicted_observing_time = np.sum(exptimes[~np.isnan(exptimes)])

                assert predicted_schedule.numberOfTargets > 0
                assert predicted_observing_time < 2.0 * 60.0 * 60.0

                for i, (ra, dec, rotSkyPos, mjd, exptime, nexp) in enumerate(
                    zip(
                        predicted_schedule.ra,
                        predicted_schedule.decl,
                        predicted_schedule.rotSkyPos,
                        predicted_schedule.mjd,
                        predicted_schedule.exptime,
                        predicted_schedule.nexp,
                    )
                ):
                    if i < predicted_schedule.numberOfTargets:
                        assert np.isscalar(ra)
                        assert np.isscalar(dec)
                        assert np.isscalar(rotSkyPos)
                        assert np.isscalar(mjd)
                        assert np.isscalar(exptime)
                        assert np.isscalar(nexp)
                        assert mjd > 0.0
                    else:
                        assert np.isnan(ra)
                        assert np.isnan(dec)
                        assert np.isnan(rotSkyPos)
                        assert np.isnan(mjd)
                        assert np.isnan(exptime)
                        assert np.isnan(nexp)

            finally:
                await salobj.set_summary_state(
                    self.remote,
                    salobj.State.STANDBY,
                )

    async def test_disable_while_computing_predicted_schedule(self):
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.MOCKS3,
        ), ObservatoryStateMock(), self.make_script_queue(running=True):
            try:
                await salobj.set_summary_state(
                    self.remote,
                    salobj.State.ENABLED,
                    override="advance_target_loop_fbs.yaml",
                )

                # Reduce CSC loop_die_timeout so test will run faster
                self.csc.loop_die_timeout = 1.0

                self.remote.evt_detailedState.flush()

                compute_predicted_schedule_cmd_task = asyncio.create_task(
                    self.remote.cmd_computePredictedSchedule.start(
                        timeout=SHORT_TIMEOUT
                    )
                )

                while True:
                    detailed_state = await self.remote.evt_detailedState.next(
                        flush=False,
                        timeout=SHORT_TIMEOUT,
                    )
                    if (
                        detailed_state.substate
                        == DetailedState.COMPUTING_PREDICTED_SCHEDULE
                    ):
                        self.log.info("Disabling scheduler.")
                        await self.remote.cmd_disable.start(timeout=SHORT_TIMEOUT)
                        break

                with self.assertRaises(salobj.AckError):
                    await compute_predicted_schedule_cmd_task

            finally:
                await salobj.set_summary_state(
                    self.remote,
                    salobj.State.STANDBY,
                )

    @contextlib.asynccontextmanager
    async def make_script_queue(self, running: bool) -> None:
        self.log.debug("Make queue.")
        async with salobj.Controller("ScriptQueue", index=1) as queue:

            async def show_schema(data) -> None:
                self.log.debug(f"Show schema: {data}")
                await queue.evt_configSchema.set_write(
                    path=data.path,
                    isStandard=data.isStandard,
                    configSchema="""
$schema: http://json-schema.org/draft-07/schema#
type: object
properties:
    name:
        type: string
        description: Target name.
    ra:
        type: string
        description: >-
            The right ascension of the target in hexagesimal format,
            e.g. HH:MM:SS.S.
    dec:
        type: string
        description: >-
            The declination of the target in hexagesimal format,
            e.g. DD:MM:SS.S.
    rot_sky:
        type: number
        description: The sky angle (degrees) of the target.
    estimated_slew_time:
        type: number
        description: Estimated slew time (seconds).
        default: 0.
    obs_time:
        type: number
        description: Estimated observing time (seconds).
        default: 0.
    note:
        type: string
        description: Survey note.
        default: ""
additionalProperties: true
                    """,
                )

            queue.cmd_showSchema.callback = show_schema
            await queue.evt_queue.set_write(running=running)
            yield


if __name__ == "__main__":
    unittest.main()
