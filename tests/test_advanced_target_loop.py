# This file is part of ts_scheduler
#
# Developed for the Vera Rubin Observatory Telescope and Site Systems.
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
import glob
import logging
import os
import pathlib
import time
import typing
import unittest

import numpy as np
from lsst.ts import salobj, utils
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.mock import ObservatoryStateMock
from lsst.ts.scheduler.utils import SchedulerModes
from lsst.ts.scheduler.utils.csc_utils import BlockStatus, DetailedState
from lsst.ts.scheduler.utils.error_codes import NO_QUEUE, UPDATE_TELEMETRY_ERROR

try:
    with_scriptqueue = True
    from lsst.ts import scriptqueue
except ModuleNotFoundError:
    with_scriptqueue = False
    pass

logging.basicConfig()

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index
STD_TIMEOUT = 15.0
SCRIPT_TIMEOUT = 30.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


@unittest.skipIf(not with_scriptqueue, "Could not import scriptqueue.")
class AdvancedTargetLoopTestCase(unittest.IsolatedAsyncioTestCase):
    """This unit test is designed to test the interaction of the advanced
    target production loop of the Scheduler CSC with the ScriptQueue.
    """

    def run(self, result: typing.Any) -> None:
        """Override `run` to set a random LSST_DDS_PARTITION_PREFIX
        and set LSST_SITE=test for every test.

        https://stackoverflow.com/a/11180583
        """
        salobj.set_random_lsst_dds_partition_prefix()
        with utils.modify_environ(LSST_SITE="test"):
            super().run(result)

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("AdvancedTargetLoopTestCase")

    async def asyncSetUp(self):
        self.datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        standardpath = os.path.join(self.datadir, "standard")
        externalpath = os.path.join(self.datadir, "external")
        self.queue = scriptqueue.ScriptQueue(
            index=1, standardpath=standardpath, externalpath=externalpath
        )
        self.queue_remote = salobj.Remote(self.queue.domain, "ScriptQueue", index=1)
        self.process = None

        self.scheduler = SchedulerCSC(
            index=1, config_dir=TEST_CONFIG_DIR, simulation_mode=SchedulerModes.MOCKS3
        )

        self.scheduler_remote = salobj.Remote(
            self.scheduler.domain, "Scheduler", index=1
        )

        self.observatory_mock = ObservatoryStateMock()

        self.received_targets = 0
        self.expected_targets = 2

        self.heartbeats = 0
        self.heartbeats_tol = 0.4

        self.target_test_timeout = 120

        await asyncio.gather(
            self.scheduler.start_task,
            self.queue.start_task,
            self.scheduler_remote.start_task,
            self.queue_remote.start_task,
            self.observatory_mock.start_task,
        )

    async def asyncTearDown(self):
        try:
            await salobj.set_summary_state(self.scheduler_remote, salobj.State.STANDBY)
        finally:
            try:
                await asyncio.gather(
                    self.scheduler.close(),
                    self.queue.close(),
                    self.scheduler_remote.close(),
                    self.queue_remote.close(),
                    self.observatory_mock.close(),
                )
            except Exception:
                pass

    async def assert_detailed_state_sequence(self, expected_detailed_states):
        for expected_detailed_state in expected_detailed_states:
            detailed_state = await self.scheduler_remote.evt_detailedState.next(
                flush=False,
                timeout=STD_TIMEOUT,
            )
            with self.subTest(
                expected_detailed_state=expected_detailed_state,
                msg=f"Expected detailed state {expected_detailed_state!r}.",
            ):
                self.log.debug(
                    f"{DetailedState(detailed_state.substate)!r} x {expected_detailed_state!r}"
                )
                assert DetailedState(detailed_state.substate) == expected_detailed_state

    async def assert_next_block_id_status(
        self, block_id: str, block_status_expected: BlockStatus
    ) -> None:
        while True:
            block_status = await self.scheduler_remote.evt_blockStatus.next(
                flush=False, timeout=SCRIPT_TIMEOUT
            )

            self.log.debug(
                f"Got {block_status=}. Expecting {block_id}:{block_status_expected!r}"
            )

            if block_status.id == block_id:
                assert block_status.statusId == block_status_expected
                assert block_status.status == block_status_expected.name
                break

    async def test_fail_enable_if_no_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler will go to a fault state if it is
        enabled and the queue is not enabled.
        """
        # Send Queue to STANDBY
        await salobj.set_summary_state(self.queue_remote, salobj.State.STANDBY)

        # Enable Scheduler
        with self.assertRaisesRegex(
            RuntimeError,
            expected_regex=(
                "Failed to validate observing blocks. "
                "Check CSC traceback for more information."
            ),
        ):
            await salobj.set_summary_state(
                self.scheduler_remote,
                salobj.State.ENABLED,
                override="advance_target_loop_sequential.yaml",
            )

    async def test_no_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler will go to a fault state if it is
        enabled and the queue is not enabled.
        """
        data = await self.scheduler_remote.evt_errorCode.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert data.errorCode == 0

        # Test 1 - Enable scheduler, Queue is not enabled. Scheduler should go
        # to ENABLE and then to FAULT. It may take some time for the scheduler
        # to go to FAULT state.

        # Make sure Queue needs to be in ENABLED before enabling the Scheduler.
        await salobj.set_summary_state(self.queue_remote, salobj.State.ENABLED)

        # Enable Scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential.yaml",
        )

        # Send Queue to STANDBY
        await salobj.set_summary_state(self.queue_remote, salobj.State.STANDBY)

        self.scheduler_remote.evt_detailedState.flush()

        # Resume scheduler operation
        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        # Wait until summary state is FAULT or Timeout
        state = None
        while True:
            try:
                evt_state = await self.scheduler_remote.evt_summaryState.next(
                    flush=False, timeout=STD_TIMEOUT
                )
                state = salobj.State(evt_state.summaryState)
                if state == salobj.State.FAULT:
                    break
            except asyncio.TimeoutError:
                break

        self.assertEqual(
            state, salobj.State.FAULT, f"Scheduler in {state}, expected FAULT. "
        )
        self.assertEqual(
            self.scheduler.summary_state,
            salobj.State.FAULT,
            f"Scheduler in {state}, expected FAULT. ",
        )
        # Check error code
        data = await self.scheduler_remote.evt_errorCode.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert data.errorCode == NO_QUEUE

        expected_detailed_states = (
            DetailedState.RUNNING,
            DetailedState.GENERATING_TARGET_QUEUE,
            DetailedState.RUNNING,
            DetailedState.IDLE,
        )

        await self.assert_detailed_state_sequence(
            expected_detailed_states=expected_detailed_states
        )

        # recover from fault state sending it to STANDBY
        await self.scheduler_remote.cmd_standby.start(timeout=STD_TIMEOUT)

        self.assertEqual(
            self.scheduler.summary_state,
            salobj.State.STANDBY,
            "Scheduler in %s, expected STANDBY. "
            % salobj.State(self.scheduler.summary_state),
        )
        data = await self.scheduler_remote.evt_errorCode.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert data.errorCode == 0

    async def test_fail_efd_query(self):
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # Enable Scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential.yaml",
        )

        self.scheduler.model.telemetry_stream_handler.efd_client.configure_mock(
            **{
                "select_time_series.side_effect": self.mock_fail_select_time_series,
            },
        )

        self.scheduler_remote.evt_errorCode.flush()
        self.scheduler_remote.evt_summaryState.flush()

        self.scheduler_remote.evt_detailedState.flush()

        # Resume scheduler operation
        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        evt_state = await self.scheduler_remote.evt_summaryState.next(
            flush=False, timeout=STD_TIMEOUT
        )
        assert salobj.State(evt_state.summaryState) == salobj.State.FAULT

        error_code = await self.scheduler_remote.evt_errorCode.next(
            flush=False, timeout=STD_TIMEOUT
        )

        assert error_code.errorCode == UPDATE_TELEMETRY_ERROR

        expected_detailed_states = (
            DetailedState.RUNNING,
            DetailedState.GENERATING_TARGET_QUEUE,
            DetailedState.RUNNING,
            DetailedState.IDLE,
        )

        await self.assert_detailed_state_sequence(
            expected_detailed_states=expected_detailed_states
        )

    async def test_abort(self):
        """Test sending the stop command with abort=True.

        Running the stop command with abort=False is already tested in
        test_with_queue.
        """
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        # Resume scheduler operation
        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        # Wait for 1 observation to complete.
        await self.scheduler_remote.evt_observation.next(
            flush=True, timeout=SCRIPT_TIMEOUT
        )

        # Test completed, pausing scheduler
        await self.scheduler_remote.cmd_stop.set_start(timeout=STD_TIMEOUT, abort=True)

        try:
            detailed_state = await self.scheduler_remote.evt_detailedState.next(
                flush=True, timeout=STD_TIMEOUT
            )
        except asyncio.TimeoutError:
            detailed_state = await self.scheduler_remote.evt_detailedState.aget(
                timeout=STD_TIMEOUT
            )

        try:
            queue = await self.queue_remote.evt_queue.next(
                flush=True, timeout=STD_TIMEOUT
            )
        except asyncio.TimeoutError:
            queue = await self.queue_remote.evt_queue.aget(timeout=STD_TIMEOUT)

        assert DetailedState(detailed_state.substate) == DetailedState.IDLE
        assert queue.currentSalIndex == 0
        assert queue.length == 0

    async def test_with_queue(self):
        """Test the target production loop with queue.

        This test makes sure the scheduler is capable of interacting with the
        queue and will produce targets when both are enabled.
        """

        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # ...and try again. This time the scheduler should stay in enabled and
        # publish targets to the queue.

        async def assert_enable(data):
            """Callback function to make sure scheduler is enabled"""
            self.assertEqual(
                data.summaryState,
                salobj.State.ENABLED,
                "Scheduler unexpectedly transitioned from "
                "ENABLED to %s" % salobj.State(data.summaryState),
            )

        async def count_targets(data):
            """Callback to count received targets"""
            self.received_targets += 1

        async def count_heartbeats(data):
            """Callback to count heartbeats"""
            self.heartbeats += 1

        # Subscribing callbacks for the test
        self.scheduler_remote.evt_target.callback = count_targets
        self.scheduler_remote.evt_heartbeat.callback = count_heartbeats

        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        self.scheduler_remote.evt_detailedState.flush()

        # Resume scheduler operation
        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        self.scheduler_remote.evt_summaryState.callback = assert_enable

        # Need to time this test and timeout if it takes too long
        start_time = time.time()
        while self.received_targets < self.expected_targets:
            if time.time() - start_time > self.target_test_timeout:
                break
            await asyncio.sleep(10)

        # Wait for one script to finish executing
        try:
            await self.queue_remote.evt_queue.next(flush=True, timeout=SCRIPT_TIMEOUT)
        except Exception:
            self.log.exception("Timeout waiting for queue state.")

        # Test over, unsubscribe callbacks
        self.scheduler_remote.evt_summaryState.callback = None
        self.scheduler_remote.evt_target.callback = None
        self.scheduler_remote.evt_heartbeat.callback = None
        end_time = time.time()

        # Test completed, pausing scheduler
        await self.scheduler_remote.cmd_stop.start(timeout=STD_TIMEOUT)

        expected_detailed_states = (
            DetailedState.RUNNING,
            DetailedState.GENERATING_TARGET_QUEUE,
            DetailedState.RUNNING,
            DetailedState.QUEUEING_TARGET,
            DetailedState.RUNNING,
            DetailedState.QUEUEING_TARGET,
            DetailedState.RUNNING,
            DetailedState.COMPUTING_PREDICTED_SCHEDULE,
            DetailedState.RUNNING,
        )

        await self.assert_detailed_state_sequence(
            expected_detailed_states=expected_detailed_states
        )

        # Scheduler should be in ENABLED state.
        self.assertEqual(
            self.scheduler.summary_state,
            salobj.State.ENABLED,
            "Scheduler in %s, expected %s"
            % (self.scheduler.summary_state, salobj.State.ENABLED),
        )

        # Must have received at least the expected number of targets
        self.assertGreaterEqual(
            self.received_targets,
            self.expected_targets,
            "Failed target production loop. "
            "Got %i of %i" % (self.received_targets, self.expected_targets),
        )

        # Check that enough heartbeats were sent
        expected_heartbeats = int(
            (end_time - start_time) / salobj.base_csc.HEARTBEAT_INTERVAL
        )
        tolerance_heartbeats = int(np.floor(expected_heartbeats * self.heartbeats_tol))
        self.assertGreaterEqual(
            self.heartbeats,
            expected_heartbeats - tolerance_heartbeats,
            "Scheduler responsiveness compromised. Received %i heartbeats, "
            "expected >%i"
            % (self.heartbeats, expected_heartbeats - tolerance_heartbeats),
        )

        # Check that telemetry stream was queried
        self.scheduler.model.telemetry_stream_handler.efd_client.select_time_series.assert_awaited()
        for (
            telemetry
        ) in self.scheduler.model.telemetry_stream_handler.telemetry_streams:
            self.log.debug(
                f"{telemetry}={self.scheduler.model.raw_telemetry[telemetry]}"
            )
            assert np.isfinite(self.scheduler.model.raw_telemetry[telemetry])

        if hasattr(self.scheduler_remote, "evt_predictedSchedule"):
            # Check predicted Schedule was published
            predicted_schedule = self.scheduler_remote.evt_predictedSchedule.get()

            assert predicted_schedule is not None, "Predicted schedule not published"
            assert (
                predicted_schedule.numberOfTargets > 0
            ), "Number of targets in predicted schedule is zero."

        if hasattr(self.scheduler_remote, "evt_timeToNextTarget"):
            # Check time to next target
            n_time_to_next_target = 0
            while (
                time_to_next_target := self.scheduler_remote.evt_timeToNextTarget.get_oldest()
            ) is not None:
                self.log.debug(f"{n_time_to_next_target}::{time_to_next_target}")
                n_time_to_next_target += 1
                assert time_to_next_target.waitTime > 0, "Wait time in the past"
            assert n_time_to_next_target >= self.received_targets, (
                "Not enough time to next target events published. "
                f"Expected at least {self.received_targets} got {n_time_to_next_target}."
            )

        if hasattr(self.scheduler_remote, "evt_generalInfo"):
            # check generalInfo was published
            general_info = self.scheduler_remote.evt_generalInfo.get()

            assert general_info is not None, "General info was not published"

        observation = self.scheduler_remote.evt_observation.get()

        assert observation is not None, "Observation was not published."

    async def test_add_block_inexistent_block(self) -> None:
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # enable scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        with self.assertRaisesRegex(
            salobj.AckError,
            expected_regex=(
                "Block inexistent-block is not in the list of observing blocks. "
                "Current observing blocks are: "
            ),
        ):
            await self.scheduler_remote.cmd_addBlock.set_start(
                id="inexistent-block",
                timeout=STD_TIMEOUT,
            )

    async def test_add_block_invalid_block(self) -> None:
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # enable scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        with self.assertRaisesRegex(
            salobj.AckError,
            expected_regex=(
                "Block invalid-block is not in the list of valid blocks. "
                "Current valid blocks are: "
            ),
        ):
            await self.scheduler_remote.cmd_addBlock.set_start(
                id="invalid-block",
                timeout=STD_TIMEOUT,
            )

    async def test_add_block_not_running(self) -> None:
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # enable scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        await self.scheduler_remote.cmd_addBlock.set_start(
            id="valid-block",
            timeout=STD_TIMEOUT,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.STARTED,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.EXECUTING,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.COMPLETED,
        )

    async def test_add_block_succeed(self) -> None:
        # enable queue...
        await salobj.set_summary_state(
            self.queue_remote,
            salobj.State.ENABLED,
        )

        # enable scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="advance_target_loop_sequential_std_visit.yaml",
        )

        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        self.scheduler_remote.evt_blockStatus.flush()

        await self.scheduler_remote.cmd_addBlock.set_start(
            id="valid-block",
            timeout=STD_TIMEOUT,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.STARTED,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.EXECUTING,
        )

        await self.assert_next_block_id_status(
            block_id="valid-block",
            block_status_expected=BlockStatus.COMPLETED,
        )

    def tearDown(self):
        for filename in glob.glob("./sequential_*.p"):
            os.remove(filename)

    async def mock_fail_select_time_series(self, *args, **kwargs):
        raise RuntimeError("This is a test.")


if __name__ == "__main__":
    unittest.main()
