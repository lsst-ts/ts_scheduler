import unittest
import pytest
import asyncio
import salobj
from lsst.ts.scheduler import SchedulerCSC
import SALPY_Scheduler

index_gen = salobj.index_generator()

class Harness:
    def __init__(self, initial_state):
        index = next(index_gen)
        salobj.test_utils.set_random_lsst_dds_domain()
        self.csc = SchedulerCSC(index=index)
        self.remote = salobj.Remote(SALPY_Scheduler, index)

# FIXME: probably need to take care of LSST_DDS_DOMAIN

class TestSchedulerCSC(unittest.TestCase):

    def test_change_state(self):
        harness = Harness()

        # CSC must start in OFFLINE
        assert harness.csc.current_state == salobj.base_csc.State.OFFLINE


        assert m.current_state == "STANDBY"
        assert m.previous_state == "OFFLINE"

        m.current_state = "DISABLED"
        assert m.current_state == "DISABLED"
        assert m.previous_state == "STANDBY"

        with pytest.raises(AttributeError):
            m.previous_state = "ENABLED"

    def test_send_valid_settings(self):
        m = Model()

        m.sal_start()
        assert m.send_valid_settings().find('master') != -1

    def test_init_models(self):
        """This unit test will check that the basic models are initialized by the model.

        Returns
        -------

        """
        models_list = ['location', 'observatory_model', 'observatory_state', 'sky', 'seeing',
                       'scheduled_downtime', 'unscheduled_downtime']  # 'cloud',
        telemetry_list = ['timeHandler', 'observatoryState', 'bulkCloud', 'seeing']

        m = Model()
        m.init_models()

        for model in models_list:
            assert model in m.models
            assert m.models[model] is not None

        for telemetry in telemetry_list:
            assert telemetry in m.raw_telemetry

    def test_configure(self):
        """Test that it is possible to configure model.

        Returns
        -------

        """
        m = Model()

        m.configure('master')

        assert m.current_setting == 'master'
        assert m.driver is not None

        # TODO: One could now check that all the settings available are valid.


if __name__ == '__main__':
    unittest.main()
