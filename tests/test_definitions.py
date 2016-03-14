import os
import unittest

from ts_scheduler.schedulerDefinitions import conf_file_path
import ts_scheduler.schedulerMain

class DefinitionsTest(unittest.TestCase):

    def test_conf_file_path(self):
        file_path = conf_file_path(ts_scheduler.schedulerMain.__name__, "../conf", "system", "site.conf")
        self.assertTrue(os.path.exists(file_path))
