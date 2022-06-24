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

import yaml
import math
import unittest

import numpy as np

from astropy.coordinates import Angle
from astropy.time import Time
from astropy import units

from rubin_sim.scheduler.utils import empty_observation

from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.scheduler.driver.feature_scheduler_target import FeatureSchedulerTarget


class TestFeatureSchedulerTarget(unittest.TestCase):
    def setUp(self) -> None:

        self.observatory_model = ObservatoryModel()
        self.observatory_model.configure_from_module()

        start_time = Time(60110.983, format="mjd", scale="tai")

        self.observatory_model.update_state(start_time.unix)

        return super().setUp()

    def test_constructor(self):

        observation = self.make_fbs_observation(note="std")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
        )

        slew_time, error = self.observatory_model.get_slew_delay(target)

        self.assertEqual(error, 0)
        self.assertGreater(slew_time, 0.0)

    def test_get_script_config(self):

        observation = self.make_fbs_observation(note="std")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
        )

        script_config_expected = {
            "targetid": target.targetid,
            "band_filter": target.filter,
            "ra": Angle(float(observation["RA"][0]), unit=units.rad).to_string(
                unit=units.hourangle, sep=":"
            ),
            "dec": Angle(float(observation["dec"][0]), unit=units.rad).to_string(
                unit=units.degree, sep=":"
            ),
            "name": observation["note"][0],
            "program": observation["note"][0].rsplit("_", maxsplit=1)[0],
            "rot_sky": target.ang,
            "obs_time": target.obs_time,
            "num_exp": target.num_exp,
            "exp_times": target.exp_times,
            "estimated_slew_time": target.slewtime,
        }

        script_config_yaml = target.get_script_config()

        script_config_unpacked = yaml.safe_load(script_config_yaml)

        self.assertEqual(script_config_expected, script_config_unpacked)

    def test_get_script_config_cwfs(self):

        observation = self.make_fbs_observation(note="cwfs")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
        )

        script_config_expected = dict(
            find_target=dict(
                az=math.degrees(float(observation["az"][0])),
                el=math.degrees(float(observation["alt"][0])),
            )
        )

        script_config_yaml = target.get_script_config()

        script_config_unpacked = yaml.safe_load(script_config_yaml)

        self.assertEqual(script_config_expected, script_config_unpacked)

    def test_get_script_config_cwfs_with_additional_config(self):

        observation = self.make_fbs_observation(note="cwfs")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
            script_configuration_cwfs=dict(filter="SDSSg", grating="empty_1"),
        )

        script_config_expected = dict(
            find_target=dict(
                az=math.degrees(float(observation["az"][0])),
                el=math.degrees(float(observation["alt"][0])),
            ),
            filter="SDSSg",
            grating="empty_1",
        )

        script_config_yaml = target.get_script_config()

        script_config_unpacked = yaml.safe_load(script_config_yaml)

        self.assertEqual(script_config_expected, script_config_unpacked)

    def test_get_script_config_spec(self):

        observation = self.make_fbs_observation(note="spec:HD12345")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
        )

        script_config_expected = {
            "object_name": observation["note"][0],
            "object_dec": Angle(float(observation["dec"][0]), unit=units.rad).to_string(
                unit=units.degree, sep=":"
            ),
            "object_ra": Angle(float(observation["RA"][0]), unit=units.rad).to_string(
                unit=units.hourangle, sep=":"
            ),
        }

        script_config_yaml = target.get_script_config()

        script_config_unpacked = yaml.safe_load(script_config_yaml)

        self.assertEqual(script_config_expected, script_config_unpacked)

    def test_get_script_config_spec_with_additional_config(self):

        observation = self.make_fbs_observation(note="spec:HD12345")

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observation,
            script_configuration_spec=dict(
                filter_sequence=["SDSSg", "SDSSg"],
                grating_sequence=["empty_1", "empty_1"],
            ),
        )

        script_config_expected = {
            "object_name": observation["note"][0],
            "object_dec": Angle(float(observation["dec"][0]), unit=units.rad).to_string(
                unit=units.degree, sep=":"
            ),
            "object_ra": Angle(float(observation["RA"][0]), unit=units.rad).to_string(
                unit=units.hourangle, sep=":"
            ),
            "filter_sequence": ["SDSSg", "SDSSg"],
            "grating_sequence": ["empty_1", "empty_1"],
        }

        script_config_yaml = target.get_script_config()

        script_config_unpacked = yaml.safe_load(script_config_yaml)

        self.assertEqual(script_config_expected, script_config_unpacked)

    def test_get_script_config_multiple_observations(self):

        filter_obs = "gri"
        observations = self.make_fbs_observation("std", filter_obs=filter_obs)

        target = FeatureSchedulerTarget(
            observing_script_name="observing_script",
            observing_script_is_standard=True,
            observation=observations,
        )

        slew_time, error = self.observatory_model.get_slew_delay(target)

        script_config = yaml.safe_load(target.get_script_config())

        self.assertEqual(len(script_config["exp_times"]), len(filter_obs) * 2)
        for filter_name in filter_obs:
            self.assertIn(filter_name, script_config["band_filter"])

        self.assertEqual(error, 0)
        self.assertGreater(slew_time, 0.0)

    def make_fbs_observation(self, note, filter_obs="r"):

        observations = np.concatenate(
            [empty_observation() for _ in range(len(filter_obs))]
        )

        ra, dec, _ = self.observatory_model.altaz2radecpa(
            self.observatory_model.dateprofile, 65.0, 180.0
        )
        for obs_filter, observation in zip(filter_obs, observations):
            observation["RA"] = ra
            observation["dec"] = dec
            observation["mjd"] = self.observatory_model.dateprofile.mjd
            observation["filter"] = obs_filter
            observation["exptime"] = 30.0
            observation["nexp"] = 2
            observation["note"] = note

        return observations
