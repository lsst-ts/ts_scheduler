import unittest
import asynctest
import time
from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC

index_gen = salobj.index_generator()


class Harness:
    def __init__(self):
        index = 0  # next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.csc = SchedulerCSC(index=index)
        self.csc.parameters.mode = 'DRY'  # need to set this to allow tests
        self.remote = salobj.Remote(self.csc.domain, "Scheduler", index=index)

    async def __aenter__(self):
        await self.csc.start_task
        await self.remote.start_task
        return self

    async def __aexit__(self, *args):
        await self.csc.close()


class TestSchedulerCSC(asynctest.TestCase):

    async def setUp(self):
        salobj.set_random_lsst_dds_domain()

    async def test_heartbeat(self):

        async with Harness() as harness:
            start_time = time.time()
            # flush for the first one
            await harness.remote.evt_heartbeat.next(flush=True, timeout=2)
            # don't need to flush for the second
            await harness.remote.evt_heartbeat.next(flush=False, timeout=2)
            duration = time.time() - start_time
            self.assertLess(abs(duration - 2), 1.0)

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

        async with Harness() as harness:
            commands = ("start", "enable", "disable", "exitControl", "standby")

            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)

            # Check that settingVersions was published

            settings = harness.remote.evt_settingVersions.get()
            self.assertIsNotNone(settings, "No settingVersions event published.")

            for bad_command in commands:
                if bad_command in ("start", "exitControl"):
                    continue  # valid command in STANDBY state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    with self.assertRaises(salobj.AckError):
                        id_ack = await cmd_attr.start(timeout=1.)
                        self.assertEqual(id_ack.ack.ack,
                                         salobj.SalRetCode.CMD_FAILED)
                        self.assertNotEqual(id_ack.ack.error, 0)
                        self.assertNotEqual(id_ack.ack.result, "")

            # send start; new state is DISABLED
            harness.remote.evt_summaryState.flush()

            # this one takes longer to execute
            id_ack = await harness.remote.cmd_start.set_start(settingsToApply='master',
                                                              timeout=120)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=10.)

            self.assertEqual(id_ack.ack, salobj.SalRetCode.CMD_COMPLETE)
            self.assertEqual(id_ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # TODO: There are two events issued when starting the scheduler;
            # appliedSettingsMatchStart and
            # settingsApplied. Check that they are received.

            for bad_command in commands:
                if bad_command in ("enable", "standby"):
                    continue  # valid command in DISABLED state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    with self.assertRaises(salobj.AckError):
                        id_ack = await cmd_attr.start(timeout=1.)
                        self.assertEqual(id_ack.ack,
                                         salobj.SalRetCode.CMD_COMPLETE)
                        self.assertNotEqual(id_ack.error, 0)
                        self.assertNotEqual(id_ack.result, "")

            # send enable; new state is ENABLED
            harness.remote.evt_summaryState.flush()

            id_ack = await harness.remote.cmd_enable.start(timeout=1.)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1.)

            self.assertEqual(id_ack.ack, salobj.SalRetCode.CMD_COMPLETE)
            self.assertEqual(id_ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.ENABLED)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            for bad_command in commands:
                if bad_command == "disable":
                    continue  # valid command in ENABLE state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    with self.assertRaises(salobj.AckError):
                        id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                        self.assertEqual(id_ack.ack.ack,
                                         salobj.SalRetCode.CMD_FAILED)
                        self.assertNotEqual(id_ack.ack.error, 0)
                        self.assertNotEqual(id_ack.ack.result, "")

            # send disable; new state is DISABLED
            harness.remote.evt_summaryState.flush()

            id_ack = await harness.remote.cmd_disable.start(timeout=1.)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1.)
            self.assertEqual(id_ack.ack, salobj.SalRetCode.CMD_COMPLETE)
            self.assertEqual(id_ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # Check that new settings is published afterwards
            harness.remote.evt_settingVersions.flush()

            # send standby; new state is STANDBY

            id_ack = await harness.remote.cmd_standby.start(timeout=1.)
            settings = await harness.remote.evt_settingVersions.next(flush=False, timeout=1)
            self.assertIsNotNone(settings)
            self.assertEqual(id_ack.ack, salobj.SalRetCode.CMD_COMPLETE)
            self.assertEqual(id_ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)


if __name__ == '__main__':
    unittest.main()
