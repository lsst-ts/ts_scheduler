#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_schedulerDriver
----------------------------------

Tests for `schedulerDriver` module.
"""

import unittest

from ts_scheduler.schedulerDriver import Driver

class TestSchedulerDriver(unittest.TestCase):

    def setUp(self):
        self.driver = Driver()

    def test_init(self):

        self.assertEqual(len(self.driver.fields_dict), 5292)
        self.assertEqual(len(self.driver.science_proposal_list), 1)
        self.assertEqual(self.driver.science_proposal_list[0].name, "universal_weak")

    def test_compute_slewtime_bonus(self):

        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(0), 10, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(2), 1.004, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(3), 0.689, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(4), 0.524, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(5), 0.421, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(10), 0.210, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(30), 0.063, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(60), 0.026, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(120), 0.008, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(160), 0.003, delta=1e-3)
        self.assertAlmostEquals(self.driver.compute_slewtime_bonus(200), 0, delta=1e-3)

    def test_startsurvey_startnight(self):

        lsst_start_timestamp = 1640995200.0

        self.assertAlmostEquals(self.driver.time, 0.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, False)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 0.0, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 0.0, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 0)

        time = lsst_start_timestamp
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1640995200.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641086668.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641110981.5, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 0)

        time = 1641086668
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1641086668.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641086668.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641110981.5, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 0)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 0)

        time = 1641086669
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1641086669.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641086668.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641110981.5, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 1519)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 1526595)

        time = 1641100000
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1641100000.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641086668.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641110981.5, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 1519)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 1526595)

        time = 1641110980
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1641110980.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, True)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641086668.8, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641110981.5, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 1519)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 1526595)

        time = 1641110982
        self.driver.update_time(time)
        self.assertAlmostEquals(self.driver.time, 1641110982.0, delta=1e-1)
        self.assertEqual(self.driver.survey_started, True)
        self.assertEqual(self.driver.isnight, False)
        self.assertAlmostEquals(self.driver.sunset_timestamp, 1641173073.1, delta=1e-1)
        self.assertAlmostEquals(self.driver.sunrise_timestamp, 1641197434.8, delta=1e-1)
        self.assertEqual(len(self.driver.science_proposal_list[0].fields_tonight_list), 1519)
        self.assertEqual(self.driver.science_proposal_list[0].total_goal, 1526595)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
