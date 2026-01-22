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
import pytest
from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.mock import ObservatoryStateMock
from lsst.ts.scheduler.utils import SchedulerModes
from lsst.ts.scheduler.utils.csc_utils import DetailedState
from lsst.ts.scheduler.utils.error_codes import OBSERVATORY_STATE_UPDATE
from lsst.ts.xml.component_info import ComponentInfo
from lsst.ts.xml.enums import Scheduler

SHORT_TIMEOUT = 10.0
LONG_TIMEOUT = 30.0
LONG_LONG_TIMEOUT = 120.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")

scheduler_info = ComponentInfo("Scheduler", "sal")
supports_observatory_status = "evt_observatoryStatus" in scheduler_info.topics


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
            if hasattr(self.remote, "evt_observatoryStatus"):
                await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=Scheduler.ObservatoryStatus.UNKNOWN,
                    statusLabels=Scheduler.ObservatoryStatus.UNKNOWN.name,
                    note=(
                        "Scheduler CSC started; "
                        "need to be in DISABLED or ENABLED to monitor observatory status."
                    ),
                )

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
                    "updateObservatoryStatus",
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
    @unittest.mock.patch("lsst_efd_client.EfdClient", unittest.mock.AsyncMock)
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

    @pytest.mark.skipif(
        not supports_observatory_status,
        reason="CSC interface does not support observatory status feature.",
    )
    async def test_observatory_status_fault_monitoring_csc_enabled(self):
        async with self.make_csc_cleanup_afterward(), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTMount"
        ) as mtmount, salobj.Controller(
            "MTRotator"
        ) as mtrotator:
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )
            await salobj.set_summary_state(
                self.remote,
                salobj.State.ENABLED,
                override="monitor_observatory_state.yaml",
            )

            # Disable monitoring observatory status so the
            # test can be more reliably executed.
            self.csc.enable_observatory_status_monitor = False

            def get_general_info_nighttime():
                return dict(isNight=True)

            self.csc.model.get_general_info = get_general_info_nighttime

            self.remote.evt_observatoryStatus.flush()
            # sending to command to set the state to
            # good would not always work for the test
            # as it is not allowed during daytime. So
            # to get around that I will skip the command
            # and force it by calling the method directly.
            await self.csc.set_observatory_status(
                status=Scheduler.ObservatoryStatus.OPERATIONAL,
                note="",
            )
            await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.OPERATIONAL,
                flush=False,
            )

            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            # Another component going to Fault will
            # trigger a new observatory status message.
            await mtrotator.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "MTRotator" in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            # While the components are in Fault
            # we cannot change the status back to good.
            expected_error_message = (
                "Cannot clear FAULT status, the following components are still in fault: "
                "MTMount, MTRotator"
            )
            with salobj.testutils.assertRaisesAckError(
                result_contains=expected_error_message
            ):
                await self.remote.cmd_updateObservatoryStatus.start(
                    timeout=SHORT_TIMEOUT
                )

            # Send mount to ENABLED and check that observatory status is
            # updated.
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTRotator" in observatory_status.note
            assert "MTMount" not in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            # Still cannot clear fault flag since MTRotator is still in Fault
            expected_error_message = (
                "Cannot clear FAULT status, the following components are still in fault: "
                "MTRotator"
            )
            with salobj.testutils.assertRaisesAckError(
                result_contains=expected_error_message
            ):
                await self.remote.cmd_updateObservatoryStatus.start(
                    timeout=SHORT_TIMEOUT
                )

            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.UNKNOWN,
                flush=False,
            )

            good_status_notes = [
                (
                    Scheduler.ObservatoryStatus.FAULT,
                    "Test manually setting flag to FAULT.",
                ),
                (
                    Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.WEATHER,
                    "Test manually setting flag to FAULT and WEATHER.",
                ),
                (
                    Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.DOWNTIME,
                    "Test manually setting flag to FAULT and DOWNTIME.",
                ),
                (
                    Scheduler.ObservatoryStatus.DOWNTIME
                    | Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.WEATHER,
                    "Test manually setting flag to DOWNTIME, FAULT and WEATHER.",
                ),
                (
                    Scheduler.ObservatoryStatus.DOWNTIME,
                    "Test manually setting flag to DOWNTIME.",
                ),
                (
                    Scheduler.ObservatoryStatus.WEATHER,
                    "Test manually setting flag to WEATHER.",
                ),
                (
                    Scheduler.ObservatoryStatus.WEATHER
                    | Scheduler.ObservatoryStatus.DOWNTIME,
                    "Test manually setting flag to WEATHER and DOWNTIME.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL,
                    "Test manually setting flag to OPERATIONAL.",
                ),
                (
                    Scheduler.ObservatoryStatus.UNKNOWN,
                    "Test manually setting flag to UNKNOWN.",
                ),
            ]

            for status, note in good_status_notes:

                await self.remote.cmd_updateObservatoryStatus.set_start(
                    status=status,
                    note=note,
                )

                observatory_status = await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status,
                    flush=False,
                )
                assert observatory_status.note == note

            bad_status_notes = [
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.DAYTIME,
                    "Cannot set operational and daytime.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.FAULT,
                    "Cannot set operational and fault.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.DOWNTIME,
                    "Cannot set operational and fault.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.DAYTIME,
                    "Cannot set operational, fault and daytime.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.DOWNTIME,
                    "Cannot set operational, fault and downtime.",
                ),
                (
                    Scheduler.ObservatoryStatus.OPERATIONAL
                    | Scheduler.ObservatoryStatus.FAULT
                    | Scheduler.ObservatoryStatus.DOWNTIME
                    | Scheduler.ObservatoryStatus.DAYTIME,
                    "Cannot set operational, fault, downtime and daytime.",
                ),
            ]

            for status, note in bad_status_notes:
                invalid_state_str = " | ".join(
                    [s.name for s in Scheduler.ObservatoryStatus if s & status]
                )
                expected_error_message = f"Invalid status: {invalid_state_str}."
                with salobj.testutils.assertRaisesAckError(
                    result_contains=expected_error_message
                ):
                    await self.remote.cmd_updateObservatoryStatus.set_start(
                        status=status,
                        note=note,
                    )

    @pytest.mark.skipif(
        not supports_observatory_status,
        reason="CSC interface does not support observatory status feature.",
    )
    async def test_observatory_status_fault_monitoring_csc_disabled(self):

        async with self.make_csc_cleanup_afterward(), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTMount"
        ) as mtmount, salobj.Controller(
            "MTRotator"
        ) as mtrotator:
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )
            await salobj.set_summary_state(
                self.remote,
                salobj.State.DISABLED,
                override="monitor_observatory_state.yaml",
            )

            # Disable monitoring observatory status so the
            # test can be more reliably executed.
            self.csc.enable_observatory_status_monitor = False

            self.remote.evt_observatoryStatus.flush()
            # sending to command to set the state to
            # good would not always work for the test
            # as it is not allowed during daytime. So
            # to get around that I will skip the command
            # and force it by calling the method directly.
            await self.csc.set_observatory_status(
                status=Scheduler.ObservatoryStatus.OPERATIONAL,
                note="",
            )
            await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.OPERATIONAL,
                flush=False,
            )

            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            # Another component going to Fault will
            # trigger a new observatory status message.
            await mtrotator.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "MTRotator" in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            # Send mount to ENABLED and check that observatory status is
            # updated.
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTRotator" in observatory_status.note
            assert "MTMount" not in observatory_status.note
            assert "fault" in observatory_status.note.lower()

            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.UNKNOWN,
                flush=False,
            )

    @pytest.mark.skipif(
        not supports_observatory_status,
        reason="CSC interface does not support observatory status feature.",
    )
    async def test_observatory_status_fault_monitoring_csc_standby(self):

        async with self.make_csc_cleanup_afterward(), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTMount"
        ) as mtmount:
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            await salobj.set_summary_state(
                self.remote,
                salobj.State.ENABLED,
                override="monitor_observatory_state.yaml",
            )
            await salobj.set_summary_state(
                self.remote,
                salobj.State.STANDBY,
                override="monitor_observatory_state.yaml",
            )

            self.remote.evt_observatoryStatus.flush()

            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            with self.assertRaises(asyncio.TimeoutError):
                await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    flush=False,
                )

    @pytest.mark.skipif(
        not supports_observatory_status,
        reason="CSC interface does not support observatory status feature.",
    )
    async def test_observatory_status_daytime_monitoring_csc_enabled(self):
        async with self.make_csc_cleanup_afterward(), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTMount"
        ) as mtmount, salobj.Controller(
            "MTRotator"
        ) as mtrotator:
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )
            await salobj.set_summary_state(
                self.remote,
                salobj.State.ENABLED,
                override="monitor_observatory_state.yaml",
            )

            # patch the model class to ensure calling get_general_info
            # returns that it is daytime
            def get_general_info_daytime():
                return dict(isNight=False)

            def get_general_info_nighttime():
                return dict(isNight=True)

            self.csc.model.get_general_info = get_general_info_daytime

            expected_initial_observatory_status_note = [
                (Scheduler.ObservatoryStatus.UNKNOWN, "Scheduler CSC started"),
                (Scheduler.ObservatoryStatus.UNKNOWN, "Scheduler CSC in STANDBY"),
                (
                    Scheduler.ObservatoryStatus.UNKNOWN,
                    "Observatory status feature enabled",
                ),
                (Scheduler.ObservatoryStatus.DAYTIME, "Daytime started"),
            ]

            for status, note in expected_initial_observatory_status_note:
                observatory_status = await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status,
                    flush=False,
                )
                assert note in observatory_status.note

            with self.assertRaises(asyncio.TimeoutError):
                await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    flush=False,
                )

            for status in Scheduler.ObservatoryStatus:
                if status == Scheduler.ObservatoryStatus.DAYTIME:
                    continue

                with salobj.testutils.assertRaisesAckError(
                    result_contains=f"Cannot set status to {status.name}; daytime flag is active."
                ):
                    await self.remote.cmd_updateObservatoryStatus.set_start(
                        status=status,
                    )

            bad_daytime_status = [
                Scheduler.ObservatoryStatus.FAULT | Scheduler.ObservatoryStatus.WEATHER,
                Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DOWNTIME,
                Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.WEATHER
                | Scheduler.ObservatoryStatus.DOWNTIME,
                Scheduler.ObservatoryStatus.WEATHER
                | Scheduler.ObservatoryStatus.DOWNTIME,
            ]

            for status in bad_daytime_status:
                bad_daytime_status_str = " | ".join(
                    [s.name for s in Scheduler.ObservatoryStatus if s & status]
                )

                with salobj.testutils.assertRaisesAckError(
                    result_contains=f"Cannot set status to {bad_daytime_status_str}; daytime flag is active."
                ):
                    await self.remote.cmd_updateObservatoryStatus.set_start(
                        status=status,
                    )

            good_daytime_status = [
                Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.WEATHER
                | Scheduler.ObservatoryStatus.DAYTIME,
                Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DOWNTIME
                | Scheduler.ObservatoryStatus.DAYTIME,
                Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.WEATHER
                | Scheduler.ObservatoryStatus.DOWNTIME
                | Scheduler.ObservatoryStatus.DAYTIME,
                Scheduler.ObservatoryStatus.WEATHER
                | Scheduler.ObservatoryStatus.DOWNTIME
                | Scheduler.ObservatoryStatus.DAYTIME,
                Scheduler.ObservatoryStatus.DAYTIME,
            ]

            for status in good_daytime_status:
                await self.remote.cmd_updateObservatoryStatus.set_start(
                    status=status,
                )
                await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status,
                    flush=False,
                )

                self.csc.model.get_general_info = get_general_info_nighttime

                observatory_status = await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status ^ Scheduler.ObservatoryStatus.DAYTIME,
                    flush=False,
                )
                assert "Nighttime started" in observatory_status.note

                self.csc.model.get_general_info = get_general_info_daytime

                observatory_status = await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status,
                    flush=False,
                )
                assert "Daytime started" in observatory_status.note

            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.FAULT)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DAYTIME,
                flush=False,
            )
            assert "MTMount" in observatory_status.note

            self.csc.model.get_general_info = get_general_info_nighttime

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "Nighttime started" in observatory_status.note

            self.csc.model.get_general_info = get_general_info_daytime

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DAYTIME,
                flush=False,
            )
            assert "Daytime started" in observatory_status.note
            assert "MTMount" in observatory_status.note

            await mtrotator.evt_summaryState.set_write(summaryState=salobj.State.FAULT)
            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DAYTIME,
                flush=False,
            )
            assert "MTMount" in observatory_status.note
            assert "MTRotator" in observatory_status.note

            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.FAULT
                | Scheduler.ObservatoryStatus.DAYTIME,
                flush=False,
            )
            assert "MTMount" not in observatory_status.note
            assert "MTRotator" in observatory_status.note

            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.DAYTIME,
                flush=False,
            )
            assert "MTMount" not in observatory_status.note
            assert "MTRotator" not in observatory_status.note

    @pytest.mark.skipif(
        not supports_observatory_status,
        reason="CSC interface does not support observatory status feature.",
    )
    async def test_observatory_status_daytime_monitoring_csc_disabled(self):
        async with self.make_csc_cleanup_afterward(), ObservatoryStateMock(), self.make_script_queue(
            running=True
        ), salobj.Controller(
            "MTMount"
        ) as mtmount, salobj.Controller(
            "MTRotator"
        ) as mtrotator:
            await mtmount.evt_summaryState.set_write(summaryState=salobj.State.ENABLED)
            await mtrotator.evt_summaryState.set_write(
                summaryState=salobj.State.ENABLED
            )
            await salobj.set_summary_state(
                self.remote,
                salobj.State.DISABLED,
                override="monitor_observatory_state.yaml",
            )

            # patch the model class to ensure calling get_general_info
            # returns that it is daytime
            def get_general_info_daytime():
                return dict(isNight=False)

            def get_general_info_nighttime():
                return dict(isNight=True)

            self.csc.model.get_general_info = get_general_info_daytime

            expected_initial_observatory_status_note = [
                (Scheduler.ObservatoryStatus.UNKNOWN, "Scheduler CSC started"),
                (Scheduler.ObservatoryStatus.UNKNOWN, "Scheduler CSC in STANDBY"),
                (
                    Scheduler.ObservatoryStatus.UNKNOWN,
                    "Observatory status feature enabled",
                ),
                (Scheduler.ObservatoryStatus.DAYTIME, "Daytime started"),
            ]

            for status, note in expected_initial_observatory_status_note:
                observatory_status = await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    status=status,
                    flush=False,
                )
                assert note in observatory_status.note

            with self.assertRaises(asyncio.TimeoutError):
                await self.assert_next_sample(
                    self.remote.evt_observatoryStatus,
                    flush=False,
                )

            self.csc.model.get_general_info = get_general_info_nighttime

            observatory_status = await self.assert_next_sample(
                self.remote.evt_observatoryStatus,
                status=Scheduler.ObservatoryStatus.UNKNOWN,
                flush=False,
            )
            assert "Nighttime started" in observatory_status.note

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

    @contextlib.asynccontextmanager
    async def make_csc_cleanup_afterward(self):
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=SchedulerModes.SIMULATION,
        ):
            yield
            await salobj.set_summary_state(self.remote, salobj.State.STANDBY)


if __name__ == "__main__":
    unittest.main()
