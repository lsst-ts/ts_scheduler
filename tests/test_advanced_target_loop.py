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

import os
import glob
import time
import asyncio
import logging
import pathlib
import unittest

import numpy as np

from lsst.ts import salobj

from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.utils import SchedulerModes
from lsst.ts.scheduler.utils.error_codes import NO_QUEUE
from lsst.ts.scheduler.mock import ObservatoryStateMock

try:
    with_scriptqueue = True
    from lsst.ts import scriptqueue
except ModuleNotFoundError:
    with_scriptqueue = False
    pass

logging.basicConfig()

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index
STD_TIMEOUT = 15.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


@unittest.skipIf(not with_scriptqueue, "Could not import scriptqueue.")
class AdvancedTargetLoopTestCase(unittest.IsolatedAsyncioTestCase):
    """This unit test is designed to test the interaction of the advanced
    target production loop of the Scheduler CSC with the ScriptQueue.
    """

    async def asyncSetUp(self):
        salobj.testutils.set_random_lsst_dds_partition_prefix()
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
            await asyncio.gather(
                self.scheduler.close(),
                self.queue.close(),
                self.scheduler_remote.close(),
                self.queue_remote.close(),
                self.observatory_mock.close(),
            )

    async def test_no_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler will go to a fault state if it is
        enabled and the queue is not enabled.
        """

        # Test 1 - Enable scheduler, Queue is not enabled. Scheduler should go
        # to ENABLE and then to FAULT. It may take some time for the scheduler
        # to go to FAULT state.

        # Make sure Queue is in STANDBY
        await salobj.set_summary_state(self.queue_remote, salobj.State.STANDBY)

        # Enable Scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            settingsToApply="advance_target_loop_sequential.yaml",
        )

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
        error_code = await self.scheduler_remote.evt_errorCode.aget(timeout=STD_TIMEOUT)
        self.assertEqual(error_code.errorCode, NO_QUEUE)
        # recover from fault state sending it to STANDBY
        await self.scheduler_remote.cmd_standby.start(timeout=STD_TIMEOUT)

        self.assertEqual(
            self.scheduler.summary_state,
            salobj.State.STANDBY,
            "Scheduler in %s, expected STANDBY. "
            % salobj.State(self.scheduler.summary_state),
        )

    async def test_with_queue(self):
        """Test the simple target production loop.

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

        def assert_enable(data):
            """Callback function to make sure scheduler is enabled"""
            self.assertEqual(
                data.summaryState,
                salobj.State.ENABLED,
                "Scheduler unexpectedly transitioned from "
                "ENABLED to %s" % salobj.State(data.summaryState),
            )

        def count_targets(data):
            """Callback to count received targets"""
            self.received_targets += 1

        def count_heartbeats(data):
            """Callback to count heartbeats"""
            self.heartbeats += 1

        # Subscribing callbacks for the test
        self.scheduler_remote.evt_target.callback = count_targets
        self.scheduler_remote.evt_heartbeat.callback = count_heartbeats

        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            settingsToApply="advance_target_loop_sequential.yaml",
        )

        # Resume scheduler operation
        await self.scheduler_remote.cmd_resume.start(timeout=STD_TIMEOUT)

        self.scheduler_remote.evt_summaryState.callback = assert_enable

        # Need to time this test and timeout if it takes took long
        start_time = time.time()
        while self.received_targets < self.expected_targets:
            if time.time() - start_time > self.target_test_timeout:
                break
            await asyncio.sleep(10)

        # Test over, unsubscribe callbacks
        self.scheduler_remote.evt_summaryState.callback = None
        self.scheduler_remote.evt_target.callback = None
        self.scheduler_remote.evt_heartbeat.callback = None
        end_time = time.time()

        # Test completed, pausing scheduler
        await self.scheduler_remote.cmd_stop.start(timeout=STD_TIMEOUT)

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

    def tearDown(self):
        for filename in glob.glob("./sequential_*.p"):
            os.remove(filename)


if __name__ == "__main__":
    unittest.main()
