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

__all__ = ["NonFinalStates", "SchedulerModes"]

import enum

from lsst.ts.idl.enums import Script


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


class SchedulerModes(enum.IntEnum):
    NORMAL = 0
    MOCKS3 = enum.auto()
    SIMULATION = enum.auto()
