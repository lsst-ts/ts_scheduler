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

import enum
import logging
import typing

from lsst.ts import observing

from . import driver, feature_scheduler, sequential

__all__ = ["DriverFactory", "DriverType"]


class DriverType(enum.Enum):
    Driver = "driver"
    Sequential = "sequential"
    FeatureScheduler = "feature_scheduler"


class DriverFactory:
    drivers = {
        DriverType.Driver: driver.Driver,
        DriverType.Sequential: sequential.SequentialScheduler,
        DriverType.FeatureScheduler: feature_scheduler.FeatureScheduler,
    }

    @classmethod
    def get_driver(
        cls,
        driver_type: DriverType,
        models: dict[str, typing.Any],
        raw_telemetry: dict[str, typing.Any],
        observing_blocks: dict[str, observing.ObservingBlock],
        parameters: driver.DriverParameters | None = None,
        log: logging.Logger | None = None,
    ) -> driver.Driver:
        return cls.drivers[driver_type](
            models=models,
            raw_telemetry=raw_telemetry,
            observing_blocks=observing_blocks,
            parameters=parameters,
            log=log,
        )
