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

import os
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

    def obs2opsim(
        self, obs_array, filename=None, info=None, delete_past=False, if_exists="append"
    ):
        """Convert an array of observations into a pandas dataframe
        with Opsim schema.

        Parameters
        ----------
        obs_array : `np.array`
            Numpy array with OpSim observations.
        filename : `str`, optional
            Name of the database file to write to.
        info : `np.array`, optional
            Numpy array with database info.
        delete_past : `bool`
            Delete past observations (default=False)?
        if_exists : `str`
            Flag to pass to `to_sql` when writting to the
            database to control strategy when the database
            already exists.

        Returns
        -------
        `pd.DataFrame` or `None`
            Either the converted dataframe or `None`, if
            filename is provided.
        """
        if delete_past:
            try:
                os.remove(filename)
            except OSError:
                pass

        df = pd.DataFrame(obs_array)
        df = df.rename(index=str, columns=self.inv_map)
        for colname in self.angles_rad2deg:
            df[colname] = np.degrees(df[colname])
        for colname in self.angles_hours2deg:
            df[colname] = df[colname] * 360.0 / 24.0

        if filename is not None:
            con = sqlite3.connect(filename)
            df.to_sql("observations", con, index=False, if_exists=if_exists)
            if info is not None:
                df = pd.DataFrame(info)
                df.to_sql("info", con, if_exists=if_exists)
        else:
            return df

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
