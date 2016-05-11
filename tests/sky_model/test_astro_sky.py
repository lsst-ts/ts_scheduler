import numpy
import unittest

from ts_scheduler.sky_model import AstronomicalSkyModel

from tests.test_constants import LSST_SITE, LSST_START_TIMESTAMP

class AstronomicalSkyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.astro_sky = AstronomicalSkyModel(LSST_SITE)
        cls.time_tolerance = 1e-6
        cls.sun_altitude = -12.0

    def create_ra_dec(self):
        self.ra_rads = numpy.radians(numpy.linspace(0., 90., 19))
        self.dec_rads = numpy.radians(numpy.linspace(-90., 0., 19))

    def check_night_boundary_tuple(self, truth_set_timestamp, truth_rise_timestamp):
        (set_timestamp, rise_timestamp) = self.astro_sky.get_night_boundaries(self.sun_altitude)
        self.assertAlmostEqual(set_timestamp, truth_set_timestamp, delta=self.time_tolerance)
        self.assertAlmostEqual(rise_timestamp, truth_rise_timestamp, delta=self.time_tolerance)

    def test_basic_information_after_initial_creation(self):
        self.assertIsNotNone(self.astro_sky.date_profile)
        self.assertEqual(self.astro_sky.date_profile.timestamp, 0)
        self.assertIsNotNone(self.astro_sky.sky_brightness)
        self.assertIsNotNone(self.astro_sky.sun)

    def test_update_mechanism(self):
        self.astro_sky.update(LSST_START_TIMESTAMP)
        self.assertEqual(self.astro_sky.date_profile.timestamp, LSST_START_TIMESTAMP)

    def test_sky_brightness_retrieval_internal_time_array_of_positions(self):
        self.create_ra_dec()
        self.astro_sky.update(LSST_START_TIMESTAMP)
        sky_mags = self.astro_sky.get_sky_brightness(self.ra_rads, self.dec_rads)
        self.assertEqual(sky_mags.size, self.ra_rads.size)

    def test_sky_brightness_retrieval_from_timestamp_set_and_array_of_positions(self):
        initial_timestamp = 1641081600.
        time_step = 5.0 * 60.0
        number_of_steps = 10
        self.create_ra_dec()
        sky_mags = self.astro_sky.get_sky_brightness_timeblock(initial_timestamp, time_step,
                                                               number_of_steps,
                                                               self.ra_rads, self.dec_rads)
        self.assertEquals(sky_mags.size, number_of_steps * self.ra_rads.size)
        self.assertEquals(sky_mags[0].size, self.ra_rads.size)
        self.assertAlmostEquals(sky_mags[0][0].u, 22.62361215, delta=1e-7)
        self.assertAlmostEquals(sky_mags[0][0].g, 21.92863773, delta=1e-7)
        self.assertAlmostEquals(sky_mags[0][0].r, 20.80615409, delta=1e-7)
        self.assertAlmostEquals(sky_mags[0][0].i, 19.79378908, delta=1e-7)
        self.assertAlmostEquals(sky_mags[0][0].z, 18.78361422, delta=1e-7)
        self.assertAlmostEquals(sky_mags[0][0].y, 17.56788428, delta=1e-7)

    def test_get_night_boundaries(self):
        self.astro_sky.update(LSST_START_TIMESTAMP)
        self.check_night_boundary_tuple(1641084532.843324, 1641113113.755558)
        # 2022/02/01
        self.astro_sky.update(1643673600)
        self.check_night_boundary_tuple(1643762299.348505, 1643793352.557206)
        # 2022/03/08
        self.astro_sky.update(1646697600)
        self.check_night_boundary_tuple(1646784061.294245, 1646819228.784648)
        # 2022/07/02
        self.astro_sky.update(1656720000)
        self.check_night_boundary_tuple(1656802219.515093, 1656845034.696892)
        # 2022/10/17
        self.astro_sky.update(1665964800)
        self.check_night_boundary_tuple(1666050479.261601, 1666084046.869362)
        # 2025/04/01
        self.astro_sky.update(1743465600)
        self.check_night_boundary_tuple(1743550264.401366, 1743588178.165652)
        # 2027/06/21
        self.astro_sky.update(1813536000)
        self.check_night_boundary_tuple(1813618020.702736, 1813660969.989451)
        # 2031/09/20
        self.astro_sky.update(1947628800)
        self.check_night_boundary_tuple(1947713387.331446, 1947750106.804758)

    def test_moon_separation_function(self):
        initial_timestamp = 1641081600 + (.04166666666 * 3600 * 24)
        self.create_ra_dec()
        self.astro_sky.update(initial_timestamp)
        self.astro_sky.get_sky_brightness(self.ra_rads, self.dec_rads)
        field_moon_sep = self.astro_sky.get_moon_separation(self.ra_rads, self.dec_rads)
        self.assertEqual(field_moon_sep.size, 19)
        self.assertAlmostEqual(field_moon_sep[0], numpy.radians(64.69897587))
