import unittest

from ts_scheduler.setup.parser import create_parser

class ArgParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = create_parser()

    def test_parser_creation(self):
        self.assertIsNotNone(self.parser)

    def test_parser_help(self):
        self.assertIsNotNone(self.parser.format_help())

    def test_behavior_with_no_args(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.verbose, 0)
        self.assertFalse(args.scripted)
        self.assertIsNone(args.console_format)
        self.assertFalse(args.profile)

    def test_scripted_flag(self):
        args = self.parser.parse_args(["-s"])
        self.assertTrue(args.scripted)

    def test_verbose_flag_count(self):
        args = self.parser.parse_args(["-v", "-v", "-v"])
        self.assertEqual(args.verbose, 3)

    def test_profile(self):
        args = self.parser.parse_args(["--profile"])
        self.assertTrue(args.profile)
