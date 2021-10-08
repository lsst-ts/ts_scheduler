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

from astropy.coordinates import Angle
from astropy import units

from .driver_target import DriverTarget


class FeatureSchedulerTarget(DriverTarget):
    """Feature based scheduler target.

    Parameters
    ----------
    observing_script_name : str
        Name of the observing script.
    observing_script_is_standard: bool
        Is the observing script standard?
    observation : `np.ndarray`
        Observation produced by the feature based scheduler.

    """

    def __init__(
        self,
        observing_script_name,
        observing_script_is_standard,
        observation,
        **kwargs,
    ):

        self.observation = observation

        self._script_config_root = "script_configuration"

        self._script_configuration = dict()
        for key in kwargs:
            if key.startswith(self._script_config_root):
                self._script_configuration[key] = kwargs[key]

        self._script_get_config = dict(
            cwfs=self._get_script_config_cwfs, spec=self._get_script_config_spec
        )

        super().__init__(
            observing_script_name=observing_script_name,
            observing_script_is_standard=observing_script_is_standard,
            targetid=observation["ID"][0],
            band_filter=observation["filter"][0],
            ra_rad=observation["RA"][0],
            dec_rad=observation["dec"][0],
            ang_rad=observation["rotSkyPos"][0],
            num_exp=observation["nexp"][0],
            exp_times=[
                observation["exptime"][0] / observation["nexp"][0]
                for i in range(observation["nexp"][0])
            ],
        )
        self.note = str(observation["note"][0])
        self.slewtime = float(observation["slewtime"][0])

    def get_script_config(self):
        survey_name = self._get_survey_name()

        if survey_name in self._script_get_config:
            return self._script_get_config[survey_name]()
        else:
            script_config_yaml = super().get_script_config()

            script_config = yaml.safe_load(script_config_yaml)

            additional_script_config = self._script_configuration.get(
                self._script_config_root, dict()
            ).copy()

            for key in additional_script_config:
                script_config[key] = additional_script_config[key]

            return yaml.safe_dump(script_config)

    def _get_script_config_cwfs(self):
        script_config = self._script_configuration.get(
            f"{self._script_config_root}_cwfs", dict()
        ).copy()

        if "find_target" in script_config:
            script_config["find_target"]["az"] = math.degrees(
                float(self.observation["az"][0])
            )
            script_config["find_target"]["el"] = math.degrees(
                float(self.observation["alt"][0])
            )
        else:
            script_config["find_target"] = dict(
                az=math.degrees(float(self.observation["az"][0])),
                el=math.degrees(float(self.observation["alt"][0])),
            )

        return yaml.safe_dump(script_config)

    def _get_script_config_spec(self):
        script_config = {
            "object_name": str(self.observation["note"][0]),
            "object_dec": str(
                Angle(float(self.observation["dec"][0]), unit=units.rad).to_string(
                    unit=units.degree, sep=":"
                )
            ),
            "object_ra": str(
                Angle(float(self.observation["RA"][0]), unit=units.rad).to_string(
                    unit=units.hourangle, sep=":"
                )
            ),
            **self._script_configuration.get(
                f"{self._script_config_root}_spec", dict()
            ),
        }

        return yaml.safe_dump(script_config)

    def _get_survey_name(self):
        return self.observation["note"][0].split(":")[0]
