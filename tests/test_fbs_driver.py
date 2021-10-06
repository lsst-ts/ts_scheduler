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

import os
import types
import pathlib
import unittest
import logging

from astropy.time import Time

from lsst.ts.scheduler.driver import (
    FeatureScheduler,
    SurveyTopology,
    NoNsideError,
    NoSchedulerError,
)

from lsst.ts.observatory.model import Target
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState

from lsst.ts.dateloc import ObservatoryLocation

from lsst.ts.astrosky.model import AstronomicalSkyModel

from rubin_sim.site_models.seeingModel import SeeingModel
from rubin_sim.site_models.cloudModel import CloudModel
from rubin_sim.site_models.downtimeModel import DowntimeModel

logging.basicConfig()


class TestFeatureSchedulerDriver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestFeatureSchedulerDriver")
        return super().setUpClass()

    def setUp(self):
        # Need to set current time to something the sky brightness files
        # available for testing have available (MJD: 59853.-59856.).
        self.start_time = Time(59853.983, format="mjd", scale="tai")

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
            )
        )

        self.files_to_delete = []

    def test_configure_scheduler(self):

        self.config.driver_configuration["scheduler_config"] = "no_file.py"

        with self.assertRaises(RuntimeError):
            survey_topology = self.driver.configure_scheduler(self.config)

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_no_nside.py")
        )

        with self.assertRaises(NoNsideError):
            survey_topology = self.driver.configure_scheduler(self.config)

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_no_scheduler.py")
        )

        with self.assertRaises(NoSchedulerError):
            survey_topology = self.driver.configure_scheduler(self.config)

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_good.py")
        )

        survey_topology = self.driver.configure_scheduler(self.config)

        for i, survey_name in enumerate(survey_topology.general_propos):
            with self.subTest(survey_name=survey_name):
                self.assertEqual(
                    survey_name, self.driver.scheduler.survey_lists[0][i].survey_name
                )

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props != 0
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

    def test_select_next_target(self):

        self.configure_scheduler_for_test()

        # Calling select_next_target without calling update_conditions first
        # should raise a RuntimeError exception.
        with self.assertRaises(RuntimeError):
            self.driver.select_next_target()

        targets = self.run_observations()

        self.assertGreater(len(targets), 0)

    def test_select_next_target_with_cwfs(self):

        self.configure_scheduler_for_test_with_cwfs()

        self.driver.assert_survey_observing_script("cwfs")

        targets = self.run_observations()

        self.assertGreater(len(targets), 0)

        number_of_cwfs_targets = len(
            [target for target in targets if target.observation["note"][0] == "cwfs"]
        )

        self.assertGreaterEqual(number_of_cwfs_targets, 2)
        self.assertGreater(len(targets), number_of_cwfs_targets)

    @unittest.skip("Not implemented yet.")
    def test_load(self):
        pass

    def test_save_and_reset_from_file(self):

        self.configure_scheduler_for_test()

        # Save state of the scheduler
        filename = self.driver.save_state()

        self.files_to_delete.append(filename)

        # Run some observations
        targets_run_1 = self.run_observations()

        self.driver.reset_from_state(filename)

        self.models["observatory_model"].reset()
        self.models["observatory_model"].update_state(self.start_time.unix)
        self.models["observatory_state"].set(
            self.models["observatory_model"].current_state
        )

        targets_run_2 = self.run_observations()

        # Targets 1 and 2 should be equal
        self.assertEqual(len(targets_run_1), len(targets_run_2))

        for target_1, target_2 in zip(targets_run_1, targets_run_2):
            with self.subTest(target_1=target_1, target_2=target_2):
                self.assertEqual(f"{target_1}", f"{target_2}")

    def configure_scheduler_for_test(self):

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_good.py")
        )

        self.driver.configure_scheduler(self.config)

    def configure_scheduler_for_test_with_cwfs(self):

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_good_with_cwfs.py")
        )
        self.config.driver_configuration["survey_observing_script"] = dict(
            cwfs=dict(
                observing_script_name="cwfs_script",
                observing_script_is_standard=False,
            ),
        )

        self.driver.configure_scheduler(self.config)

    def run_observations(self):

        targets = []

        while len(targets) < 10:

            self.driver.update_conditions()

            target = self.driver.select_next_target()

            self.log.debug(f"[{len(targets)}]::{target.observation}")

            if target is None:
                break
            else:
                with self.subTest(msg="Request target {n_targets}."):
                    self.assertIsInstance(target, Target, "Wrong target type.")
                    self.assertGreater(
                        target.num_exp,
                        0,
                        "Number of exposures should be greater than zero.",
                    )
                    self.assertEqual(
                        len(target.exp_times),
                        target.num_exp,
                        "Size of exposure times table should be equal to number of exposures.",
                    )
                    self.assertGreater(
                        target.slewtime,
                        0.0,
                        f"Slewtime must be larger then zero. {target.observation}",
                    )

                self.driver.register_observation([target])
                self.models["observatory_model"].observe(target)
                self.models["observatory_state"].set(
                    self.models["observatory_model"].current_state
                )

                targets.append(target)

        return targets

    def tearDown(self):
        for filename in self.files_to_delete:
            os.remove(filename)


if __name__ == "__main__":
    unittest.main()
