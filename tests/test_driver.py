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
import logging
import unittest
import pathlib

from lsst.ts.scheduler.driver import Driver, SurveyTopology
from lsst.ts.observatory.model import Target

logging.basicConfig()


class TestSchedulerDriver(unittest.TestCase):
    def setUp(self):
        self.driver = Driver(models={}, raw_telemetry={})

    def test_configure_scheduler(self):
        config = types.SimpleNamespace(
            driver_configuration=dict(
                general_propos=["Test"],
                default_observing_script_name="standard_visit.py",
                default_observing_script_is_standard=True,
            )
        )
        survey_topology = self.driver.configure_scheduler(config)

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props == 1
        assert survey_topology.general_propos[0] == "Test"
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

        self.assertEqual(
            self.driver.default_observing_script_name,
            config.driver_configuration["default_observing_script_name"],
        )
        self.assertEqual(
            self.driver.default_observing_script_is_standard,
            config.driver_configuration["default_observing_script_is_standard"],
        )

    def test_select_next_target(self):
        target = self.driver.select_next_target()

        assert isinstance(target, Target)
        assert target.num_exp > 0
        assert len(target.exp_times) == target.num_exp

    def test_load(self):
        config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "test_observing_list.yaml")
        )

        bad_config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "bad_config.yaml")
        )

        self.driver.load(config)

        with self.assertRaises(RuntimeError):
            self.driver.load(bad_config)

    @unittest.skip("Cannot run this as-is: needs updating")
    def test_init(self):

        self.assertEqual(len(self.driver.fields_dict), 5292)
        self.assertEqual(len(self.driver.science_proposal_list), 1)
        self.assertEqual(self.driver.science_proposal_list[0].name, "weak_lensing")

    @unittest.skip("Cannot run this as-is: needs updating")
    def test_compute_slewtime_cost(self):

        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(0), -0.034, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(2), -0.020, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(3), -0.014, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(4), -0.007, delta=1e-3
        )
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(5), 0.000, delta=1e-3)
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(10), 0.034, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(30), 0.171, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(60), 0.377, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(120), 0.791, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(150), 1.000, delta=1e-3
        )
        self.assertAlmostEquals(
            self.driver.compute_slewtime_cost(200), 1.350, delta=1e-3
        )

    @unittest.skip("Cannot run this as-is: needs updating")
    def test_startsurvey_startnight(self):

        lsst_start_timestamp = 1640995200.0

        self.assertAlmostEquals(self.driver.time, 0.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, False)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 0.0, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 0.0, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 0
        )
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = lsst_start_timestamp
        night = 1
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1640995200.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 0
        )
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = 1640998122
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1640998122.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 0
        )
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = 1641000000
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641000000.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 1515
        )
        self.assertEqual(
            self.driver.science_proposal_list[0].survey_targets_goal, 1522575
        )

        time = 1641010980
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641010980.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 1515
        )
        self.assertEqual(
            self.driver.science_proposal_list[0].survey_targets_goal, 1522575
        )

        time = 1641086669
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641086669.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641084532.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641113113.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 1515
        )
        self.assertEqual(
            self.driver.science_proposal_list[0].survey_targets_goal, 1522575
        )

        time = 1641114000
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641114000.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641084532.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641113113.8, delta=1e-1)
        self.assertEqual(
            len(self.driver.science_proposal_list[0].tonight_fields_list), 1519
        )
        self.assertEqual(
            self.driver.science_proposal_list[0].survey_targets_goal, 1537650
        )

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
