import numpy
import unittest

from ts_scheduler.sky_model import AstronomicalSkyModel

from ..test_constants import LSST_SITE, LSST_START_TIMESTAMP

class AstronomicalSkyTest(unittest.TestCase):

    def setUp(self):
        self.astro_sky = AstronomicalSkyModel(LSST_SITE)

    def test_basic_information_after_initial_creation(self):
        self.assertIsNotNone(self.astro_sky.date_profile)
        self.assertEqual(self.astro_sky.date_profile.timestamp, 0)
        self.assertIsNotNone(self.astro_sky.sky_brightness)

    def test_update_mechanism(self):
        self.astro_sky.update(LSST_START_TIMESTAMP)
        self.assertEqual(self.astro_sky.date_profile.timestamp, LSST_START_TIMESTAMP)

    def test_sky_brightness_retrieval_internal_time_array_of_positions(self):
        ra_rads = numpy.radians(numpy.linspace(0., 90., 19))
        dec_rads = numpy.radians(numpy.linspace(-90., 0., 19))
        self.astro_sky.update(LSST_START_TIMESTAMP)
        sky_mags = self.astro_sky.get_sky_brightness(ra_rads, dec_rads)
        self.assertEqual(sky_mags.size, ra_rads.size * 6)
