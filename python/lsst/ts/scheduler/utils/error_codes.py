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
    "NO_QUEUE",
    "PUT_ON_QUEUE",
    "UPDATE_TELEMETRY_ERROR",
    "SIMPLE_LOOP_ERROR",
    "ADVANCE_LOOP_ERROR",
    "UNABLE_TO_FIND_TARGET",
    "OBSERVATORY_STATE_UPDATE",
]


NO_QUEUE = 300
PUT_ON_QUEUE = 301
UPDATE_TELEMETRY_ERROR = 302
SIMPLE_LOOP_ERROR = 400
ADVANCE_LOOP_ERROR = 401
UNABLE_TO_FIND_TARGET = 402
OBSERVATORY_STATE_UPDATE = 500
