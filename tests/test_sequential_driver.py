import types
import logging
import pathlib
import unittest

from lsst.ts.scheduler.driver import SequentialScheduler
from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.kernel import SurveyTopology


class TestSchedulerDriver(unittest.TestCase):

    def setUp(self):
        logging.getLogger().setLevel(logging.WARN)

        self.driver = SequentialScheduler(models={}, raw_telemetry={})

        self.config = types.SimpleNamespace(
            observing_list=pathlib.Path(__file__).parents[1].joinpath(
                "tests",
                "data",
                "test_observing_list.yaml"))

    def test_configure_scheduler(self):

        survey_topology = self.driver.configure_scheduler(self.config)

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props != 0
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

    def test_select_next_target(self):
        self.driver.configure_scheduler(self.config)

        target = self.driver.select_next_target()

        assert isinstance(target, Target)
        assert target.num_exp > 0
        assert len(target.exp_times) == target.num_exp

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
