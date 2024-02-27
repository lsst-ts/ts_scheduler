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

__all__ = ["FeatureSchedulerSim", "MJD_START"]

import logging
import types
import typing

from astropy.time import Time
from lsst.ts import observing
from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel, ObservatoryState
from rubin_scheduler.site_models.cloud_model import CloudModel
from rubin_scheduler.site_models.seeing_model import SeeingModel
from rubin_scheduler.utils import survey_start_mjd

from ...driver import FeatureScheduler
from ...driver.feature_scheduler_target import FeatureSchedulerTarget

MJD_START = survey_start_mjd()


class FeatureSchedulerSim:
    """Utility class to simulate observations with the FeatureScheduler.

    This class is used for unit testing.
    """

    def __init__(self, log: logging.Logger) -> None:
        self.log = log.getChild(__name__)

        self.mjd_start = MJD_START

        self.start_time = Time(self.mjd_start, format="mjd", scale="tai")
        # Step in time when there is no target (in seconds).
        self.no_target_time_step = 120.0

        self.raw_telemetry = dict(
            timeHandler=None,
            scheduled_targets=[],
            observing_queue=[],
            observatoryState=None,
            bulkCloud=0.0,
            seeing=1.19,
        )

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
        self.models["sky"].sky_brightness_pre.load_length = 7
        self.models["seeing"] = SeeingModel()
        self.models["cloud"] = CloudModel()

        observing_blocks = self.get_observing_blocks()

        self.driver = FeatureScheduler(
            models=self.models,
            raw_telemetry=self.raw_telemetry,
            observing_blocks=observing_blocks,
            log=log,
        )

        self.config = types.SimpleNamespace(
            driver_configuration=dict(
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
            ),
            feature_scheduler_driver_configuration=dict(
                scheduler_config="",
            ),
        )

        self.files_to_delete = []

    @staticmethod
    def get_observing_blocks() -> dict[str, observing.ObservingBlock]:
        """Generate a observing blocks for testing.

        Returns
        -------
        dict[str, observing.ObservingBlock]
            Observing blocks.
        """

        script1 = observing.ObservingScript(
            name="slew",
            standard=True,
            parameters={
                "name": "$name",
                "ra": "$ra",
                "dec": "$dec",
                "rot_sky": "$rot_sky",
                "estimated_slew_time": "$estimated_slew_time",
                "obs_time": "$obs_time",
                "note": "Static note will be preserved.",
            },
        )
        script2 = observing.ObservingScript(
            name="standard_visit",
            standard=True,
            parameters={
                "exp_times": "$exp_times",
                "band_filter": "$band_filter",
                "program": "$program",
                "note": "Static note will be preserved.",
            },
        )

        script_cwfs = observing.ObservingScript(
            name="cwfs",
            standard=False,
            parameters={
                "find_target": {
                    "az": "$az",
                    "el": "$el",
                    "mag_limit": 8.0,
                },
                "program": "$program",
            },
        )

        standard_visit_block = observing.ObservingBlock(
            name="StandardVisit",
            program="greedy",
            scripts=[script1, script2],
            constraints=[],
        )

        survey_1 = observing.ObservingBlock(
            name="StandardVisit",
            program="Survey1",
            scripts=[script1, script2],
            constraints=[observing.AirmassConstraint(max=1.5)],
        )

        survey_2 = observing.ObservingBlock(
            name="StandardVisit",
            program="Survey2",
            scripts=[script1, script2],
            constraints=[observing.AirmassConstraint(max=1.5)],
        )

        cwfs = observing.ObservingBlock(
            name="CurvatureWavefrontSensing",
            program="cwfs",
            scripts=[script_cwfs],
            constraints=[],
        )

        return {
            cwfs.program: cwfs,
            standard_visit_block.program: standard_visit_block,
            survey_1.program: survey_1,
            survey_2.program: survey_2,
        }

    def make_scheduler_configuration(
        self,
        test_config_dir: str,
        scheduler_config_name: str,
        observation_database_name: typing.Optional[str] = None,
    ) -> None:
        """Make a simple Scheduler configuration.

        Parameters
        ----------
        test_config_dir : `str`
            Directory with the test configuration.
        scheduler_config_name : `str`
            Name of the Scheduler configuration.
        survey_observing_script : `str`, optional
            Name of the survey observing script.
        observation_database_name : `str`, optional
            Name ot the observation database.
        """
        self.config.feature_scheduler_driver_configuration["scheduler_config"] = (
            test_config_dir.parents[1].joinpath("data", "config", scheduler_config_name)
        )

        if observation_database_name is not None:
            self.config.feature_scheduler_driver_configuration[
                "observation_database_name"
            ] = test_config_dir.parents[1].joinpath("data", observation_database_name)

            self.files_to_delete.append(
                self.config.feature_scheduler_driver_configuration[
                    "observation_database_name"
                ]
            )

    def configure_scheduler_for_test(self, test_config_dir: str) -> None:
        """Configure the scheduler for testing using a simple configuration.

        Parameters
        ----------
        test_config_dir : `str`
            Directory with the test configuration.
        """

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good.py",
            observation_database_name="fbs_test_observation_database",
        )

        self.driver.configure_scheduler(self.config)

    def configure_scheduler_for_test_with_cwfs(self, test_config_dir: str) -> None:
        """Configure the scheduler for testing using a configuration that, in
        addition to a simple survey, defines a curvature wavefront sensing
        (cwfs) survey using a custom observation database.

        The feature scheduler threats cwfs surveys slighly different than any
        other surveys, which is why we have a specific test for it.

        Parameters
        ----------
        test_config_dir : `str`
            Directory with the test configuration.

        See Also
        --------
        configure_scheduler_for_test_with_cwfs_standard_obs_database
        """

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good_with_cwfs.py",
            observation_database_name="fbs_test_observation_database_with_cwfs",
        )

        self.log.debug(f"Config: {self.config}")
        self.driver.configure_scheduler(self.config)

    def configure_scheduler_for_test_with_cwfs_standard_obs_database(
        self, test_config_dir: str
    ) -> None:
        """Configure the scheduler for testing using a configuration that, in
        addition to a simple survey, defines a curvature wavefront sensing
        (cwfs) survey and uses a standard observation database.


        Parameters
        ----------
        test_config_dir : `str`
            Directory with the test configuration.

        See Also
        --------
        configure_scheduler_for_test_with_cwfs
        """

        self.make_scheduler_configuration(
            test_config_dir=test_config_dir,
            scheduler_config_name="fbs_config_good_with_cwfs.py",
        )

        self.log.debug(f"Config: {self.config}")
        self.driver.configure_scheduler(self.config)

    def run_observations(
        self, register_observations: bool
    ) -> typing.List[FeatureSchedulerTarget]:
        """Run observations.

        This method performs a small simulation of an observing night and
        returns the targets produced by the scheduler.

        Parameters
        ----------
        register_observations : `bool`
            Should the observations be registered? This mean they will be
            written to a sqlite database.

        Returns
        -------
        targets : `typing.List[FeatureSchedulerTarget]`
            List of targets.
        """

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
