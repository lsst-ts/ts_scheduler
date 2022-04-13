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

__all__ = ["FeatureSchedulerSim"]

import logging
import types

from astropy.time import Time

from lsst.ts.scheduler.driver import FeatureScheduler

from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState

from lsst.ts.dateloc import ObservatoryLocation

from lsst.ts.astrosky.model import AstronomicalSkyModel

from rubin_sim.site_models.seeingModel import SeeingModel
from rubin_sim.site_models.cloudModel import CloudModel
from rubin_sim.site_models.downtimeModel import DowntimeModel


class FeatureSchedulerSim:
    """Utility class to simulate observations with the FeatureScheduler.

    This class is used mostly for unit testing.
    """

    def __init__(self, log: logging.Logger) -> None:

        self.log = log.getChild(__name__)

        self.start_time = Time(59853.983, format="mjd", scale="tai")
        # Step in time when there is no target (in seconds).
        self.no_target_time_step = 120.0

        self.raw_telemetry = dict()

        self.raw_telemetry["timeHandler"] = None
        self.raw_telemetry["scheduled_targets"] = []
        self.raw_telemetry["observing_queue"] = []
        self.raw_telemetry["observatoryState"] = None
        self.raw_telemetry["bulkCloud"] = 0.0
        self.raw_telemetry["seeing"] = 1.19

        self.models = dict()

        self.models["location"] = ObservatoryLocation()
        self.models["location"].for_lsst()

        self.models["observatory_model"] = ObservatoryModel(self.models["location"])
        self.models["observatory_model"].configure_from_module()

        self.models["observatory_model"].update_state(self.start_time.unix)

        self.models["observatory_state"] = ObservatoryState()
        self.models["observatory_state"].set(
            self.models["observatory_model"].current_state
        )

        self.models["sky"] = AstronomicalSkyModel(self.models["location"])
        self.models["seeing"] = SeeingModel()
        self.models["cloud"] = CloudModel()
        self.models["downtime"] = DowntimeModel()

        self.driver = FeatureScheduler(
            models=self.models, raw_telemetry=self.raw_telemetry
        )

        self.config = types.SimpleNamespace(
            driver_configuration=dict(
                scheduler_config="",
                force=True,
                default_observing_script_name="standard_visit.py",
                default_observing_script_is_standard=True,
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
            )
        )

        self.files_to_delete = []

    def make_scheduler_configuration(
        self,
        test_config_dir,
        scheduler_config_name,
        survey_observing_script=None,
        observation_database_name=None,
    ):
        self.config.driver_configuration["scheduler_config"] = test_config_dir.parents[
            1
        ].joinpath("data", "config", scheduler_config_name)

        if survey_observing_script is not None:
            self.config.driver_configuration[
                "survey_observing_script"
            ] = survey_observing_script

        if observation_database_name is not None:
            self.config.driver_configuration[
                "observation_database_name"
            ] = test_config_dir.parents[1].joinpath("data", observation_database_name)

            self.files_to_delete.append(
                self.config.driver_configuration["observation_database_name"]
            )

    def configure_scheduler_for_test(self, test_config_dir):

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good.py",
            observation_database_name="fbs_test_observation_database",
        )

        self.driver.configure_scheduler(self.config)

    def configure_scheduler_for_test_with_cwfs(self, test_config_dir):

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good_with_cwfs.py",
            survey_observing_script=dict(
                cwfs=dict(
                    observing_script_name="cwfs_script",
                    observing_script_is_standard=False,
                ),
            ),
            observation_database_name="fbs_test_observation_database_with_cwfs",
        )

        self.log.debug(f"Config: {self.config}")
        self.driver.configure_scheduler(self.config)

    def configure_scheduler_for_test_with_cwfs_standard_obs_database(
        self, test_config_dir
    ):

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good_with_cwfs.py",
            survey_observing_script=dict(
                cwfs=dict(
                    observing_script_name="cwfs_script",
                    observing_script_is_standard=False,
                ),
            ),
        )

        self.log.debug(f"Config: {self.config}")
        self.driver.configure_scheduler(self.config)

    def run_observations(self, register_observations):

        targets = []

        self.driver.update_conditions()
        current_time = self.driver.current_sunset
        sunset_time = self.driver.current_sunset
        sunrise_time = self.driver.current_sunrise
        self.models["observatory_model"].update_state(current_time)

        while current_time < sunrise_time:

            self.log.debug(
                f"current_time: {current_time}, sunset: {sunset_time}, sunrise: {sunrise_time}."
            )

            self.driver.update_conditions()

            target = self.driver.select_next_target()

            if target is None:
                self.log.debug("No target produced by scheduler.")
                current_time += self.no_target_time_step
                self.models["observatory_model"].update_state(current_time)
                self.models["observatory_state"].set(
                    self.models["observatory_model"].current_state
                )
                self.driver.update_conditions()
            else:

                self.log.debug(f"[{len(targets)}]::{target}")

                self.models["observatory_model"].observe(target)
                self.models["observatory_state"].set(
                    self.models["observatory_model"].current_state
                )
                current_time = self.models["observatory_state"].time
                self.driver.register_observed_target(target)
                targets.append(target)

            if len(targets) > 10:
                break

        if register_observations:
            for target in targets:
                self.driver.register_observation(target)
        return targets
