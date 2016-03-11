import logging
import os
import pkg_resources
import time

from ts_scheduler.schedulerDefinitions import INFOX

__all__ = ["configure_logging", "generate_logfile"]

DETAIL_LEVEL = {
    0: logging.WARN,
    1: logging.INFO,
    2: INFOX,
    3: logging.DEBUG
}

MAX_LEVEL = 3

def generate_logfile():
    """Generate a log file name based on current time.
    """
    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_path = pkg_resources.resource_filename(__name__, "../../log")
    logfilename = os.path.join(log_path, "scheduler.%s.log" % (timestr))
    return logfilename

def configure_logging(options, logfilename=None):
    """Configure the logging for the system.

    Parameters
    ----------
    options : argparse.Namespace
        The options returned by the ArgumentParser instance.argparse.
    logfilename : str
        A name, including path, for a log file.
    """
    console_detail_level = options.verbose if options.scripted else options.verbose + 2

    log_level = DETAIL_LEVEL[console_detail_level]

    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    if options.console_format is None:
        console_format = log_format
    else:
        console_format = options.console_format

    logging.basicConfig(level=DETAIL_LEVEL[MAX_LEVEL], format=console_format)
    # Remove old console logger as it will double up messages when levels match.
    logging.getLogger().removeHandler(logging.getLogger().handlers[0])

    logging.INFOX = INFOX
    logging.addLevelName(logging.INFOX, 'INFOX')

    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(logging.Formatter(console_format))
    logging.getLogger().addHandler(ch)

    if options.scripted:
        socket = logging.handlers.SocketHandler('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        logging.getLogger().addHandler(socket)

    if not options.scripted:
        logFile = logging.FileHandler(logfilename)
        logFile.setFormatter(log_format)
        logFile.setLevel(DETAIL_LEVEL[3])
        logging.getLogger().addHandler(logFile)
