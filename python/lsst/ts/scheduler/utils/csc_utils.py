# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = [
    "NonFinalStates",
    "FailedStates",
    "block_regex",
    "SchedulerModes",
    "is_uri",
    "OBSERVATION_NAMED_PARAMETERS",
    "set_detailed_state",
    "BlockStatus",
]

import enum
import re
from urllib.parse import urlparse

from lsst.ts.xml.enums import Script

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
    )
)
"""Stores all non final state for scripts submitted to the queue.
"""

FailedStates = frozenset(
    (
        Script.ScriptState.STOPPED,
        Script.ScriptState.FAILED,
        Script.ScriptState.CONFIGURE_FAILED,
    )
)

efd_query_re = re.compile(r"SELECT (.*) FROM (.*) WHERE (.*)")

block_regex = re.compile(
    r"(?P<block_test_case>BLOCK-T)?(?P<block>BLOCK-)?(?P<id>[0-9]*)"
)

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


class BlockStatus(enum.IntEnum):
    """Observing block status.

    This enumeration is added here temporarily to support publishing this
    information with the current version of ts-idl. Once the new version of
    ts-idl package is released and deployed this can be removed.
    """

    # Block is invalid.
    INVALID = enum.auto()
    # Block is available.
    AVAILABLE = enum.auto()
    # Block started executing but did not completed yet.
    STARTED = enum.auto()
    # Block is currently executing.
    EXECUTING = enum.auto()
    # Block completed.
    COMPLETED = enum.auto()
    # Error while executing block.
    ERROR = enum.auto()
    # Block was interrupted.
    INTERRUPTED = enum.auto()


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


def set_detailed_state(detailed_state):
    """A class decorator for coroutine to facilitate setting/resetting
    detailed state.

    Parameters
    ----------
    detailed_state : `DetailedState`
        Detailed state to switch to before awaiting the coroutine.

    Notes
    -----
    When decorating a coroutine with `set_detailed_state`, you specify the
    associated detailed state and it will wrap the call with
    `async with detailed_state` context manager, causing it to switch to
    the provided detailed state before awaiting the coroutine and switching
    back to the previous detailed state when it is done.

    The `detailed_state` context manager will acquire a lock when setting
    the detailed state. The idea is that you can only execute one detailed
    state at a time so beware not to call a method that changes the
    detailed state from a another, to avoid dead locks.
    """

    def decorator(coroutine):
        async def detailed_state_wrapper(self, *args, **kwargs):
            async with self.detailed_state(detailed_state):
                await coroutine(self, *args, **kwargs)

        return detailed_state_wrapper

    return decorator
