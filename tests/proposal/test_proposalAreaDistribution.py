import unittest

from ts_scheduler.schedulerDefinitions import read_conf_file, conf_file_path
from ts_scheduler.proposal import AreaDistributionProposal
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.sky_model import AstronomicalSkyModel

class AreaDistributionProposalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        site_confdict = read_conf_file(conf_file_path(__name__, "../../conf", "system", "site.conf"))
        location = ObservatoryLocation()
        location.configure(site_confdict)
        cls.skyModel = AstronomicalSkyModel(location)

    def setUp(self):
        self.areaprop = AreaDistributionProposal(conf_file_path(__name__, "../../conf", "survey",
                                                 "areaProp1.conf"), self.skyModel)

    def test_init(self):
        self.assertEqual(self.areaprop.name, "areaProp1")

    def test_build_night_target_list(self):
        """Set timestamp as 2022-01-01 0h UTC"""
        lsst_start_timestamp = 1640995200.0

        self.areaprop.build_night_target_list(lsst_start_timestamp)
        fieldid_list = self.areaprop.fields_tonight_list
        self.assertEqual(len(fieldid_list), 5)
        self.assertEqual(str(fieldid_list), "[1764, 2006, 2234, 2464, 2692]")
        self.assertEqual(str(self.areaprop.fields_tonight_dict[fieldid_list[0]]),
                         "ID=1764 ra=13.726 dec=-19.793 gl=129.297 gb=-82.622 el=4.457 eb=-23.547 fov=3.500")
        self.assertEqual(str(self.areaprop.fields_tonight_dict[fieldid_list[-1]]),
                         "ID=2692 ra=14.146 dec=0.931 gl=125.664 gb=-61.913 el=13.451 eb=-4.720 fov=3.500")

        lsst_six_months = lsst_start_timestamp + 182 * 24 * 3600

        self.areaprop.build_night_target_list(lsst_six_months)
        fieldid_list = self.areaprop.fields_tonight_list
        self.assertEqual(len(fieldid_list), 73)
        self.assertEqual(str(fieldid_list),
                         "[1764, 1819, 1824, 1825, 1840, 1841, 1860, 1861, 1873, 1939, 1940, 1949, 1950, "
                         "1973, 1974, 1996, 2006, 2061, 2066, 2067, 2084, 2085, 2105, 2106, 2108, 2183, "
                         "2184, 2201, 2202, 2211, 2212, 2226, 2234, 2304, 2315, 2316, 2319, 2320, 2329, "
                         "2330, 2346, 2425, 2426, 2427, 2428, 2439, 2440, 2450, 2464, 2536, 2543, 2544, "
                         "2555, 2556, 2563, 2564, 2572, 2655, 2656, 2657, 2658, 2669, 2670, 2682, 2692, "
                         "2762, 2769, 2770, 2783, 2784, 2787, 2788, 2802]")
        self.assertEqual(str(self.areaprop.fields_tonight_dict[fieldid_list[0]]),
                         "ID=1764 ra=13.726 dec=-19.793 gl=129.297 gb=-82.622 el=4.457 eb=-23.547 fov=3.500")
        self.assertEqual(str(self.areaprop.fields_tonight_dict[fieldid_list[-1]]),
                         "ID=2802 ra=12.654 dec=3.318 gl=122.527 gb=-59.554 el=13.001 eb=-1.942 fov=3.500")
