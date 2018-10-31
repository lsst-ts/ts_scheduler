import logging
import logging.handlers
import os
import pkg_resources
import time

__all__ = ["EXTENSIVE", "TRACE", "WORDY", "configure_logging", "generate_logfile", "set_log_levels"]

# Extra INFO levels
WORDY = 15
# Extra DEBUG levels
EXTENSIVE = 5
TRACE = 2

DETAIL_LEVEL = {
    0: logging.ERROR,
    1: logging.INFO,
    2: WORDY,
    3: logging.DEBUG,
    4: EXTENSIVE,
    5: TRACE
}

MAX_CONSOLE = 2
MIN_FILE = 3
MAX_FILE = 5

def generate_logfile(basename="scheduler"):
    """Generate a log file name based on current time.
    """
    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_path = pkg_resources.resource_filename(__name__, "../../log")
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    logfilename = os.path.join(log_path, "%s.%s.log" % (basename, timestr))
    return logfilename

def configure_logging(options, logfilename=None, log_port=logging.handlers.DEFAULT_TCP_LOGGING_PORT):
    """Configure the logging for the system.

    Parameters
    ----------
    options : argparse.Namespace
        The options returned by the ArgumentParser instance.argparse.
    logfilename : str
        A name, including path, for a log file.
    log_port : int, optional
        An alternate port for the socket logger.
    """
    console_detail, file_detail = set_log_levels(options.verbose)
    main_level = max(console_detail, file_detail)

    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    if options.console_format is None:
        console_format = log_format
    else:
        console_format = options.console_format

    logging.basicConfig(level=DETAIL_LEVEL[main_level], format=console_format)
    logging.captureWarnings(True)
    # Remove old console logger as it will double up messages when levels match.
    logging.getLogger().removeHandler(logging.getLogger().handlers[0])

    logging.addLevelName(WORDY, 'WORDY')
    logging.addLevelName(EXTENSIVE, 'EXTENSIVE')
    logging.addLevelName(TRACE, 'TRACE')

    ch = logging.StreamHandler()
    ch.setLevel(DETAIL_LEVEL[console_detail])
    ch.setFormatter(logging.Formatter(console_format))
    logging.getLogger().addHandler(ch)

    if options.scripted:
        socket = logging.handlers.SocketHandler('localhost', log_port)
        logging.getLogger().addHandler(socket)

    if not options.scripted:
        log_file = logging.FileHandler(logfilename)
        log_file.setFormatter(logging.Formatter(log_format))
        log_file.setLevel(DETAIL_LEVEL[file_detail])
        logging.getLogger().addHandler(log_file)

def set_log_levels(verbose=0):
    """Set detail levels for console and file logging systems.

    This function sets the detail levels for console and file (via socket) logging systems. These
    levels are keys into the DETAIL_LEVEL dictionary.

    Parameters
    ----------
    verbose : int
        The requested verbosity level.

    Returns
    -------
    (int, int)
        A tuple containing the console detail level and the file detail level respectively.
    """
    console_detail = MAX_CONSOLE if verbose > MAX_CONSOLE else verbose

    file_detail = MIN_FILE if verbose < MIN_FILE else verbose
    file_detail = MAX_FILE if file_detail > MAX_FILE else file_detail

    return (console_detail, file_detail)
