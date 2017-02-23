import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lsst.ts.scheduler import Main
from tests.sequence_prop_topic import seqprop

class TestSequencePropTopicReader(unittest.TestCase):

    def setUp(self):
        patcher1 = mock.patch("lsst.ts.scheduler.main.Driver")
        self.addCleanup(patcher1.stop)
        self.mock_driver = patcher1.start()

        self.main = Main(None)

    def check_filter(self, cdict, name, *truths):
        band_filter = "filter_{}".format(name)
        self.assertTrue(band_filter in cdict)
        self.assertEqual(cdict[band_filter]["min_brig"], truths[0])
        self.assertEqual(cdict[band_filter]["max_brig"], truths[1])
        self.assertEqual(cdict[band_filter]["max_seeing"], truths[2])
        self.assertListEqual(cdict[band_filter]["exp_times"], truths[3])

    def check_subsequence(self, cdict, name, is_master, *truths):
        offset = 1
        if is_master:
            offset = 0
        self.assertTrue(name in cdict)
        if not is_master:
            self.assertListEqual(cdict[name]["filters"], truths[0])
            self.assertListEqual(cdict[name]["visits_per_filter"], truths[1])
        else:
            self.assertListEqual(cdict[name]["nested_names"], truths[0])
        self.assertEqual(cdict[name]["num_events"], truths[1 + offset])
        self.assertEqual(cdict[name]["num_max_missed"], truths[2 + offset])
        self.assertEqual(cdict[name]["time_interval"], truths[3 + offset])
        self.assertEqual(cdict[name]["time_window_start"], truths[4 + offset])
        self.assertEqual(cdict[name]["time_window_max"], truths[5 + offset])
        self.assertEqual(cdict[name]["time_window_end"], truths[6 + offset])
        self.assertEqual(cdict[name]["time_weight"], truths[7 + offset])

    def test_reader(self):
        confdict = self.main.rtopic_seq_prop_config(seqprop)
        self.assertEquals(confdict["sky_nightly_bounds"]["twilight_boundary"], -18.0)
        self.assertEquals(confdict["sky_nightly_bounds"]["delta_lst"], 60.0)
        self.assertEquals(confdict["constraints"]["max_cloud"], 0.7)
        self.assertEquals(confdict["constraints"]["max_airmass"], 1.5)
        self.assertEquals(confdict["constraints"]["min_distance_moon"], 30.0)
        self.assertTrue(confdict["constraints"]["exclude_planets"])
        self.assertListEqual(confdict["sky_region"]["user_regions"], [1, 20, 350, 4015])
        self.assertEqual(confdict["sky_exclusions"]["dec_window"], 90.0)
        self.assertListEqual(confdict["subsequences"]["names"], ["test1"])
        self.check_subsequence(confdict, "subseq_test1", False,
                               ["g", "r", "i", "z", "y"], [20, 25, 30, 20, 27],
                               30, 2, 432000, 0.0, 1.0, 2.0, 1.0)
        self.assertListEqual(confdict["master_subsequences"]["names"], ["master1", "master2"])
        self.assertListEqual(confdict["master_subsequences"]["num_nested"], [2, 1])
        self.check_subsequence(confdict, "msubseq_master1", True, ["nested1", "nested2"],
                               20, 1, 648000, 0.0, 1.0, 2.0, 1.0)
        self.check_subsequence(confdict, "msubseq_master2", True, ["nested3"],
                               15, 3, 518400, 0.0, 1.0, 2.0, 1.0)
        self.check_subsequence(confdict, "nsubseq_nested1", False,
                               ["r", "g", "i"], [10, 10, 20],
                               20, 1, 7200, 0.0, 1.0, 2.0, 1.0)
        self.check_subsequence(confdict, "nsubseq_nested2", False,
                               ["z", "y"], [3, 3],
                               10, 1, 3600, 0.0, 1.0, 2.0, 1.0)
        self.check_subsequence(confdict, "nsubseq_nested3", False,
                               ["u", "y"], [5, 5],
                               15, 5, 900, 0.0, 1.0, 2.0, 1.0)
        band_filters = "u,g,r,i,z,y"
        for band_filter in band_filters.split(','):
            self.check_filter(confdict, band_filter, 21.0, 30.0, 2.0, [15, 15])
        self.assertEquals(confdict["scheduling"]["max_num_targets"], 100)
        self.assertFalse(confdict["scheduling"]["accept_serendipity"])
        self.assertTrue(confdict["scheduling"]["accept_consecutive_visits"])
        self.assertEquals(confdict["scheduling"]["airmass_bonus"], 0.5)
        self.assertEquals(confdict["scheduling"]["hour_angle_bonus"], 0.5)
