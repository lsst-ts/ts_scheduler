import unittest
import pytest

from lsst.ts.scheduler import Model

class TestSchedulerModel(unittest.TestCase):

    def test_init(self):
        m = Model()
        
        assert m.current_state == "OFFLINE"
        assert m.previous_state == "OFFLINE"
        assert m.configuration_path != None
        assert m.valid_settings != None

    def test_change_state(self):
        m = Model()
        
        m.current_state = "STANDBY"
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
        """
        This unit test will check that the basic models are initialized by the model.

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


if __name__ == '__main__':
    unittest.main()
