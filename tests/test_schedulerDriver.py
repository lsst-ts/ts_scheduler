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

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
