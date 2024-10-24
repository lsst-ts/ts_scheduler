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
from lsst.ts.scheduler.utils.error_codes import NO_QUEUE

with_scriptqueue = False

try:
    with_scriptqueue = True
    from lsst.ts import scriptqueue
except ModuleNotFoundError:
    with_scriptqueue = False
    pass

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index
STD_TIMEOUT = 15.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


@unittest.skipIf(not with_scriptqueue, "Could not import scriptqueue.")
class SimpleTargetLoopTestCase(unittest.IsolatedAsyncioTestCase):
    """This unit test is designed to test the interaction of the simple target
    production loop of the Scheduler CSC with the LSST Queue.

    """

    def run(self, result: typing.Any) -> None:
        """Override `run` to set a random LSST_DDS_PARTITION_PREFIX
        and set LSST_SITE=test for every test.

        https://stackoverflow.com/a/11180583
        """
        salobj.set_random_lsst_dds_partition_prefix()
        with utils.modify_environ(LSST_SITE="test"):
            super().run(result)

    async def asyncSetUp(self):
        self.log = logging.getLogger(__name__)
        self.datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        standardpath = os.path.join(self.datadir, "standard")
        externalpath = os.path.join(self.datadir, "external")
        self._test_start_time = utils.current_tai()

        self.queue = scriptqueue.ScriptQueue(
            index=1, standardpath=standardpath, externalpath=externalpath
        )
        self.queue_remote = salobj.Remote(self.queue.domain, "ScriptQueue", index=1)
        self.process = None

        self.scheduler = SchedulerCSC(index=1, config_dir=TEST_CONFIG_DIR)
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

    async def next_sample(self, topic_reader, timeout=STD_TIMEOUT):
        sample = await topic_reader.next(flush=False, timeout=timeout)
        while sample.private_sndStamp < self._test_start_time:
            self.log.debug(f"Discarding old sample: {sample}.")
            sample = await topic_reader.next(flush=False, timeout=timeout)
        return sample

    async def test_no_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler will go to a fault state if it is
        enabled and the queue is not enabled.
        """
        data = await self.next_sample(self.scheduler_remote.evt_errorCode)
        assert data.errorCode == 0

        data = await self.next_sample(self.queue_remote.evt_summaryState)
        assert data.summaryState == salobj.State.STANDBY

        data = await self.next_sample(self.scheduler_remote.evt_summaryState)
        assert data.summaryState == salobj.State.STANDBY
        # Test 1 - Enable scheduler, with Queue enabled, then put queue in
        # standby. Scheduler should go to ENABLE and then to FAULT It may take
        # some time for the scheduler to go to FAULT state.

        # Make sure Queue is in ENABLED so we can enable the scheduler
        await salobj.set_summary_state(self.queue_remote, salobj.State.ENABLED)

        # Enable Scheduler
        await salobj.set_summary_state(
            self.scheduler_remote,
            salobj.State.ENABLED,
            override="simple_target_loop_sequential.yaml",
        )

        # Make sure Queue is in STANDBY
        await salobj.set_summary_state(self.queue_remote, salobj.State.STANDBY)

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
        await salobj.set_summary_state(self.queue_remote, salobj.State.ENABLED)

        # ...and try again. This time the scheduler should stay in enable and
        # publish targets to the queue.

        def assert_enable(data):
            """Callback function to make sure scheduler is enabled"""
            self.assertEqual(
                data.summaryState,
                salobj.State.ENABLED,
                "Scheduler unexpectedly transitioned from "
                "ENABLE to %s" % salobj.State(data.summaryState),
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
            override="simple_target_loop_sequential.yaml",
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


if __name__ == "__main__":
    unittest.main()
