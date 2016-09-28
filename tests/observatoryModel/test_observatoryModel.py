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
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_altaz(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=7.7 ra=29.374 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=80.000 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=29.374 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=79.994 az=357.918 pa=178.083 rot=358.083 "
                         "telaz=-2.082 telrot=-1.917 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_altaz(100, math.radians(70), math.radians(30), math.radians(15), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=144.4 ra=40.035 dec=-12.558 ang=191.265 "
                         "filter=r track=True alt=70.000 az=30.000 pa=-153.735 rot=15.000 "
                         "telaz=30.000 telrot=15.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_slew_radec(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.433 az=67.360 pa=-127.125 rot=52.875 "
                         "telaz=67.360 telrot=52.875 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.539 az=67.264 pa=-127.179 rot=52.821 "
                         "telaz=67.264 telrot=52.821 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(100, math.radians(70), math.radians(-30), math.radians(15), "r")
        self.assertEqual(str(self.model.currentState), "t=144.8 ra=70.000 dec=-30.000 ang=-165.000 "
                         "filter=r track=True alt=55.539 az=99.978 pa=-100.754 rot=64.246 "
                         "telaz=99.978 telrot=64.246 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_get_slew_delay(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = True
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 74.253, delta=1e-3)

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
        self.assertAlmostEquals(delay, 22.487, delta=1e-3)

        self.model.slew(target)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

        target.ang_rad = math.radians(15)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 4.472, delta=1e-3)

    def test_get_slew_delay_followsky_false(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = False
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 74.253, delta=1e-3)

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
        self.assertAlmostEquals(delay, 22.487, delta=1e-3)

        self.model.slew(target)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

        target.ang_rad = math.radians(15)
        delay = self.model.get_slew_delay(target)
        self.assertAlmostEquals(delay, 2.0, delta=1e-3)

    def test_slew(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=74.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=r track=True alt=60.788 az=76.614 pa=-116.575 rot=63.425 "
                         "telaz=76.614 telrot=63.425 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "i"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=194.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=i track=True alt=61.209 az=76.177 pa=-116.785 rot=63.215 "
                         "telaz=76.177 telrot=63.215 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_slewdata(self):
        self.model.update_state(0)

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=74.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=r track=True alt=60.788 az=76.614 pa=-116.575 rot=63.425 "
                         "telaz=76.614 telrot=63.425 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        lastslew_delays_dict = self.model.lastslew_delays_dict
        self.assertAlmostEquals(lastslew_delays_dict["telalt"], 8.421, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telaz"], 11.983, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telrot"], 21.657, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsopenloop"], 7.421, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsclosedloop"], 20.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domalt"], 18.842, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domaz"], 53.253, delta=1e-3)
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
        self.assertEqual(str(self.model.currentState), "t=194.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=i track=True alt=61.209 az=76.177 pa=-116.785 rot=63.215 "
                         "telaz=76.177 telrot=63.215 "
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
                         "filter=i track=True alt=60.817 az=78.859 pa=-114.782 rot=64.218 "
                         "telaz=78.859 telrot=64.218 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        lastslew_delays_dict = self.model.lastslew_delays_dict
        self.assertAlmostEquals(lastslew_delays_dict["telalt"], 0.683, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telaz"], 1.242, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telrot"], 2.010, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsopenloop"], 0.117, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["telopticsclosedloop"], 0.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domalt"], 1.367, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domaz"], 3.793, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["domazsettle"], 1.0, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["filter"], 0.000, delta=1e-3)
        self.assertAlmostEquals(lastslew_delays_dict["readout"], 2.000, delta=1e-3)
        lastslew_criticalpath = self.model.lastslew_criticalpath

        self.assertEqual(str(lastslew_criticalpath), "['domazsettle', 'domaz']")
        self.assertAlmostEquals(math.degrees(self.model.currentState.telalt_peakspeed_rad),
                                -1.196, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telaz_peakspeed_rad),
                                4.346, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.telrot_peakspeed_rad),
                                1.005, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domalt_peakspeed_rad),
                                -0.598, delta=1e-3)
        self.assertAlmostEquals(math.degrees(self.model.currentState.domaz_peakspeed_rad),
                                1.423, delta=1e-3)

    def test_rotator_followsky_true(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = True
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.433 az=67.360 pa=-127.125 rot=52.875 "
                         "telaz=67.360 telrot=52.875 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(83.5), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=72.8 ra=83.500 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=30.634 az=69.801 pa=-125.830 rot=54.170 "
                         "telaz=69.801 telrot=54.170 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")

    def test_rotator_followsky_false(self):
        self.model.update_state(0)
        self.model.params.Rotator_FollowSky = False
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 "
                         "telaz=0.000 telrot=0.000 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-127.013 "
                         "filter=r track=True alt=33.433 az=67.360 pa=-127.125 rot=359.887 "
                         "telaz=67.360 telrot=-0.113 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.slew_radec(0, math.radians(83.5), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=72.8 ra=83.500 dec=0.000 ang=-125.711 "
                         "filter=r track=True alt=30.634 az=69.801 pa=-125.830 rot=359.880 "
                         "telaz=69.801 telrot=-0.120 "
                         "mounted=['g', 'r', 'i', 'z', 'y'] unmounted=['u']")
        self.model.params.Rotator_FollowSky = True
