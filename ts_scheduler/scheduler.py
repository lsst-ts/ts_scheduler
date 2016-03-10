#!/usr/bin/env python

import argparse
import sys

from schedulerMain import Main

if (__name__ == '__main__'):
    description = ["This is the main driver script for the LSST Scheduler."]

    parser = argparse.ArgumentParser(usage="scheduler.py [options]",
                                     description=" ".join(description),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-s", "--scripted", dest="scripted", action="store_true",
                        help="Flag to run the Scheduler code from another script.")
    parser.add_argument("-v", "--verbose", dest="verbose", action='count', default=0,
                        help="Set the verbosity for the console logging.")
    parser.add_argument("-c", "--console-format", dest="console_format", default=None,
                        help="Override the console format.")

    args = parser.parse_args()

    scheduler = Main(args)

    scheduler.run()

    sys.exit(0)
