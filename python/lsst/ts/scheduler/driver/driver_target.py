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

import numpy as np

from astropy import units
from astropy.coordinates import Angle

from lsst.ts.observatory.model import Target


class DriverTarget(Target):
    """This class provides a wrapper around `lsst.ts.observatory.model.Target`
    to add utility methods used by the Scheduler. The base class itself
    provides utility methods to interface with the observatory model. The
    methods added here are scheduler-specific, hence the need to subclass.

    Parameters
    ----------
    observing_script_name : str
        Name of the observing script.
    observing_script_is_standard: bool
        Is the observing script standard?
    targetid : int
        A unique identifier for the given target.
    fieldid : int
        The ID of the associated OpSim field for the target.
    band_filter : str
        The single character name of the associated band filter.
    ra_rad : float
        The right ascension (radians) of the target.
    dec_rad : float
        The declination (radians) of the target.
    ang_rad : float
        The sky angle (radians) of the target.
    obs_time : float
        Time of the observation. If zero (default) slew as soon as possible.
    num_exp : int
        The number of requested exposures for the target.
    exp_times : list[float]
        The set of exposure times (seconds) for the target. Needs to length
        of num_exp.

    """

    def __init__(
        self,
        observing_script_name,
        observing_script_is_standard,
        sal_index=0,
        targetid=0,
        fieldid=0,
        band_filter="",
        ra_rad=0.0,
        dec_rad=0.0,
        ang_rad=0.0,
        obs_time=0.0,
        num_exp=0,
        exp_times=[],
    ):
        self._observing_script_name = observing_script_name
        self._observing_script_is_standard = observing_script_is_standard
        self.sal_index = sal_index
        self.obs_time = obs_time
        super().__init__(
            targetid=targetid,
            fieldid=fieldid,
            band_filter=band_filter,
            ra_rad=ra_rad,
            dec_rad=dec_rad,
            ang_rad=ang_rad,
            num_exp=num_exp,
            exp_times=exp_times,
        )

    def get_script_config(self):
        """Returns a yaml string representation of a dictionary with the
        configuration to be used for the observing script.

        Returns
        -------
        config_str: str
        """
        script_config = {
            "targetid": self.targetid,
            "band_filter": str(self.filter),
            "ra": str(
                Angle(self.ra, unit=units.degree).to_string(
                    unit=units.hourangle, sep=":"
                )
            ),
            "dec": str(
                Angle(self.dec, unit=units.degree).to_string(unit=units.degree, sep=":")
            ),
            "name": self.note,
            "rot_sky": self.ang,
            "obs_time": self.obs_time,
            "num_exp": int(self.num_exp),
            "exp_times": [float(exptime) for exptime in self.exp_times],
            "estimated_slew_time": self.slewtime,
        }

        return yaml.safe_dump(script_config)

    def get_observing_script(self):
        """Returns the name of the observing script and whether it is a
        standard script or not.

        Returns
        -------
        observing_script_name : str
            Name of the observing script.
        observing_script_is_standard: bool
            Is the observing script standard?
        """
        return self._observing_script_name, self._observing_script_is_standard

    def as_dict(self, exposure_times_size=10, proposal_id_size=5):
        """Returns a dictionary with the Target information.

        Returns
        -------
        topic_target: `dict`
            Dictionary with target information.
        """
        topic_target = dict()

        topic_target["targetId"] = self.targetid
        topic_target["filter"] = self.filter
        topic_target["requestTime"] = self.time
        topic_target["ra"] = self.ra
        topic_target["decl"] = self.dec
        topic_target["skyAngle"] = self.ang
        topic_target["numExposures"] = self.num_exp
        topic_target["exposureTimes"] = np.zeros(exposure_times_size)
        for i, exptime in enumerate(self.exp_times):
            topic_target["exposureTimes"][i] = exptime
        topic_target["airmass"] = self.airmass
        topic_target["skyBrightness"] = self.sky_brightness
        topic_target["cloud"] = self.cloud
        topic_target["seeing"] = self.seeing
        topic_target["slewTime"] = self.slewtime
        topic_target["numProposals"] = self.num_props
        topic_target["proposalId"] = np.zeros(proposal_id_size, dtype=int)
        for i, prop_id in enumerate(self.propid_list):
            topic_target["proposalId"][i] = int(prop_id)
        topic_target["note"] = self.note

        return topic_target