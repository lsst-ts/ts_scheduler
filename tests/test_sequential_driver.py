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
import types
import unittest

from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel, ObservatoryState
from lsst.ts.scheduler.driver import SequentialScheduler, SurveyTopology
from lsst.ts.scheduler.utils.test import FeatureSchedulerSim
from lsst.ts.utils import current_tai
from rubin_sim.site_models.cloud_model import CloudModel
from rubin_sim.site_models.seeing_model import SeeingModel


class TestSequentialScheduler(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestSequentialScheduler")
        return super().setUpClass()

    def setUp(self):
        self.raw_telemetry = dict()

        self.raw_telemetry["timeHandler"] = None
        self.raw_telemetry["scheduled_targets"] = []
        self.raw_telemetry["observing_queue"] = []
        self.raw_telemetry["observatoryState"] = None
        self.raw_telemetry["bulkCloud"] = 0.0
        self.raw_telemetry["seeing"] = 1.0

        self.models = dict()

        self.models["location"] = ObservatoryLocation()
        self.models["location"].for_lsst()

        self.models["observatory_model"] = ObservatoryModel(self.models["location"])
        self.models["observatory_model"].configure_from_module()

        self.models["observatory_model"].update_state(current_tai())

        self.models["observatory_state"] = ObservatoryState()
        self.models["observatory_state"].set(
            self.models["observatory_model"].current_state
        )

        self.models["sky"] = AstronomicalSkyModel(self.models["location"])
        self.models["sky"].sky_brightness_pre.load_length = 7
        self.models["seeing"] = SeeingModel()
        self.models["cloud"] = CloudModel()

        self.driver = SequentialScheduler(
            models=self.models,
            raw_telemetry=self.raw_telemetry,
            observing_blocks=FeatureSchedulerSim.get_observing_blocks(),
            log=self.log,
        )

        self.config = types.SimpleNamespace(
            sequential_driver_configuration=dict(
                observing_list=pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "test_observing_list.yaml"),
            ),
            driver_configuration=dict(
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
                general_propos=["Test"],
            ),
        )

        self.files_to_delete = []

    def test_configure_scheduler(self):
        survey_topology = self.driver.configure_scheduler(self.config)

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props != 0
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

    def test_select_next_target(self):
        self.driver.configure_scheduler(self.config)

        n_targets = self.run_observations()

        self.assertGreater(n_targets, 0)

    def test_load(self):
        config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "test_observing_list.yaml")
        )

        self.driver.load(config)

    def test_save_and_reset_from_file(self):
        self.driver.configure_scheduler(self.config)

        # Store copy of the state dictionary
        state = self.driver.observing_list_dict.copy()

        # Save state of the scheduler
        filename = self.driver.save_state()

        self.files_to_delete.append(filename)

        # Run some observations
        self.run_observations()

        self.assertNotEqual(self.driver.observing_list_dict, state)

        self.driver.reset_from_state(filename)

        self.assertEqual(self.driver.observing_list_dict, state)

    def run_observations(self):
        n_targets = 0

        while True:
            self.driver.update_conditions()

            target = self.driver.select_next_target()

            if target is None:
                self.log.debug("No target from driver. Stopping...")
                break
            else:
                self.models["observatory_model"].observe(target)
                self.models["observatory_state"].set(
                    self.models["observatory_model"].current_state
                )
                self.log.debug(f"Target[{n_targets}]: {target}")
                n_targets += 1

        return n_targets

    def tearDown(self):
        for filename in self.files_to_delete:
            os.remove(filename)


if __name__ == "__main__":
    unittest.main()
