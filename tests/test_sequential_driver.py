# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

import types
import pathlib
import unittest
import logging

from lsst.ts.salobj import current_tai

from lsst.ts.scheduler.driver import SequentialScheduler, SurveyTopology
from lsst.ts.observatory.model import Target
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState

from lsst.ts.dateloc import ObservatoryLocation

logging.basicConfig()


class TestSchedulerDriver(unittest.TestCase):
    def setUp(self):

        self.location = ObservatoryLocation()
        self.location.for_lsst()

        self.model = ObservatoryModel(self.location)
        self.model.configure_from_module()

        self.model.update_state(current_tai())

        self.state = ObservatoryState()
        self.state.set(self.model.current_state)

        self.driver = SequentialScheduler(
            models={"observatory_model": self.model, "observatory_state": self.state},
            raw_telemetry={},
        )

        self.config = types.SimpleNamespace(
            observing_list=pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "test_observing_list.yaml")
        )

    def test_configure_scheduler(self):

        survey_topology = self.driver.configure_scheduler(self.config)

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props != 0
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

    def test_select_next_target(self):
        self.driver.configure_scheduler(self.config)

        n_targets = 0

        while True:

            with self.subTest(msg="Request target {n_targets}."):

                target = self.driver.select_next_target()

                if target is None:
                    break
                else:
                    self.assertIsInstance(target, Target)
                    self.assertGreater(target.num_exp, 0)
                    self.assertEqual(len(target.exp_times), target.num_exp)
                    self.assertGreater(target.slewtime, 0.0)
                    n_targets += 1
                self.model.observe(target)
                self.state.set(self.model.current_state)

        self.assertGreater(n_targets, 0)

    def test_load(self):

        config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "test_observing_list.yaml")
        )

        self.driver.load(config)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
