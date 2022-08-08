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

import logging
import os
import pathlib
import unittest

import pytest
from numpy import isscalar

from lsst.ts.scheduler.driver import NoNsideError, NoSchedulerError, SurveyTopology
from lsst.ts.scheduler.utils.test.feature_scheduler_sim import FeatureSchedulerSim

logging.basicConfig()


class TestFeatureSchedulerDriver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestFeatureSchedulerDriver")
        return super().setUpClass()

    def setUp(self) -> None:
        self.feature_scheduler_sim = FeatureSchedulerSim(self.log)

        self.files_to_delete = []

    @property
    def driver(self):
        return self.feature_scheduler_sim.driver

    @property
    def start_time(self):
        return self.feature_scheduler_sim.start_time

    @property
    def raw_telemetry(self):
        return self.feature_scheduler_sim.raw_telemetry

    @property
    def models(self):
        return self.feature_scheduler_sim.models

    @property
    def config(self):
        return self.feature_scheduler_sim.config

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

        targets = self.run_observations(register_observations=True)

        registered_targets = self.driver.schema_converter.opsim2obs(
            filename=self.driver.observation_database_name,
        )

        self.assertGreater(len(targets), 0)
        self.assertEqual(len(targets), len(registered_targets))

        for observed_target, registered_target in zip(targets, registered_targets):
            observed_ra, observed_dec, observed_note = (
                observed_target.observation["RA"][0],
                observed_target.observation["dec"][0],
                observed_target.observation["note"][0],
            )
            target_ra, target_dec, target_note = (
                registered_target["RA"],
                registered_target["dec"],
                registered_target["note"],
            )
            self.assertAlmostEqual(observed_ra, target_ra)
            self.assertAlmostEqual(observed_dec, target_dec)
            self.assertEqual(observed_note, target_note)

    def test_select_next_target_with_cwfs(self):

        self.configure_scheduler_for_test_with_cwfs()

        self.driver.assert_survey_observing_script("cwfs")

        targets = self.run_observations(register_observations=True)

        self.assertGreater(len(targets), 0)

        number_of_cwfs_targets = len(
            [target for target in targets if target.observation["note"][0] == "cwfs"]
        )

        registered_targets = self.driver.schema_converter.opsim2obs(
            filename=self.driver.observation_database_name,
        )

        self.assertGreaterEqual(number_of_cwfs_targets, 2)
        self.assertGreater(len(targets), number_of_cwfs_targets)

        for observed_target, registered_target in zip(targets, registered_targets):
            observed_ra, observed_dec, observed_note = (
                observed_target.observation["RA"][0],
                observed_target.observation["dec"][0],
                observed_target.observation["note"][0],
            )
            target_ra, target_dec, target_note = (
                registered_target["RA"],
                registered_target["dec"],
                registered_target["note"],
            )
            self.assertAlmostEqual(observed_ra, target_ra)
            self.assertAlmostEqual(observed_dec, target_dec)
            self.assertEqual(observed_note, target_note)

    def test_save_and_reset_from_file(self):

        self.configure_scheduler_for_test()

        # Save state of the scheduler
        filename = self.driver.save_state()

        self.files_to_delete.append(filename)

        # Run some observations
        targets_run_1 = self.run_observations(register_observations=False)

        self.driver.reset_from_state(filename)

        self.models["observatory_model"].reset()
        self.models["observatory_model"].update_state(self.start_time.unix)
        self.models["observatory_state"].set(
            self.models["observatory_model"].current_state
        )

        targets_run_2 = self.run_observations(register_observations=False)

        # Targets 1 and 2 should be equal
        self.assertEqual(len(targets_run_1), len(targets_run_2))

        for target_1, target_2 in zip(targets_run_1, targets_run_2):
            with self.subTest(target_1=target_1, target_2=target_2):
                self.assertEqual(f"{target_1}", f"{target_2}")

    def test_parse_observation_database(self):

        self.configure_scheduler_for_test()
        # self.files_to_delete.append(self.driver.observation_database_name)

        # Run some observations
        targets_run_1 = self.run_observations(register_observations=True)

        observations = self.driver.parse_observation_database(
            self.driver.observation_database_name
        )

        assert len(targets_run_1) == len(observations)

        for target, observation in zip(targets_run_1, observations):
            for item in [
                "RA",
                "dec",
                "mjd",
                "exptime",
                "filter",
                "rotSkyPos",
                "nexp",
                "airmass",
            ]:
                if isscalar(target.observation[item][0]):
                    assert target.observation[item][0] == pytest.approx(
                        observation.observation[item][0]
                    )
                else:
                    assert (
                        target.observation[item][0] == observation.observation[item][0]
                    )

    def configure_scheduler_for_test(self):

        self.config.driver_configuration["scheduler_config"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "config", "fbs_config_good.py")
        )

        self.config.driver_configuration["observation_database_name"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "fbs_test_observation_database")
        )

        self.files_to_delete.append(
            self.config.driver_configuration["observation_database_name"]
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

        self.config.driver_configuration["observation_database_name"] = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "fbs_test_observation_database_with_cwfs")
        )

        self.files_to_delete.append(
            self.config.driver_configuration["observation_database_name"]
        )

        self.driver.configure_scheduler(self.config)

    def run_observations(self, register_observations):

        return self.feature_scheduler_sim.run_observations(
            register_observations=register_observations
        )

    def tearDown(self):
        for filename in self.files_to_delete:
            if os.path.exists(filename):
                self.log.debug(f"Deleting: {filename}")
                os.remove(filename)
            else:
                self.log.warning(f"File not found: {filename}")


if __name__ == "__main__":
    unittest.main()
