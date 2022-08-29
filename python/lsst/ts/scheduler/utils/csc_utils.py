# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

__all__ = [
    "NonFinalStates",
    "SchedulerModes",
    "is_uri",
    "support_command",
    "OBSERVATION_NAMED_PARAMETERS",
]

import enum
import re
from urllib.parse import urlparse

from lsst.ts.idl import get_idl_dir
from lsst.ts.idl.enums import Script
from lsst.ts.salobj import parse_idl

NonFinalStates = frozenset(
    (
        Script.ScriptState.UNKNOWN,
        Script.ScriptState.UNCONFIGURED,
        Script.ScriptState.CONFIGURED,
        Script.ScriptState.RUNNING,
        Script.ScriptState.PAUSED,
        Script.ScriptState.ENDING,
        Script.ScriptState.STOPPING,
        Script.ScriptState.FAILING,
        Script.ScriptState.STOPPED,
    )
)
"""Stores all non final state for scripts submitted to the queue.
"""

efd_query_re = re.compile(r"SELECT (.*) FROM (.*) WHERE (.*)")

OBSERVATION_NAMED_PARAMETERS = [
    "targetId",
    "ra",
    "decl",
    "mjd",
    "exptime",
    "filter",
    "rotSkyPos",
    "nexp",
]


class SchedulerModes(enum.IntEnum):
    NORMAL = 0
    MOCKS3 = enum.auto()
    SIMULATION = enum.auto()


# TODO (DM-36037): Remove DetailedState enumeration from Scheduler once ts-idl
# is released.
class DetailedState(enum.IntEnum):
    """Detailed state enumeration for the Scheduler.

    This enumeration is added here temporarily to support publishing this
    information with the current version of ts-idl. Once the new version of
    ts-idl package is released and deployed this can be removed.
    """

    # Scheduler is idle. This will be the detailed state when the Scheduler is
    # not in ENABLED state or is in enabled but not running.
    IDLE = enum.auto()
    # Scheduler is running but not doing anything in particular.
    RUNNING = enum.auto()
    # Scheduler is running and waiting for the "next_target_timer_task" to
    # finish. This condition happens when there is no target to observe, the
    # scheduler estimates how long until there is a target to observe and
    # create a timer to wait for.
    WAITING_NEXT_TARGET_TIMER_TASK = enum.auto()
    # Scheduler is generating the target queue. This consists of processing the
    # telemetry data to produce the targets to observe.
    GENERATING_TARGET_QUEUE = enum.auto()
    # Scheduler is computing the predicted queue.
    COMPUTING_PREDICTED_SCHEDULE = enum.auto()
    # Scheduler is queueing targets.
    QUEUEING_TARGET = enum.auto()


def is_uri(uri: str) -> bool:
    """Check if input is a valid uri.

    Parameters
    ----------
    uri : str
        String to check if it is a valid uri.

    Returns
    -------
    bool
        True if uri is valid.
    """

    parse_result = urlparse(uri)

    return len(parse_result.scheme) > 0 and len(parse_result.path) > 0


def is_valid_efd_query(entry: str) -> bool:
    """Verify if input information is a valid EFD query.

    Parameters
    ----------
    entry : str
        String to check if it is a valid EFD query.

    Returns
    -------
    bool
        True if it is a valid EFD query.
    """
    return efd_query_re.match(entry) is not None


def support_command(command_name: str) -> bool:
    """Check if the CSC supports a particular command.

    This is used to provide backward compatibility for new commands being added
    to the CSC.

    Returns
    -------
    `bool`
        True if the CSC interface defines the command, False
        otherwise.
    """
    idl_metadata = parse_idl("Scheduler", get_idl_dir() / "sal_revCoded_Scheduler.idl")

    return f"command_{command_name}" in idl_metadata.topic_info
