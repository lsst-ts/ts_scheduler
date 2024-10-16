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

import math
import typing
import unittest

import numpy as np
import yaml
from astropy import units
from astropy.coordinates import Angle
from astropy.time import Time
from lsst.ts import observing
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.scheduler.driver.feature_scheduler_target import FeatureSchedulerTarget
from lsst.ts.scheduler.utils.test.feature_scheduler_sim import MJD_START
from rubin_scheduler.scheduler.utils import ObservationArray


class TestFeatureSchedulerTarget(unittest.TestCase):
    def setUp(self) -> None:
        self.observatory_model = ObservatoryModel()
        self.observatory_model.configure_from_module()

        start_time = Time(MJD_START, format="mjd", scale="tai")

        self.observatory_model.update_state(start_time.unix)

        return super().setUp()

    def test_constructor(self):
        observing_block = self.make_observing_block()
        observation = self.make_fbs_observation(note="std")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        slew_time, error = self.observatory_model.get_slew_delay(target)

        self.assertEqual(error, 0)
        self.assertGreater(slew_time, 0.0)

    def test_get_script_config(self):
        observing_block = self.make_observing_block()
        observation = self.make_fbs_observation(note="std")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        script_config_expected = {
            "targetid": target.targetid,
            "band_filter": target.filter,
            "name": observation["note"][0],
            "ra": target.get_ra(),
            "dec": target.get_dec(),
            "alt": target.alt,
            "az": target.az,
            "rot": target.rot,
            "rot_sky": target.ang,
            "obs_time": target.obs_time,
            "num_exp": target.num_exp,
            "exp_times": target.exp_times,
            "estimated_slew_time": target.slewtime,
            "program": observing_block.program,
        }

        script_config = target.get_script_config()

        assert script_config == script_config_expected

    def test_get_script_config_cwfs(self):
        observing_block = self.make_observing_block_cwfs()
        observation = self.make_fbs_observation(note="cwfs")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        script_config_expected = dict(
            find_target=dict(
                az=math.degrees(float(observation["az"][0])),
                el=math.degrees(float(observation["alt"][0])),
                mag_limit=8.0,
            ),
            program="cwfs",
        )

        script_config = yaml.safe_load(
            target.get_observing_block().scripts[0].get_script_configuration()
        )

        assert script_config == script_config_expected

    def test_get_script_config_cwfs_with_additional_config(self):
        observing_block = self.make_observing_block_cwfs(
            additional_config=dict(filter="SDSSg", grating="empty_1")
        )
        observation = self.make_fbs_observation(note="cwfs")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        script_config_expected = dict(
            find_target=dict(
                az=math.degrees(float(observation["az"][0])),
                el=math.degrees(float(observation["alt"][0])),
                mag_limit=8.0,
            ),
            program="cwfs",
            filter="SDSSg",
            grating="empty_1",
        )

        script_config = yaml.safe_load(
            target.get_observing_block().scripts[0].get_script_configuration()
        )

        assert script_config == script_config_expected

    def test_get_script_config_spec(self):
        observing_block = self.make_observing_block_spec()
        observation = self.make_fbs_observation(note="spec:HD12345")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        script_config_expected = {
            "object_name": observation["note"][0].split(":", maxsplit=1)[-1],
            "object_dec": Angle(float(observation["dec"][0]), unit=units.rad).to_string(
                unit=units.degree, sep=":", alwayssign=True
            ),
            "object_ra": Angle(float(observation["RA"][0]), unit=units.rad).to_string(
                unit=units.hourangle, sep=":", alwayssign=True
            ),
            "program": observing_block.program,
        }

        script_config = yaml.safe_load(
            target.get_observing_block().scripts[0].get_script_configuration()
        )

        assert script_config == script_config_expected

    def test_get_script_config_spec_with_additional_config(self):
        additional_config = dict(
            do_acquire=True,
            acq_filter="empty_1",
            acq_grating="holo4_003",
            acq_exposure_time=5.0,
            do_blind_offset=False,
            do_take_sequence=True,
            exposure_time_sequence=[30.0, 30.0],
            filter_sequence=["empty_1", "empty_1"],
            grating_sequence=["holo4_003", "holo4_003"],
        )

        observing_block = self.make_observing_block_spec(
            additional_config=additional_config
        )
        observation = self.make_fbs_observation(note="spec:HD12345")

        target = FeatureSchedulerTarget(
            observing_block=observing_block,
            observation=observation,
        )

        script_config_expected = additional_config.copy()

        script_config_expected["object_name"] = observation["note"][0].split(
            ":", maxsplit=1
        )[-1]
        script_config_expected["object_dec"] = Angle(
            float(observation["dec"][0]), unit=units.rad
        ).to_string(unit=units.degree, sep=":", alwayssign=True)
        script_config_expected["object_ra"] = Angle(
            float(observation["RA"][0]), unit=units.rad
        ).to_string(unit=units.hourangle, sep=":", alwayssign=True)
        script_config_expected["filter_sequence"] = ["empty_1", "empty_1"]
        script_config_expected["grating_sequence"] = ["holo4_003", "holo4_003"]
        script_config_expected["program"] = observing_block.program

        script_config = yaml.safe_load(
            target.get_observing_block().scripts[0].get_script_configuration()
        )

        assert script_config == script_config_expected

    def make_fbs_observation(self, note, filter_obs="r"):
        observations = np.concatenate(
            [ObservationArray(n=1) for _ in range(len(filter_obs))]
        )

        ra, dec, _ = self.observatory_model.altaz2radecpa(
            self.observatory_model.dateprofile, np.deg2rad(65.0), np.deg2rad(180.0)
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

    def make_observing_block(self) -> observing.ObservingBlock:
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
            standard=False,
            parameters={
                "exp_times": "$exp_times",
                "band_filter": "$band_filter",
                "program": "$program",
                "note": "Static note will be preserved.",
            },
        )

        return observing.ObservingBlock(
            name="OBS-123",
            program="SITCOM-456",
            scripts=[script1, script2],
            constraints=[observing.AirmassConstraint(max=1.5)],
        )

    def make_observing_block_cwfs(
        self, additional_config: dict[str, typing.Any] = None
    ) -> observing.ObservingBlock:
        parameters = additional_config if additional_config is not None else dict()
        parameters["find_target"] = dict(
            az="$az",
            el="$alt",
            mag_limit=8.0,  # This won't be overwritten.
        )
        parameters["program"] = "$program"
        script = observing.ObservingScript(
            name="cwfs",
            standard=True,
            parameters=parameters,
        )
        return observing.ObservingBlock(
            name="cwfs",
            program="cwfs",
            scripts=[script],
            constraints=[],
        )

    def make_observing_block_spec(
        self, additional_config: dict[str, typing.Any] = None
    ) -> observing.ObservingBlock:
        parameters = (
            additional_config.copy() if additional_config is not None else dict()
        )
        parameters["object_name"] = "$name"
        parameters["object_ra"] = "$ra"
        parameters["object_dec"] = "$dec"
        parameters["program"] = "$program"

        script = observing.ObservingScript(
            name="spec",
            standard=True,
            parameters=parameters,
        )
        return observing.ObservingBlock(
            name="MainSpectroscopicSurvey",
            program="SITCOM-123",
            scripts=[script],
            constraints=[],
        )
