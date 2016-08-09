import os
import unittest

from ts_scheduler.schedulerDefinitions import conf_file_path, read_conf_file
import ts_scheduler.schedulerMain

class DefinitionsTest(unittest.TestCase):

    def test_conf_file_path(self):
        file_path = conf_file_path(ts_scheduler.schedulerMain.__name__, "../conf", "system", "site.conf")
        self.assertTrue(os.path.exists(file_path))

    def test_read_conf_file(self):
        file_path = conf_file_path(ts_scheduler.schedulerMain.__name__, "../conf", "survey", "areaProp1.conf")
        conf_dict = read_conf_file(file_path)
        self.assertEquals(len(conf_dict), 11)
        sky_region_cuts = conf_dict["sky_region"]["cuts"]
        self.assertEqual(len(sky_region_cuts), 2)
        self.assertEqual(sky_region_cuts[0][0], 'RA')

if __name__ == "__main__":
    unittest.main()
