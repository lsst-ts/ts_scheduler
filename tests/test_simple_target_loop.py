
import asyncio
import os
import unittest
import time
import warnings
import numpy as np

import SALPY_ScriptQueue
import SALPY_Scheduler
import lsst.ts.salobj as salobj
from lsst.ts import scriptqueue
from lsst.ts.scheduler import SchedulerCSC

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index


class SimpleTargetLoopTestCase(unittest.TestCase):
    """This unit test is designed to test the interaction of the simple target production loop of the Scheduler CSC
    with the LSST Queue.

    """
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()
        self.datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        standardpath = os.path.join(self.datadir, "standard")
        externalpath = os.path.join(self.datadir, "external")
        self.queue = scriptqueue.ScriptQueue(index=1,
                                             standardpath=standardpath,
                                             externalpath=externalpath)
        self.queue.summary_state = salobj.State.DISABLED
        self.queue_remote = salobj.Remote(SALPY_ScriptQueue, index=1)
        self.process = None

        self.scheduler = SchedulerCSC(index=1)
        self.scheduler.parameters.mode = 'SIMPLE'
        self.scheduler_remote = salobj.Remote(SALPY_Scheduler, index=1)
        self.received_targets = 0
        self.expected_targets = 2

        self.heartbeats = 0
        self.heartbeats_tol = 0.4

        self.target_test_timeout = 120

    async def enable_scheduler(self):
        """ Utility method to enable the scheduler CSC. """

        # send enterControl; new state is STANDBY
        state_coro = self.scheduler_remote.evt_summaryState.next(timeout=1.)
        cmd_attr = getattr(self.scheduler_remote, f"cmd_enterControl")
        await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
        state = await state_coro
        self.assertEqual(state.summaryState, salobj.State.STANDBY,
                         "Scheduler in %s, expected STANDBY. " % salobj.State(state.summaryState))

        # send start; new state is DISABLED
        state_coro = self.scheduler_remote.evt_summaryState.next(timeout=1.)
        cmd_attr = getattr(self.scheduler_remote, f"cmd_start")
        start_topic = cmd_attr.DataType()
        start_topic.settingsToApply = 'master'  # use master branch on configuration for unit tests.
        await cmd_attr.start(start_topic, timeout=120)  # this one takes longer to execute
        state = await state_coro
        self.assertEqual(state.summaryState, salobj.State.DISABLED,
                         "Scheduler in %s, expected DISABLE. " % salobj.State(state.summaryState))

        # send enable; new state is ENABLED
        state_coro = self.scheduler_remote.evt_summaryState.next(timeout=1.)
        cmd_attr = getattr(self.scheduler_remote, f"cmd_enable")
        await cmd_attr.start(cmd_attr.DataType(), timeout=1.)

        self.assertEqual(self.scheduler.summary_state, salobj.State.ENABLED)

        state = await state_coro
        self.assertEqual(state.summaryState, salobj.State.ENABLED,
                         "Scheduler in %s, expected ENABLED. " % salobj.State(state.summaryState))

    async def enable_queue(self):
        """ Utility method to enable the Queue. """
        # send enable; new state is ENABLED
        cmd_attr = getattr(self.queue_remote, f"cmd_enable")
        await cmd_attr.start(cmd_attr.DataType(), timeout=1.)

        self.assertEqual(self.queue.summary_state, salobj.State.ENABLED)

    def test_simple_loop(self):
        """Test the simple target production loop."""

        async def doit():

            # Test 1 - Enable scheduler Queue is not enable. Scheduler should go to ENABLE and then to FAULT
            # It may take some time for the scheduler to go to FAULT state.

            state_coro = self.scheduler_remote.evt_summaryState.next(timeout=1.)
            await self.enable_scheduler()

            self.assertEqual(self.scheduler.summary_state, salobj.State.ENABLED,
                             "Scheduler in %s, expected ENABLED. " % salobj.State(self.scheduler.summary_state))
            # I won't check for self.scheduler.summary_state here because the scheduler can transition to Fault
            # in the meantime

            state = await state_coro
            self.assertEqual(state.summaryState, salobj.State.FAULT,
                             "Scheduler in %s, expected FAULT. " % salobj.State(state.summaryState))
            self.assertEqual(self.scheduler.summary_state, salobj.State.FAULT,
                             "Scheduler in %s, expected FAULT. " % salobj.State(state.summaryState))

            # recover from fault state sending it to OFFLINE
            cmd_attr = getattr(self.scheduler_remote, f"cmd_exitControl")
            await cmd_attr.start(cmd_attr.DataType(), timeout=1.)

            self.assertEqual(self.scheduler.summary_state, salobj.State.OFFLINE,
                             "Scheduler in %s, expected OFFLINE. " % salobj.State(self.scheduler.summary_state))

            # now enable queue...
            await self.enable_queue()

            # ...and try again. This time the scheduler should stay in enable and publish targets to the queue.

            def assertEnable(data):
                """Callback function to make sure scheduler is enabled"""
                self.assertEqual(data.summaryState, salobj.State.ENABLED,
                                 "Scheduler unexpectedly transitioned from "
                                 "ENABLE to %s" % salobj.State(data.summaryState))

            # I will wait for the scheduler to publish 2 targets and then I will disable it
            def count_targets(data):
                """Callback to count received targets"""
                self.received_targets += 1

            def count_heartbeats(data):
                """Callback to count heartbeats"""
                self.heartbeats += 1

            # Subscribing callbacks for the test
            self.scheduler_remote.evt_target.callback = count_targets
            self.scheduler_remote.evt_heartbeat.callback = count_heartbeats

            await self.enable_scheduler()

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
            cmd_attr = getattr(self.scheduler_remote, f"cmd_disable")
            await cmd_attr.start(cmd_attr.DataType())

            # Scheduler should be in OFFLINE state.
            self.assertEqual(self.scheduler.summary_state, salobj.State.DISABLED,
                             'Scheduler in %s, expected %s' % (self.scheduler.summary_state,
                                                               salobj.State.DISABLED))

            # Must have received at least the expected number of targets
            self.assertGreaterEqual(self.received_targets, self.expected_targets,
                                    'Failed target production loop. Got %i of %i' % (self.received_targets,
                                                                                     self.expected_targets))

            expected_heartbeats = int((end_time - start_time)/salobj.base_csc.HEARTBEAT_INTERVAL)
            tolerance_heartbeats = int(np.floor(expected_heartbeats*self.heartbeats_tol))
            self.assertGreaterEqual(self.heartbeats, expected_heartbeats-tolerance_heartbeats,
                                    'Scheduler responsiveness compromised. Received %i heartbeats, '
                                    'expected >%i' % (self.heartbeats,
                                                      expected_heartbeats-tolerance_heartbeats))

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == "__main__":
    unittest.main()
