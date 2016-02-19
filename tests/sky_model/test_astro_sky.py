import numpy
import unittest

from ts_scheduler.sky_model import AstronomicalSkyModel

from ..test_constants import LSST_NUM_FILTERS, LSST_SITE, LSST_START_TIMESTAMP

class AstronomicalSkyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.astro_sky = AstronomicalSkyModel(LSST_SITE)

    def create_ra_dec(self):
        self.ra_rads = numpy.radians(numpy.linspace(0., 90., 19))
        self.dec_rads = numpy.radians(numpy.linspace(-90., 0., 19))

    def test_basic_information_after_initial_creation(self):
        self.assertIsNotNone(self.astro_sky.date_profile)
        self.assertEqual(self.astro_sky.date_profile.timestamp, 0)
        self.assertIsNotNone(self.astro_sky.sky_brightness)

    def test_update_mechanism(self):
        self.astro_sky.update(LSST_START_TIMESTAMP)
        self.assertEqual(self.astro_sky.date_profile.timestamp, LSST_START_TIMESTAMP)

    def test_sky_brightness_retrieval_internal_time_array_of_positions(self):
        self.create_ra_dec()
        self.astro_sky.update(LSST_START_TIMESTAMP)
        sky_mags = self.astro_sky.get_sky_brightness(self.ra_rads, self.dec_rads)
        self.assertEqual(sky_mags.size, self.ra_rads.size * LSST_NUM_FILTERS)

    def test_sky_brightness_retrieval_from_timestamp_set_and_array_of_positions(self):
        initial_timestamp = 1641081600.
        time_step = 5.0 * 60.0
        number_of_steps = 10
        self.create_ra_dec()
        sky_mags = self.astro_sky.get_sky_brightness_timeblock(initial_timestamp, time_step,
                                                               number_of_steps,
                                                               self.ra_rads, self.dec_rads)
        self.assertEquals(sky_mags.size, number_of_steps * self.ra_rads.size * LSST_NUM_FILTERS)
        self.assertEquals(sky_mags[0].size, self.ra_rads.size * LSST_NUM_FILTERS)
        self.assertAlmostEquals(sky_mags[0][0][0], 22.60926161, delta=1e-7)
