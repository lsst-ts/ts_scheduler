import os
import unittest

from lsst.ts.scheduler.kernel import conf_file_path, read_conf_file

class DefinitionsTest(unittest.TestCase):

    def test_conf_file_path(self):
        file_path = conf_file_path(__name__, "../conf", "system", "site.conf")
        self.assertTrue(os.path.exists(file_path))

    def test_read_conf_file(self):
        file_path = conf_file_path(__name__, "../conf", "survey", "areaProp1.conf")
        conf_dict = read_conf_file(file_path)
        self.assertEquals(len(conf_dict), 11)
        sky_region_cuts = conf_dict["sky_region"]["cuts"]
        self.assertEqual(len(sky_region_cuts), 2)
        self.assertEqual(sky_region_cuts[0][0], 'RA')

    def test_new_fields(self):
        file_path = conf_file_path(__name__, "../conf", "survey", "rolling_cadence.conf")
        conf_dict = read_conf_file(file_path)
        selection_mappings = conf_dict["sky_region"]["selection_mappings"]
        self.assertEqual(len(selection_mappings), 5)
        self.assertEqual(len(selection_mappings[0]), 1)
        self.assertTupleEqual(selection_mappings[0], (0,))
        self.assertTupleEqual(selection_mappings[1], (1,))

if __name__ == "__main__":
    unittest.main()
