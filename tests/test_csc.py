import sys
import unittest
import time
import pytest
import asyncio
import salobj
from lsst.ts.scheduler import SchedulerCSC
import SALPY_Scheduler

index_gen = salobj.index_generator()

class Harness:
    def __init__(self):
        index = 0  # next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.csc = SchedulerCSC(index=index)
        self.remote = salobj.Remote(SALPY_Scheduler, index)

# FIXME: probably need to take care of LSST_DDS_DOMAIN

class TestSchedulerCSC(unittest.TestCase):

    def test_heartbeat(self):
        async def doit():
            harness = Harness()
            start_time = time.time()
            await harness.remote.evt_heartbeat.next(timeout=2)
            await harness.remote.evt_heartbeat.next(timeout=2)
            duration = time.time() - start_time
            self.assertLess(abs(duration - 2), 0.5)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_standard_state_transitions(self):
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * enterControl: OFFLINE to STANDBY
        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async def doit():
            harness = Harness()
            commands = ("enterControl", "start", "enable", "disable", "exitControl", "standby")

            self.assertEqual(harness.csc.summary_state, salobj.State.OFFLINE)

            for bad_command in commands:
                if bad_command == "enterControl":
                    continue  # valid command in OFFLINE state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                    self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                    self.assertNotEqual(id_ack.ack.error, 0)
                    self.assertNotEqual(id_ack.ack.result, "")

            # send enterControl; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_enterControl")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)

            for bad_command in commands:
                if bad_command in ("start", "exitControl"):
                    continue  # valid command in STANDBY state
                with self.subTest(bad_command=bad_command):
                    cmd_attr = getattr(harness.remote, f"cmd_{bad_command}")
                    id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                    self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                    self.assertNotEqual(id_ack.ack.error, 0)
                    self.assertNotEqual(id_ack.ack.result, "")

            # send start; new state is DISABLED
            cmd_attr = getattr(harness.remote, f"cmd_start")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
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
                    id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
                    self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_FAILED)
                    self.assertNotEqual(id_ack.ack.error, 0)
                    self.assertNotEqual(id_ack.ack.result, "")

            # send enable; new state is ENABLED
            cmd_attr = getattr(harness.remote, f"cmd_enable")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
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

            # send standby; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_standby")
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
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

    def test_every_fault_transition(self):
        """Test standard CSC Fault transitions.
         Returns
        -------
        The initial state is STANDBY.
        The standard commands and associated state transitions are:
         * enterControl: OFFLINE to STANDBY
        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED
         * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """
        
        async def doit():
            harness = Harness()
            self.assertEqual(harness.csc.summary_state, salobj.State.OFFLINE)

            # send enterControl; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_enterControl")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)
            # set to FAULT; new state is FAULT
            harness.csc._summary_state = salobj.State.FAULT
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            harness.csc.report_summary_state()
            state = await state_coro
            self.assertEqual(harness.csc.summary_state, salobj.State.FAULT)
            self.assertEqual(state.summaryState, salobj.State.FAULT)


            # send standby; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_standby")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)
            # send start; new state is DISABLED 
            cmd_attr = getattr(harness.remote, f"cmd_start")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)
            # set to FAULT; new state is FAULT
            harness.csc._summary_state = salobj.State.FAULT
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            harness.csc.report_summary_state()
            state = await state_coro
            self.assertEqual(harness.csc.summary_state, salobj.State.FAULT)
            self.assertEqual(state.summaryState, salobj.State.FAULT)
            

            # send standby; new state is STANDBY
            cmd_attr = getattr(harness.remote, f"cmd_standby")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)
            # send start; new state is DISABLED 
            cmd_attr = getattr(harness.remote, f"cmd_start")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)
            # send enable; new state is ENABLED 
            cmd_attr = getattr(harness.remote, f"cmd_enable")
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            state = await state_coro
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.ENABLED)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)
            # set to FAULT; new state is FAULT
            harness.csc._summary_state = salobj.State.FAULT
            state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            harness.csc.report_summary_state()
            state = await state_coro
            self.assertEqual(harness.csc.summary_state, salobj.State.FAULT)
            self.assertEqual(state.summaryState, salobj.State.FAULT)
         
        asyncio.get_event_loop().run_until_complete(doit())


    def test_heartbeat_count(self):
        """Count the number of hearbeats for 5s of enabled SchedulerCSC.
        """
        self.count = 0
    
        def count_heartbeats(self, evt_data):
            self.count += 1


        async def doit():
            harness = Harness()
            
            harness.remote.evt_heartbeat.callback = self.count_heartbeats()

            # cmd_attr = getattr(harness.remote, f"cmd_enterControl")
            # state_coro = harness.remote.evt_summaryState.next(timeout=1.)
            # id_ack = await cmd_attr.start(cmd_attr.DataType(), timeout=1.)
            # state = await state_coro
        

         
        asyncio.get_event_loop().run_until_complete(doit())

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
