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


if __name__ == '__main__':
    unittest.main()
