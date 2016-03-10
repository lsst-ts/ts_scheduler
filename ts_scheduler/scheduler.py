#!/usr/bin/env python

import argparse
import logging
import pkg_resources
import os
import sys
import time

from schedulerDefinitions import INFOX
from schedulerMain import Main

DETAIL_LEVEL = {
    0: logging.WARN,
    1: logging.INFO,
    2: INFOX,
    3: logging.DEBUG
}

MAX_LEVEL = 3

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

    console_detail_level = args.verbose if args.scripted else args.verbose + 2

    log_level = DETAIL_LEVEL[console_detail_level]

    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    if args.console_format is None:
        console_format = log_format
    else:
        console_format = args.console_format

    logging.basicConfig(level=DETAIL_LEVEL[MAX_LEVEL], format=console_format)
    # Remove old console logger as it will double up messages when levels match.
    logging.getLogger().removeHandler(logging.getLogger().handlers[0])

    logging.INFOX = INFOX
    logging.addLevelName(logging.INFOX, 'INFOX')

    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(logging.Formatter(console_format))
    logging.getLogger().addHandler(ch)

    if args.scripted:
        socket = logging.handlers.SocketHandler('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        logging.getLogger().addHandler(socket)

    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_path = pkg_resources.resource_filename(__name__, "../log")
    logfilename = os.path.join(log_path, "scheduler.%s.log" % (timestr))

    if not args.scripted:
        logFile = logging.FileHandler(logfilename)
        logFile.setFormatter(log_format)
        logFile.setLevel(DETAIL_LEVEL[3])
        logging.getLogger().addHandler(logFile)

    logger = logging.getLogger("scheduler")
    logger.log(INFOX, "Configure logFile=%s" % logfilename)

    scheduler = Main(args)
    scheduler.run()

    sys.exit(0)
