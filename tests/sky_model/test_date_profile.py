import unittest

from ts_scheduler.sky_model import DateProfile

from ..test_constants import LSST_SITE, LSST_START_MJD, LSST_START_TIMESTAMP

class DateProfileTest(unittest.TestCase):

    def setUp(self):
        self.dp = DateProfile(LSST_START_TIMESTAMP, LSST_SITE)

    def test_basic_information_after_creation(self):
        self.assertEquals(self.dp.timestamp, LSST_START_TIMESTAMP)
        self.assertIsNotNone(self.dp.location)
        self.assertIsNotNone(self.dp.current_dt)
        self.assertEqual(self.dp.mjd, LSST_START_MJD)
        self.assertEqual(self.dp.lst_rad, 0.5215154816963141)

    def test_update_mechanism(self):
        new_timestamp = LSST_START_TIMESTAMP + 3600.0
        self.dp.update(new_timestamp)
        self.assertEqual(self.dp.timestamp, new_timestamp)
        self.assertEqual(self.dp.mjd, LSST_START_MJD + (1.0 / 24.0))
        self.assertEqual(self.dp.lst_rad, 0.7840316524739084)

    def test_call_mechanism(self):
        new_timestamp = LSST_START_TIMESTAMP + (2.0 * 3600.0)
        (mjd, lst_rad) = self.dp(new_timestamp)
        self.assertEqual(mjd, LSST_START_MJD + (2.0 / 24.0))
        self.assertAlmostEqual(lst_rad, 1.0465478232515026, delta=1E-7)
