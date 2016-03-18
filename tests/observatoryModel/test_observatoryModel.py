import unittest
import math

from ts_scheduler.schedulerDefinitions import read_conf_file
from ts_scheduler.observatoryModel import ObservatoryModel

class ObservatoryModelTest(unittest.TestCase):

    def setUp(self):
        self.model = ObservatoryModel()

    def test_init(self):
        self.assertIsNotNone(self.model.log)
        self.assertEqual(self.model.location.longitude_rad, 0)
        self.assertEqual(self.model.currentState.telalt_rad, 1.5)

    def test_configure(self):
        siteconf = read_conf_file("conf/system/site.conf")
        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
        observatoryconf.update(siteconf)
        self.model.configure(observatoryconf)

        self.assertEqual(self.model.location.longitude_rad, math.radians(-70.7494))
        self.assertEqual(self.model.currentState.telalt_rad, math.radians(86.5))

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
        siteconf = read_conf_file("conf/system/site.conf")
        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
        observatoryconf.update(siteconf)
        self.model.configure(observatoryconf)

        self.model.reset()
        self.assertEqual(self.model.currentState.__str__(), "t=0.0 ra=0.000 dec=0.000 ang=0.000 filter=r track=False alt=86.500 az=0.000 pa=0.000 rot=0.000 telaz=0.000 telrot=0.000")

    def test_slew_altazrot(self):
        siteconf = read_conf_file("conf/system/site.conf")
        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
        observatoryconf.update(siteconf)
        self.model.configure(observatoryconf)
        self.model.reset()

        self.model.update_state(0)
        self.assertEqual(self.model.currentState.__str__(), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 telaz=0.000 telrot=0.000")
        self.model.slew_altazrot(0, math.radians(80), math.radians(0), math.radians(0))
        self.model.start_tracking(0)
        self.assertEqual(self.model.currentState.__str__(), "t=7.7 ra=29.374 dec=-20.244 ang=180.000 filter=r track=True alt=80.000 az=0.000 pa=-180.000 rot=0.000 telaz=0.000 telrot=0.000")

        self.model.update_state(100)
        self.assertEqual(self.model.currentState.__str__(), "t=100.0 ra=29.374 dec=-20.244 ang=180.000 filter=r track=True alt=79.994 az=357.918 pa=178.083 rot=358.083 telaz=-2.082 telrot=-1.917")
        self.model.slew_altazrot(100, math.radians(70), math.radians(30), math.radians(15))
        self.model.start_tracking(0)
        self.assertEqual(self.model.currentState.__str__(), "t=124.4 ra=39.952 dec=-12.558 ang=191.265 filter=r track=True alt=70.000 az=30.000 pa=-153.735 rot=15.000 telaz=30.000 telrot=15.000")

    def test_slew_radecang(self):
        siteconf = read_conf_file("conf/system/site.conf")
        observatoryconf = read_conf_file("conf/system/observatoryModel.conf")
        observatoryconf.update(siteconf)
        self.model.configure(observatoryconf)
        self.model.reset()

        self.model.update_state(0)
        self.assertEqual(self.model.currentState.__str__(), "t=0.0 ra=29.342 dec=-26.744 ang=180.000 filter=r track=False alt=86.500 az=0.000 pa=-180.000 rot=0.000 telaz=0.000 telrot=0.000")
        self.model.slew_radecang(0, math.radians(80), math.radians(0), math.radians(0))
        self.assertEqual(self.model.currentState.__str__(), "t=48.0 ra=80.000 dec=0.000 ang=-180.000 filter=r track=True alt=33.366 az=67.421 pa=-127.092 rot=52.908 telaz=67.421 telrot=52.908")

        self.model.update_state(100)
        self.assertEqual(self.model.currentState.__str__(), "t=100.0 ra=80.000 dec=0.000 ang=-180.000 filter=r track=True alt=33.539 az=67.264 pa=-127.179 rot=52.821 telaz=67.264 telrot=52.821")
        self.model.slew_radecang(100, math.radians(70), math.radians(-30), math.radians(15))
        self.assertEqual(self.model.currentState.__str__(), "t=124.8 ra=70.000 dec=-30.000 ang=-165.000 filter=r track=True alt=55.468 az=100.002 pa=-100.776 rot=64.224 telaz=100.002 telrot=64.224")
