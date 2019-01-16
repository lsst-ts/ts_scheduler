import sys
import unittest
import time
import pytest
import asyncio
from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
import SALPY_Scheduler

index_gen = salobj.index_generator()

class Harness:
    def __init__(self):
        index = 0  # next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.csc = SchedulerCSC(index=index)
        self.csc.parameters.mode = 'DRY'  # need to set this to allow tests
        self.remote = salobj.Remote(SALPY_Scheduler, index)


class TestSchedulerCSC(unittest.TestCase):

    def setUp(self):
        salobj.set_random_lsst_dds_domain()

    def test_heartbeat(self):
        async def doit():
            harness = Harness()
            start_time = time.time()
            await harness.remote.evt_heartbeat.next(flush=True, timeout=2)  # flush for the first one
            await harness.remote.evt_heartbeat.next(flush=False, timeout=2)  # don't need to flush for the second
            duration = time.time() - start_time
            self.assertLess(abs(duration - 2), 0.5)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_standard_state_transitions(self):
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async def doit():
            harness = Harness()
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
                        id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                        self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                        self.assertNotEqual(id_ack.ack.error, 0)
                        self.assertNotEqual(id_ack.ack.result, "")

            # send start; new state is DISABLED
            cmd_attr = getattr(harness.remote, f"cmd_start")
            state_coro = harness.remote.evt_summaryState.next(flush=True, timeout=1.)
            start_topic = cmd_attr.DataType()
            start_topic.settingsToApply = 'master'  # user master branch on configuration for unit tests.
            id_ack = await cmd_attr.start(start_topic, timeout=120)  # this one takes longer to execute
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # TODO: There are two events issued when starting the scheduler; appliedSettingsMatchStart and
            # settingsApplied. Check that they are received.

            for bad_command in commands:
                if bad_command in ("enable", "standby"):
                    continue  # valid command in DISABLED state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    with self.assertRaises(salobj.AckError):
                        id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                        self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                        self.assertNotEqual(id_ack.ack.error, 0)
                        self.assertNotEqual(id_ack.ack.result, "")

            # send enable; new state is ENABLED
            cmd_attr = getattr(harness.remote, f"cmd_enable")
            state_coro = harness.remote.evt_summaryState.next(flush=True, timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.ENABLED)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            for bad_command in commands:
                if bad_command == "disable":
                    continue  # valid command in ENABLE state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    with self.assertRaises(salobj.AckError):
                        id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                        self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                        self.assertNotEqual(id_ack.ack.error, 0)
                        self.assertNotEqual(id_ack.ack.result, "")

            # send disable; new state is DISABLED
            cmd_attr = getattr(harness.remote, f"cmd_disable")
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)

            # Check that new settings is published afterwards
            settings_coro = harness.remote.evt_settingVersions.next(flush=True, timeout=1)
            # send standby; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_standby")
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            settings = await settings_coro
            self.assertIsNotNone(settings)
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)

            # send exitControl; new state is OFFLINE
            # cmd_attr = getattr(harness.remote, f"cmd_exitControl")
            # id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            # self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            # self.assertEqual(id_ack.ack.error, 0)
            # self.assertEqual(harness.csc.summary_state, salobj.State.OFFLINE)

        asyncio.get_event_loop().run_until_complete(doit())

        # assert m.current_state == "STANDBY"
        # assert m.previous_state == "OFFLINE"
        #
        # m.current_state = "DISABLED"
        # assert m.current_state == "DISABLED"
        # assert m.previous_state == "STANDBY"
        #
        # with pytest.raises(AttributeError):
        #     m.previous_state = "ENABLED"

    # def test_send_valid_settings(self):
    #     m = Model()
    #
    #     m.sal_start()
    #     assert m.send_valid_settings().find('master') != -1
    #
    # def test_init_models(self):
    #     """This unit test will check that the basic models are initialized by the model.
    #
    #     Returns
    #     -------
    #
    #     """
    #     models_list = ['location', 'observatory_model', 'observatory_state', 'sky', 'seeing',
    #                    'scheduled_downtime', 'unscheduled_downtime']  # 'cloud',
    #     telemetry_list = ['timeHandler', 'observatoryState', 'bulkCloud', 'seeing']
    #
    #     m = Model()
    #     m.init_models()
    #
    #     for model in models_list:
    #         assert model in m.models
    #         assert m.models[model] is not None
    #
    #     for telemetry in telemetry_list:
    #         assert telemetry in m.raw_telemetry
    #
    # def test_configure(self):
    #     """Test that it is possible to configure model.
    #
    #     Returns
    #     -------
    #
    #     """
    #     m = Model()
    #
    #     m.configure('master')
    #
    #     assert m.current_setting == 'master'
    #     assert m.driver is not None
    #
    #     # TODO: One could now check that all the settings available are valid.


if __name__ == '__main__':
    unittest.main()
