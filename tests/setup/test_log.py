import collections
import logging
import logging.handlers
try:
    from unittest import mock
except ImportError:
    import mock
import os
import unittest

from ts_scheduler.setup.log import configure_logging, generate_logfile

class LogTest(unittest.TestCase):

    def setUp(self):
        self.args = collections.namedtuple('args', ['verbose', 'console_format', 'scripted'])
        self.args.verbose = 0
        self.args.console_format = None
        self.args.scripted = False

        self.log_file_name = "scheduler.2016-03-10_15:50:01.log"

    @mock.patch("time.strftime")
    def test_logfile_creation(self, mock_strftime):
        mock_strftime.return_value = "2016-03-10_15:50:01"
        log_path = generate_logfile()
        self.assertEqual(mock_strftime.called, 1)
        self.assertEqual(os.path.basename(log_path), self.log_file_name)

    def test_configure_logging_default(self):
        configure_logging(self.args, self.log_file_name)
        self.assertEqual(len(logging.getLogger().handlers), 2)
        self.assertIsInstance(logging.getLogger().handlers[1], logging.FileHandler)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.DEBUG)
