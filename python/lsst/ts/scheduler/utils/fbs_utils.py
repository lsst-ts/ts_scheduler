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

__all__ = [
    "SchemaConverter",
    "make_fbs_observation_from_target",
]

import sqlite3

import numpy as np
import pandas as pd
import rubin_scheduler.scheduler.utils as rs_sched_utils

from ..driver.driver_target import DriverTarget


class SchemaConverter(rs_sched_utils.SchemaConverter):
    """Record how to convert an observation array to the standard
    opsim schema.

    Extends rubin_scheduler.scheduler.utils.SchemaConverter with
    a method to read an opsim database and return a dataframe instead
    of an observation array.
    """

    def opsim2df(self, filename: str) -> pd.DataFrame:
        """Read an opsim database and return a pandas data frame.

        Parameters
        ----------
        filename : `str`
            Path to an sqlite3 opsim database.

        Returns
        -------
        `pd.DataFrame`
            Observations from the database.
        """
        con = sqlite3.connect(filename)
        df = pd.read_sql("select * from observations;", con)
        for key in self.angles_rad2deg:
            df[key] = np.radians(df[key])
        for key in self.angles_hours2deg:
            df[key] = df[key] * 24.0 / 360.0

        df = df.rename(index=str, columns=self.convert_dict)
        return df


def make_fbs_observation_from_target(target: DriverTarget) -> np.ndarray:
    """Make an fbs observation from a driver target.

    Parameters
    ----------
    target : `DriverTarget`
        Target to generate observation from.

    Returns
    -------
    `np.ndarray`
        Feature based scheduler observation.
    """
    observation = rs_sched_utils.empty_observation()

    observation["ID"][0] = target.targetid
    observation["filter"][0] = target.filter
    observation["RA"][0] = target.ra_rad
    observation["dec"][0] = target.dec_rad
    observation["rotSkyPos"][0] = target.ang_rad
    observation["nexp"][0] = target.num_exp
    observation["exptime"][0] = sum(target.exp_times)
    observation["note"][0] = target.note
    observation["slewtime"][0] = target.slewtime

    return observation
