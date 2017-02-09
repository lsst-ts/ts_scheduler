import numpy
import unittest
import warnings

from lsst.ts.scheduler.sky_model import AstronomicalSkyModel

from tests.constants import LSST_SITE, LSST_START_TIMESTAMP

class AstronomicalSkyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=RuntimeWarning, append=True)
        warnings.filterwarnings('ignore', category=FutureWarning, append=True)
        cls.astro_sky = AstronomicalSkyModel(LSST_SITE)
        cls.time_tolerance = 1e-6
        cls.sun_altitude = -12.0

    def create_ra_dec(self):
        self.ra_rads = numpy.radians(numpy.linspace(0., 90., 19))
        self.dec_rads = numpy.radians(numpy.linspace(-90., 0., 19))
        self.field_ids = numpy.arange(1, 20)

    def check_night_boundary_tuple(self, truth_set_timestamp, truth_rise_timestamp):
        (set_timestamp, rise_timestamp) = self.astro_sky.get_night_boundaries(self.sun_altitude)
        self.assertAlmostEqual(set_timestamp, truth_set_timestamp, delta=self.time_tolerance)
        self.assertAlmostEqual(rise_timestamp, truth_rise_timestamp, delta=self.time_tolerance)

    def test_basic_information_after_initial_creation(self):
        self.assertIsNotNone(self.astro_sky.date_profile)
        self.assertIsNotNone(self.astro_sky.sky_brightness)
        self.assertIsNotNone(self.astro_sky.sun)
        self.assertTrue(self.astro_sky.exclude_planets)

    def test_update_mechanism(self):
        self.astro_sky.update(LSST_START_TIMESTAMP)
        self.assertEqual(self.astro_sky.date_profile.timestamp, LSST_START_TIMESTAMP)

    def test_sky_brightness_retrieval_internal_time_array_of_positions(self):
        self.create_ra_dec()
        self.astro_sky.update(1641084532.843324)
        sky_mags = self.astro_sky.get_sky_brightness(self.field_ids)
        self.assertEqual(len(sky_mags), 6)
        self.assertEqual(sky_mags['g'].size, self.field_ids.size)

    def test_airmass_retrieval(self):
        self.create_ra_dec()
        self.astro_sky.update(1641084532.843324)
        airmass = self.astro_sky.get_airmass(self.field_ids)
        self.assertEqual(len(airmass), self.field_ids.size)
        self.assertAlmostEqual(airmass[0], 1.9853499253850071, delta=1e-7)

    def test_sky_brightness_retrieval_from_timestamp_set_and_array_of_positions(self):
        initial_timestamp = 1641081600.
        time_step = 5.0 * 60.0
        number_of_steps = 10
        self.create_ra_dec()
        sky_mags = self.astro_sky.get_sky_brightness_timeblock(initial_timestamp, time_step,
                                                               number_of_steps,
                                                               self.field_ids)
        self.assertEqual(len(sky_mags), number_of_steps)
        self.assertEqual(sky_mags[0]['g'].size, self.field_ids.size)
        self.assertAlmostEqual(sky_mags[0]['u'][0], 18.811567698177235, delta=1e-7)
        self.assertAlmostEqual(sky_mags[0]['g'][0], 19.115367630591688, delta=1e-7)
        self.assertAlmostEqual(sky_mags[0]['r'][0], 19.223547839614682, delta=1e-7)
        self.assertAlmostEqual(sky_mags[0]['i'][0], 18.144658531311183, delta=1e-7)
        self.assertAlmostEqual(sky_mags[0]['z'][0], 17.155387687993628, delta=1e-7)
        self.assertAlmostEqual(sky_mags[0]['y'][0], 15.988078842357307, delta=1e-7)

    def test_get_night_boundaries(self):
        # 2022/01/01
        # At sunset
        self.astro_sky.update(1641084532.843324)
        self.check_night_boundary_tuple(1641084532.843324, 1641113113.755558)
        # In night
        self.astro_sky.update(1641098823.29944)
        self.check_night_boundary_tuple(1641084532.843324, 1641113113.755558)
        # At sunrise, next night bounds
        self.astro_sky.update(1641113113.755558)
        self.check_night_boundary_tuple(1641170940.8965435, 1641199562.951024)
        # In daytime, next night bounds
        self.astro_sky.update(1641113114.755558)
        self.check_night_boundary_tuple(1641170940.8965435, 1641199562.951024)
        self.astro_sky.update(1641133114.755558)
        self.check_night_boundary_tuple(1641170940.8965435, 1641199562.951024)
        # 2022/02/01
        self.astro_sky.update(1643762299.348505)
        self.check_night_boundary_tuple(1643762299.348505, 1643793352.557206)
        # 2022/03/08
        self.astro_sky.update(1646784061.294245)
        self.check_night_boundary_tuple(1646784061.294245, 1646819228.784648)
        # 2022/07/02
        # At sunset
        self.astro_sky.update(1656802219.515093)
        self.check_night_boundary_tuple(1656802219.515093, 1656845034.696892)
        # At sunrise, next night bounds
        self.astro_sky.update(1656845034.696892)
        self.check_night_boundary_tuple(1656888641.725961, 1656931433.3882337)
        # In daytime, next night bounds
        self.astro_sky.update(1656845035.696892)
        self.check_night_boundary_tuple(1656888641.725961, 1656931433.3882337)
        # 2022/10/17
        self.astro_sky.update(1666050479.261601)
        self.check_night_boundary_tuple(1666050479.261601, 1666084046.869362)
        # 2025/04/01
        self.astro_sky.update(1743550264.401366)
        self.check_night_boundary_tuple(1743550264.401366, 1743588178.165652)
        # 2027/06/21
        self.astro_sky.update(1813618020.702736)
        self.check_night_boundary_tuple(1813618020.702736, 1813660969.989451)
        # 2031/09/20
        self.astro_sky.update(1947713387.331446)
        self.check_night_boundary_tuple(1947713387.331446, 1947750106.804758)

    def test_separation_function(self):
        initial_timestamp = 1641081600 + (.04166666666 * 3600 * 24)
        self.create_ra_dec()
        self.astro_sky.update(initial_timestamp)
        field_moon_sep = self.astro_sky.get_separation("moon", self.ra_rads, self.dec_rads)
        self.assertEqual(field_moon_sep.size, 19)
        self.assertAlmostEqual(field_moon_sep[0], numpy.radians(64.6988849))
        field_sun_sep = self.astro_sky.get_separation("sun", self.ra_rads, self.dec_rads)
        self.assertEqual(field_sun_sep.size, 19)
        self.assertAlmostEqual(field_sun_sep[0], numpy.radians(67.06949045))

    def test_moon_sun_information(self):
        initial_timestamp = 1641081600 + (.04166666666 * 3600 * 24)
        self.create_ra_dec()
        self.astro_sky.update(initial_timestamp)
        info = self.astro_sky.get_moon_sun_info(self.ra_rads, self.dec_rads)
        self.assertEqual(len(info), 11)
        self.assertAlmostEqual(info["moonPhase"], 0.86929207727236935, delta=1e-7)
        self.assertEqual(len(info["moonDist"]), self.ra_rads.size)
        self.assertAlmostEqual(info["moonDist"][0], 1.1292085643462495, delta=1e-7)
        self.assertAlmostEqual(info["moonDec"], -0.44158776244864711, delta=1e-7)
        self.assertAlmostEqual(info["moonRA"], 4.7244118956305821, delta=1e-7)
        self.assertEqual(len(info["solarElong"]), self.ra_rads.size)
        self.assertAlmostEqual(info["solarElong"][0], 1.1705834338898418, delta=1e-7)

    def test_target_information(self):
        initial_timestamp = 1641081600 + (.04166666666 * 3600 * 24)
        self.create_ra_dec()
        self.astro_sky.update(initial_timestamp)
        info = self.astro_sky.get_target_information(self.field_ids, self.ra_rads, self.dec_rads)
        self.assertEqual(len(info), 3)
        self.assertEqual(info['airmass'].size, self.field_ids.size)
        self.assertEqual(info['altitude'].size, self.ra_rads.size)
        self.assertEqual(info['azimuth'].size, self.ra_rads.size)
        self.assertAlmostEqual(info['airmass'][0], 1.9853499253850071, delta=1e-7)
        self.assertAlmostEqual(info['altitude'][0], 0.52786436029017303, delta=1e-7)
        self.assertFalse(numpy.isnan(info['azimuth'][0]))

    def test_configure(self):
        self.astro_sky.configure(exclude_planets=False)
        self.assertFalse(self.astro_sky.exclude_planets)
