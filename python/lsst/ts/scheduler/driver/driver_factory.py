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
