
import asyncio
import os
import unittest
import time
import asynctest
import numpy as np

import lsst.ts.salobj as salobj
from lsst.ts.scheduler import SchedulerCSC
with_scriptqueue = False

try:
    with_scriptqueue = True
    from lsst.ts import scriptqueue
except ModuleNotFoundError:
    with_scriptqueue = False
    pass

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index
STD_TIMEOUT = 15.


@unittest.skipIf(not with_scriptqueue, "Could not import scriptqueue.")
class SimpleTargetLoopTestCase(asynctest.TestCase):
    """This unit test is designed to test the interaction of the simple target
    production loop of the Scheduler CSC with the LSST Queue.

    """

    async def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()
        self.datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        standardpath = os.path.join(self.datadir, "standard")
        externalpath = os.path.join(self.datadir, "external")
        self.queue = scriptqueue.ScriptQueue(index=1,
                                             standardpath=standardpath,
                                             externalpath=externalpath)
        self.queue.summary_state = salobj.State.DISABLED
        self.queue_remote = salobj.Remote(self.queue.domain, "ScriptQueue", index=1)
        self.process = None

        self.scheduler = SchedulerCSC(index=1)
        self.scheduler.parameters.mode = 'SIMPLE'
        self.scheduler_remote = salobj.Remote(self.scheduler.domain, "Scheduler", index=1)
        self.received_targets = 0
        self.expected_targets = 2

        self.heartbeats = 0
        self.heartbeats_tol = 0.4

        self.target_test_timeout = 120

        await asyncio.gather(self.scheduler.start_task,
                             self.queue.start_task,
                             self.scheduler_remote.start_task,
                             self.queue_remote.start_task)

    async def tearDown(self):
        await asyncio.gather(self.scheduler.close(),
                             self.queue.close(),
                             self.scheduler_remote.close(),
                             self.queue_remote.close())

    async def test_simple_loop_no_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler will go to a fault state if it is
        enabled and the queue is not enabled.
        """

        # Test 1 - Enable scheduler, Queue is not enable. Scheduler should go
        # to ENABLE and then to FAULT It may take some time for the scheduler
        # to go to FAULT state.

        # Make sure Queue is in STANDBY
        await salobj.set_summary_state(self.queue_remote,
                                       salobj.State.STANDBY)

        # Enable Scheduler
        await salobj.set_summary_state(self.scheduler_remote,
                                       salobj.State.ENABLED,
                                       settingsToApply='master')

        self.assertEqual(self.scheduler.summary_state, salobj.State.ENABLED,
                         "Scheduler in %s, expected ENABLED. " % salobj.State(
                             self.scheduler.summary_state))

        self.scheduler_remote.evt_summaryState.flush()
        state = await self.scheduler_remote.evt_summaryState.next(flush=False, timeout=STD_TIMEOUT)

        if state.summaryState == salobj.State.ENABLED:
            state = await self.scheduler_remote.evt_summaryState.next(flush=False,
                                                                      timeout=STD_TIMEOUT*2.)

        self.assertEqual(state.summaryState, salobj.State.FAULT,
                         "Scheduler in %s, expected FAULT. " % salobj.State(state.summaryState))
        self.assertEqual(self.scheduler.summary_state, salobj.State.FAULT,
                         "Scheduler in %s, expected FAULT. " % salobj.State(state.summaryState))

        # recover from fault state sending it to STANDBY
        await self.scheduler_remote.cmd_standby.start(timeout=STD_TIMEOUT)

        self.assertEqual(self.scheduler.summary_state, salobj.State.STANDBY,
                         "Scheduler in %s, expected STANDBY. " % salobj.State(
                             self.scheduler.summary_state))

    async def test_simple_loop_with_queue(self):
        """Test the simple target production loop.

        This test makes sure the scheduler is capable of interacting with the
        queue and will produce targets when both are enabled.
        """

        # enable queue...
        await salobj.set_summary_state(self.queue_remote,
                                       salobj.State.ENABLED)

        # ...and try again. This time the scheduler should stay in enable and
        # publish targets to the queue.

        def assertEnable(data):
            """Callback function to make sure scheduler is enabled"""
            self.assertEqual(data.summaryState, salobj.State.ENABLED,
                             "Scheduler unexpectedly transitioned from "
                             "ENABLE to %s" % salobj.State(data.summaryState))

        def count_targets(data):
            """Callback to count received targets"""
            self.received_targets += 1

        def count_heartbeats(data):
            """Callback to count heartbeats"""
            self.heartbeats += 1

        # Subscribing callbacks for the test
        self.scheduler_remote.evt_target.callback = count_targets
        self.scheduler_remote.evt_heartbeat.callback = count_heartbeats

        await salobj.set_summary_state(self.scheduler_remote,
                                       salobj.State.ENABLED,
                                       settingsToApply='master')

        self.scheduler_remote.evt_summaryState.callback = assertEnable

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

        # Test completed, disabling scheduler
        await self.scheduler_remote.cmd_disable.start()

        # Scheduler should be in DISABLED state.
        self.assertEqual(self.scheduler.summary_state, salobj.State.DISABLED,
                         'Scheduler in %s, expected %s' % (self.scheduler.summary_state,
                                                           salobj.State.DISABLED))

        # Must have received at least the expected number of targets
        self.assertGreaterEqual(self.received_targets, self.expected_targets,
                                'Failed target production loop. '
                                'Got %i of %i' % (self.received_targets,
                                                  self.expected_targets))

        expected_heartbeats = int((end_time - start_time)/salobj.base_csc.HEARTBEAT_INTERVAL)
        tolerance_heartbeats = int(np.floor(expected_heartbeats*self.heartbeats_tol))
        self.assertGreaterEqual(self.heartbeats, expected_heartbeats-tolerance_heartbeats,
                                'Scheduler responsiveness compromised. Received %i heartbeats, '
                                'expected >%i' % (self.heartbeats,
                                                  expected_heartbeats-tolerance_heartbeats))


if __name__ == "__main__":
    unittest.main()
