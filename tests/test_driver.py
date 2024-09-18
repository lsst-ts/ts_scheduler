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
import pathlib
import types
import unittest

from lsst.ts import observing
from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.driver import Driver, SurveyTopology

logging.basicConfig()


class TestSchedulerDriver(unittest.TestCase):
    def setUp(self):
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

        standard_visit_block = observing.ObservingBlock(
            name="StandardVisit",
            program="WFD",
            scripts=[script1, script2],
            constraints=[observing.AirmassConstraint(max=1.5)],
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

        observing_blocks = {
            standard_visit_block.program: standard_visit_block,
            survey_1.program: survey_1,
            survey_2.program: survey_2,
        }

        self.driver = Driver(
            models={}, raw_telemetry={}, observing_blocks=observing_blocks
        )

    def test_configure_scheduler(self):
        survey_topology, config = self.configure_scheduler_for_test()

        assert isinstance(survey_topology, SurveyTopology)
        assert survey_topology.num_general_props == 3
        assert survey_topology.general_propos[0] == "WFD"
        assert survey_topology.general_propos[1] == "Survey1"
        assert survey_topology.general_propos[2] == "Survey2"
        assert len(survey_topology.general_propos) == survey_topology.num_general_props
        assert len(survey_topology.sequence_propos) == survey_topology.num_seq_props

    def test_select_next_target(self):
        target = self.driver.select_next_target()

        assert isinstance(target, Target)
        assert target.num_exp > 0
        assert len(target.exp_times) == target.num_exp

    def test_load(self):
        config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "test_observing_list.yaml")
        )

        bad_config = (
            pathlib.Path(__file__)
            .parents[1]
            .joinpath("tests", "data", "bad_config.yaml")
        )

        self.driver.load(config)

        with self.assertRaises(RuntimeError):
            self.driver.load(bad_config)

    def test_assert_survey_observing_script(self):
        self.driver.assert_survey_observing_script("Survey1")

        with self.assertRaises(AssertionError):
            self.driver.assert_survey_observing_script("Survey3")

    def test_get_survey_observing_script(self):
        observing_block = self.driver.get_survey_observing_block("Survey1")

        assert observing_block.name == "StandardVisit"

    def test_get_stop_tracking_target(self):
        _, config = self.configure_scheduler_for_test()

        stop_tracking_target = self.driver.get_stop_tracking_target()

        assert stop_tracking_target.observing_block.name == "StopTracking"
        assert stop_tracking_target.observing_block.program == ""
        assert (
            stop_tracking_target.observing_block.scripts[0].name
            == config.driver_configuration["stop_tracking_observing_script_name"]
        )
        assert (
            stop_tracking_target.observing_block.scripts[0].standard
            == config.driver_configuration["stop_tracking_observing_script_is_standard"]
        )

    def configure_scheduler_for_test(self, additional_driver_configuration=None):
        config = types.SimpleNamespace(
            driver_configuration=dict(
                general_propos=["WFD", "Survey1", "Survey2"],
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
            )
        )
        if additional_driver_configuration is not None:
            for item in additional_driver_configuration:
                config.driver_configuration[item] = additional_driver_configuration[
                    item
                ]

        return self.driver.configure_scheduler(config), config


if __name__ == "__main__":
    unittest.main()
