import unittest
import math

from ts_scheduler.schedulerDefinitions import conf_file_path, read_conf_file
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryLocation, ObservatoryModel

class ObservatoryModelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        siteconf = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        cls.location = ObservatoryLocation()
        cls.location.configure(siteconf)

        observatoryconf = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                        "observatory_model.conf"))
        cls.model = ObservatoryModel(cls.location)
        cls.model.configure(observatoryconf)

    def setUp(self):
        self.model.reset()

    def test_init(self):
        temp_model = ObservatoryModel(self.location)
        self.assertIsNotNone(temp_model.log)
        self.assertAlmostEquals(temp_model.location.longitude_rad, -1.23480, delta=1e6)
        self.assertEqual(temp_model.currentState.telalt_rad, 1.5)

    def test_configure(self):
        observatoryconf = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                        "observatory_model.conf"))
        temp_model = ObservatoryModel(self.location)
        temp_model.configure(observatoryconf)

        self.assertEqual(temp_model.location.longitude_rad, math.radians(-70.7494))
        self.assertEqual(temp_model.location.longitude, -70.7494)
        self.assertEqual(temp_model.currentState.telalt_rad, math.radians(86.5))

    def test_get_closest_angle_distance_unlimited(self):
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(0), math.radians(0)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(90), math.radians(0)),
                         (math.radians(90), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(180), math.radians(0)),
                         (math.radians(180), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(360), math.radians(0)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-90), math.radians(0)),
                         (math.radians(-90), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-180), math.radians(0)),
                         (math.radians(180), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-360), math.radians(0)),
                         (math.radians(0), math.radians(0)))

    def test_get_closest_angle_distance_cable_wrap270(self):
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(0), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(90), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(90), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(180), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(180), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(360), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-90), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(-90), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-180), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(180), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-360), math.radians(0),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(0)))

        self.assertEqual(self.model.get_closest_angle_distance(math.radians(0), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(-180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(90), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(90), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(180), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(180), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(360), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(-180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-90), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(270), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-180), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(180), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-360), math.radians(180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(-180)))

        self.assertEqual(self.model.get_closest_angle_distance(math.radians(0), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(90), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(-270), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(180), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(-180), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(360), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(180)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-90), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(-90), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-180), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(-180), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-360), math.radians(-180),
                                                               math.radians(-270), math.radians(270)),
                         (math.radians(0), math.radians(180)))

    def test_get_closest_angle_distance_cable_wrap90(self):
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(0), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(45), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(45), math.radians(45)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(90), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(90), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(180), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(270), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(-90), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(360), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-45), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(-45), math.radians(-45)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-90), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(-90), math.radians(-90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-180), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(0), math.radians(0)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-270), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(90), math.radians(90)))
        self.assertEqual(self.model.get_closest_angle_distance(math.radians(-360), math.radians(0),
                                                               math.radians(-90), math.radians(90)),
                         (math.radians(0), math.radians(0)))

    def test_reset(self):
        self.model.reset()
        self.assertEqual(self.model.currentState.__str__(), "t=0.0 ra=0.000 dec=0.000 ang=0.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_slew_altaz(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_altaz(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=7.7 ra=29.510 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=80.000 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=29.510 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=79.994 az=357.901 pa=178.068 rot=358.068 "
                         "telaz=-2.099 telrot=-1.932 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_altaz(100, math.radians(70), math.radians(30), math.radians(15), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=144.4 ra=40.172 dec=-12.558 ang=191.265 "
                         "filter=r track=True alt=70.000 az=30.000 pa=-153.735 rot=15.000 "
                         "telaz=30.000 telrot=15.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_slew_radec(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.540 az=67.263 pa=-127.179 rot=52.821 "
                         "telaz=67.263 telrot=52.821 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.650 az=67.163 pa=-127.234 rot=52.766 "
                         "telaz=67.163 telrot=52.766 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(100, math.radians(70), math.radians(-30), math.radians(15), "r")
        self.assertEqual(str(self.model.currentState), "t=144.9 ra=70.000 dec=-30.000 ang=-165.000 "
                         "filter=r track=True alt=55.654 az=99.940 pa=-100.718 rot=64.282 "
                         "telaz=99.940 telrot=64.282 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_get_slew_delay(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = True
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 74.174, delta=1e-3)

        self.model.slew(target)

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "g"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 120, delta=1e-3)

        target = Target()
        target.ra_rad = math.radians(50)
        target.dec_rad = math.radians(-10)
        target.ang_rad = math.radians(10)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 22.556, delta=1e-3)

        self.model.slew(target)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

        target.ang_rad = math.radians(15)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 4.472, delta=1e-3)

    def test_get_slew_delay_followsky_false(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = False
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 74.174, delta=1e-3)

        self.model.slew(target)

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "g"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 120, delta=1e-3)

        target = Target()
        target.ra_rad = math.radians(50)
        target.dec_rad = math.radians(-10)
        target.ang_rad = math.radians(10)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 22.556, delta=1e-3)

        self.model.slew(target)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

        target.ang_rad = math.radians(15)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

    def test_slew(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=74.2 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=r track=True alt=60.904 az=76.495 pa=-116.632 rot=63.368 "
                         "telaz=76.495 telrot=63.368 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "i"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=194.2 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=i track=True alt=61.324 az=76.056 pa=-116.844 rot=63.156 "
                         "telaz=76.056 telrot=63.156 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_slewdata(self):
        self.model.update_state(0)

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=74.2 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=r track=True alt=60.904 az=76.495 pa=-116.632 rot=63.368 "
                         "telaz=76.495 telrot=63.368 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        lastslew_delays_dict = self.model.lastslew_delays_dict
        self.assertAlmostEquals(lastslew_delays_dict["telalt"], 8.387, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telaz"], 11.966, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telrot"], 21.641, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsopenloop"], 7.387, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsclosedloop"], 20.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domalt"], 18.775, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domaz"], 53.174, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domazsettle"], 1.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["filter"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["readout"], 2.0, delta=1e-3)
        lastslew_criticalpath = self.model.lastslew_criticalpath
        self.assertEqual(str(lastslew_criticalpath), "['telopticsclosedloop', 'domazsettle', 'domaz']")

        self.assertAlmostEquals(math.degrees(self.model.currentState.telalt_peakspeed_rad), -3.50, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telaz_peakspeed_rad), 7.00, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telrot_peakspeed_rad), 3.50, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domalt_peakspeed_rad), -1.75, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domaz_peakspeed_rad), 1.50, delta=1e-3)

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "i"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=194.2 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=i track=True alt=61.324 az=76.056 pa=-116.844 rot=63.156 "
                         "telaz=76.056 telrot=63.156 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        lastslew_delays_dict = self.model.lastslew_delays_dict
        self.assertAlmostEquals(lastslew_delays_dict["telalt"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telaz"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telrot"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsopenloop"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsclosedloop"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domalt"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domaz"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domazsettle"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["filter"], 120.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["readout"], 2.0, delta=1e-3)
        lastslew_criticalpath = self.model.lastslew_criticalpath

        self.assertEqual(str(lastslew_criticalpath), "['filter']")
        self.assertAlmostEquals(math.degrees(self.model.currentState.telalt_peakspeed_rad), 0, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telaz_peakspeed_rad), 0, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telrot_peakspeed_rad), 0, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domalt_peakspeed_rad), 0, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domaz_peakspeed_rad), 0, delta=1e-3)

        target = Target()
        target.ra_rad = math.radians(61)
        target.dec_rad = math.radians(-21)
        target.ang_rad = math.radians(1)
        target.filter = "i"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=199.0 ra=61.000 dec=-21.000 ang=-179.000 "
                         "filter=i track=True alt=60.931 az=78.751 pa=-114.828 rot=64.172 "
                         "telaz=78.751 telrot=64.172 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        lastslew_delays_dict = self.model.lastslew_delays_dict
        self.assertAlmostEquals(lastslew_delays_dict["telalt"], 0.683, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telaz"], 1.244, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telrot"], 2.022, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsopenloop"], 0.117, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsclosedloop"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domalt"], 1.365, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domaz"], 3.801, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domazsettle"], 1.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["filter"], 0.000, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["readout"], 2.000, delta=1e-3)
        lastslew_criticalpath = self.model.lastslew_criticalpath

        self.assertEqual(str(lastslew_criticalpath), "['domazsettle', 'domaz']")
        self.assertAlmostEquals(math.degrees(self.model.currentState.telalt_peakspeed_rad),
                                -1.194, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telaz_peakspeed_rad),
                                4.354, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telrot_peakspeed_rad),
                                1.011, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domalt_peakspeed_rad),
                                -0.598, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domaz_peakspeed_rad),
                                1.425, delta=1e-3)

    def test_rotator_followsky_true(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = True
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.540 az=67.263 pa=-127.179 rot=52.821 "
                         "telaz=67.263 telrot=52.821 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(83.5), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=72.8 ra=83.500 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=30.744 az=69.709 pa=-125.877 rot=54.123 "
                         "telaz=69.709 telrot=54.123 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_rotator_followsky_false(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = False
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-127.067 "
                         "filter=r track=True alt=33.540 az=67.263 pa=-127.179 rot=359.888 "
                         "telaz=67.263 telrot=-0.112 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(83.5), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=72.8 ra=83.500 dec=0.000 ang=-125.759 "
                         "filter=r track=True alt=30.744 az=69.709 pa=-125.877 rot=359.881 "
                         "telaz=69.709 telrot=-0.119 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.params.Rotator_FollowSky = True

    def test_swap_filter(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.assertEqual(str(self.model.parkState), "t=0.0 ra=0.000 dec=0.000 ang=0.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.swap_filter("z")
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'y', 'u'] unmounted=['z']")
        self.assertEqual(str(self.model.parkState), "t=0.0 ra=0.000 dec=0.000 ang=0.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'y', 'u'] unmounted=['z']")
        self.model.swap_filter("u")
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.480 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'y', 'z'] unmounted=['u']")
        self.assertEqual(str(self.model.parkState), "t=0.0 ra=0.000 dec=0.000 ang=0.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'y', 'z'] unmounted=['u']")
