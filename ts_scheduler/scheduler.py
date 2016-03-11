#!/usr/bin/env python

import logging
import sys

from schedulerDefinitions import INFOX
from schedulerMain import Main
from ts_scheduler.setup import configure_logging, create_parser, generate_logfile

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    logfilename = generate_logfile()
    configure_logging(args, logfilename)

    logger = logging.getLogger("scheduler")
    logger.log(INFOX, "Configure logFile=%s" % logfilename)

    scheduler = Main(args)
    scheduler.run()

    sys.exit(0)
