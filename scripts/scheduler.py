#!/usr/bin/env python

import asyncio
import logging
import sys

from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.setup import configure_logging, create_parser, generate_logfile

def main(args):
    logfilename = generate_logfile()
    configure_logging(args, logfilename, args.log_port)

    logger = logging.getLogger("scheduler")
    logger.info("logfile=%s" % logfilename)

    csc = SchedulerCSC(args.index)

    loop = asyncio.get_event_loop()

    try:
        logger.info('Running CSC (Control+C to stop it)...')
        loop.run_until_complete(csc.done_task)
    except KeyboardInterrupt as e:
        logger.info('Stopping %s CSC.', args.subsystem_tag)
    finally:
        loop.close()


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    if args.profile:
        import cProfile
        from datetime import datetime
        cProfile.run("main(args)",
                     "scheduler_prof_{}.dat".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S")))
    else:
        main(args)
