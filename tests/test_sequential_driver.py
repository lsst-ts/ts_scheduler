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

from lsst.ts.utils import current_tai

from lsst.ts.scheduler.driver import SequentialScheduler, SurveyTopology
from lsst.ts.observatory.model import Target
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState

from lsst.ts.dateloc import ObservatoryLocation

from lsst.ts.astrosky.model import AstronomicalSkyModel

from rubin_sim.site_models.seeingModel import SeeingModel
from rubin_sim.site_models.cloudModel import CloudModel
from rubin_sim.site_models.downtimeModel import DowntimeModel

logging.basicConfig()


class TestSchedulerDriver(unittest.TestCase):
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
        self.models["downtime"] = DowntimeModel()

        self.driver = SequentialScheduler(
            models=self.models,
            raw_telemetry=self.raw_telemetry,
        )

        self.config = types.SimpleNamespace(
            driver_configuration=dict(
                observing_list=pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "test_observing_list.yaml"),
                general_propos=["Test"],
                default_observing_script_name="standard_visit.py",
                default_observing_script_is_standard=True,
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
            )
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

            print(target)

            if target is None:
                break
            else:
                with self.subTest(msg="Request target {n_targets}."):
                    self.assertIsInstance(target, Target)
                    self.assertGreater(target.num_exp, 0)
                    self.assertEqual(len(target.exp_times), target.num_exp)
                    self.assertGreater(target.slewtime, 0.0)
                n_targets += 1

            self.models["observatory_model"].observe(target)
            self.models["observatory_state"].set(
                self.models["observatory_model"].current_state
            )

        return n_targets

    def tearDown(self):
        for filename in self.files_to_delete:
            os.remove(filename)


if __name__ == "__main__":
    unittest.main()
