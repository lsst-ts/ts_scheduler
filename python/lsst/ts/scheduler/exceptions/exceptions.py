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
    "UnableToFindTargetError",
    "UpdateTelemetryError",
    "FailedToQueueTargetsError",
    "TargetScriptFailedError",
    "NonConsecutiveIndexError",
    "InvalidStatusError",
    "UpdateStatusError",
]


class UnableToFindTargetError(Exception):
    """Raised when the Scheduler CSC requests a target and does not receive
    anything.
    """

    pass


class UpdateTelemetryError(Exception):
    """Raised when the Scheduler CSC fails to update telemetry."""

    pass


class FailedToQueueTargetsError(Exception):
    """Raised when the Scheduler CSC fails to add targets to the queue."""

    pass


class TargetScriptFailedError(Exception):
    """Raised when the Scheduler CSC is fails to add a script for a block to
    the queue.
    """

    pass


class NonConsecutiveIndexError(Exception):
    """Raised by the Scheduler CSC when it is adding scripts of a block and
    their index is not sequential.
    """

    pass


class InvalidStatusError(Exception):
    pass


class UpdateStatusError(Exception):
    pass
