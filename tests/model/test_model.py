# import logging
# import os
import unittest

from lsst.ts.scheduler import Model

class TestSchedulerModel(unittest.TestCase):

    def test_initialize_with_default(self):
        m = Model()
        assert m.get_current_state() == "OFFLINE"
        assert m.get_previous_state() == "OFFLINE"
        assert m.get_configuration_path() != None
        assert m.get_valid_settings() != None

    def test_change_state(self):

        m = Model()
        m.change_state("STANDBY")
        assert m.get_current_state() == "STANDBY"
        assert m.get_previous_state() == "OFFLINE"

        m.change_state("DISABLED")
        assert m.get_current_state() == "DISABLED"
        assert m.get_previous_state() == "STANDBY"



if __name__ == '__main__':
    unittest.main()