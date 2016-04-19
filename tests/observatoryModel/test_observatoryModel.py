import unittest
import math

from ts_scheduler.schedulerDefinitions import read_conf_file
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryLocation, ObservatoryModel

class ObservatoryModelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        siteconf = read_conf_file("conf/system/site.conf")
        cls.location = ObservatoryLocation()
        cls.location.configure(siteconf)

        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
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
        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
        temp_model = ObservatoryModel(self.location)
        temp_model.configure(observatoryconf)

        self.assertEqual(temp_model.location.longitude_rad, math.radians(-70.7494))
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
                         "filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 rot_sky=0.000 "
                         "telaz=0.000 telrot=0.000")

    def test_slew_altaz(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 rot_sky=180.000 "
                         "telaz=0.000 telrot=0.000")
        self.model.slew_altaz(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=7.7 ra=29.374 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=80.000 az=0.000 pa=-180.000 rot=0.000 rot_sky=180.000 "
                         "telaz=0.000 telrot=0.000")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=29.374 dec=-20.244 ang=180.000 "
                         "filter=r track=True alt=79.994 az=357.918 pa=178.083 rot=358.083 rot_sky=180.000 "
                         "telaz=-2.082 telrot=-1.917")
        self.model.slew_altaz(100, math.radians(70), math.radians(30), math.radians(15), "r")
        self.model.start_tracking(0)
        self.assertEqual(str(self.model.currentState), "t=144.4 ra=40.035 dec=-12.558 ang=191.265 "
                         "filter=r track=True alt=70.000 az=30.000 pa=-153.735 rot=15.000 rot_sky=168.735 "
                         "telaz=30.000 telrot=15.000")

    def test_slew_radec(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 rot_sky=180.000 "
                         "telaz=0.000 telrot=0.000")
        self.model.slew_radec(0, math.radians(80), math.radians(0), math.radians(0), "r")
        self.assertEqual(str(self.model.currentState), "t=68.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.433 az=67.360 pa=-127.125 rot=52.875 rot_sky=180.000 "
                         "telaz=67.360 telrot=52.875")

        self.model.update_state(100)
        self.assertEqual(str(self.model.currentState), "t=100.0 ra=80.000 dec=0.000 ang=-180.000 "
                         "filter=r track=True alt=33.539 az=67.264 pa=-127.179 rot=52.821 rot_sky=180.000 "
                         "telaz=67.264 telrot=52.821")
        self.model.slew_radec(100, math.radians(70), math.radians(-30), math.radians(15), "r")
        self.assertEqual(str(self.model.currentState), "t=144.8 ra=70.000 dec=-30.000 ang=-165.000 "
                         "filter=r track=True alt=55.539 az=99.978 pa=-100.754 rot=64.246 rot_sky=165.000 "
                         "telaz=99.978 telrot=64.246")

    def test_get_slew_delay(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 rot_sky=180.000 "
                         "telaz=0.000 telrot=0.000")

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

    def test_slew(self):
        self.model.update_state(0)
        self.assertEqual(str(self.model.currentState), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 "
                         "filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 rot_sky=180.000 "
                         "telaz=0.000 telrot=0.000")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "r"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=74.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=r track=True alt=60.788 az=76.614 pa=-116.575 rot=63.425 rot_sky=180.000 "
                         "telaz=76.614 telrot=63.425")

        target = Target()
        target.ra_rad = math.radians(60)
        target.dec_rad = math.radians(-20)
        target.ang_rad = math.radians(0)
        target.filter = "i"

        self.model.slew(target)
        self.assertEqual(str(self.model.currentState), "t=194.3 ra=60.000 dec=-20.000 ang=-180.000 "
                         "filter=i track=True alt=61.209 az=76.177 pa=-116.785 rot=63.215 rot_sky=180.000 "
                         "telaz=76.177 telrot=63.215")
