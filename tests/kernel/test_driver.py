#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_schedulerDriver
----------------------------------

Tests for `schedulerDriver` module.
"""
import logging
import os
import unittest

from ts_scheduler.schedulerDefinitions import conf_file_path, read_conf_file
from ts_scheduler.schedulerDriver import Driver

class TestSchedulerDriver(unittest.TestCase):

    def setUp(self):
        logging.getLogger().setLevel(logging.WARN)
        conf_path = conf_file_path(__name__, "conf")
        self.driver = Driver()

        driver_conf_file = os.path.join(conf_path, "scheduler", "driver.conf")
        obs_site_conf_file = os.path.join(conf_path, "system", "site.conf")
        obs_model_conf_file = os.path.join(conf_path, "system", "observatory_model.conf")
        survey_conf_file = os.path.join(conf_path, "survey", "test_survey.conf")

        driver_confdict = read_conf_file(driver_conf_file)
        obs_site_confdict = read_conf_file(obs_site_conf_file)
        obs_model_confdict = read_conf_file(obs_model_conf_file)

        self.driver.configure(driver_confdict)
        self.driver.configure_location(obs_site_confdict)
        self.driver.configure_observatory(obs_model_confdict)

        self.driver.configure_survey(survey_conf_file)

    def test_init(self):

        self.assertEqual(len(self.driver.fields_dict), 5292)
        self.assertEqual(len(self.driver.science_proposal_list), 1)
        self.assertEqual(self.driver.science_proposal_list[0].name, "weak_lensing")

    def test_compute_slewtime_cost(self):

        self.assertAlmostEquals(self.driver.compute_slewtime_cost(0), 0.000, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(2), 0.013, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(3), 0.020, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(4), 0.026, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(5), 0.033, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(10), 0.066, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(30), 0.198, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(60), 0.398, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(120), 0.798, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(150), 1.000, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_cost(200), 1.338, delta=1e-3)

    def test_startsurvey_startnight(self):

        lsst_start_timestamp = 1640995200.0

        self.assertAlmostEquals(self.driver.time, 0.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, False)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 0.0, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 0.0, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = lsst_start_timestamp
        night = 1
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1640995200.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = 1640998122
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1640998122.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 0)

        time = 1641000000
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641000000.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 1515)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 1522575)

        time = 1641010980
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641010980.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1640998122.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641026665.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 1515)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 1522575)

        time = 1641086669
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641086669.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641084532.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641113113.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 1515)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 1522575)

        time = 1641114000
        self.driver.update_time(time, night)
        self.assertAlmostEquals(self.driver.time, 1641114000.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641084532.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641113113.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].tonight_fields_list), 1519)
        self.assertEqual(self.driver.science_proposal_list[0].survey_targets_goal, 1537650)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
