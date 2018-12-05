import argparse
import logging.handlers

from lsst.ts.scheduler import __version__

__all__ = ["create_parser"]

def create_parser():
    """Create the argument parser for the main driver script.
    """
    description = ["This is the main driver script for the LSST Scheduler."]

    parser = argparse.ArgumentParser(usage="scheduler.py [options]",
                                     description=" ".join(description),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-s", "--scripted", dest="scripted", action="store_true",
                        help="Flag to run the Scheduler code from another script.")
    parser.add_argument("-v", "--verbose", dest="verbose", action='count', default=0,
                        help="Set the verbosity for the console logging.")
    parser.add_argument("-c", "--console-format", dest="console_format", default=None,
                        help="Override the console format.")
    parser.add_argument("--profile", dest="profile", action="store_true", help="Run the profiler on Scheduler"
                        "code.")
    parser.add_argument("--log-port", dest="log_port", default=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                        type=int, help="Specify the logging port for the Scheduler.")
    parser.add_argument("-t", "--timeout", dest="timeout", default=60.0, type=float,
                        help="Specify the timeout for the DDS messaging checks.")
    parser.add_argument("-p", "--path_config", dest="path", default=None, type=str,
                        help="Specify the path to the configuration directory.")
    parser.add_argument("--index", dest="index", default=1, type=int,
                        help="The Scheduler SAL index. This parameter basically defines which telescope the scheduler"
                             "will be controlling, by matching the index of the scheduler and the queue.")

    return parser
