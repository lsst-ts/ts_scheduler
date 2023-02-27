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

__all__ = [
    "SchemaConverter",
]

import sqlite3

import numpy as np
import pandas as pd
from rubin_sim.scheduler.utils import empty_observation


class SchemaConverter:
    """Record how to convert an observation array to the standard
    opsim schema.
    """

    def __init__(self) -> None:
        # Conversion dictionary, keys are opsim schema, values are
        # observation dtype names
        self.convert_dict = {
            "observationId": "ID",
            "night": "night",
            "observationStartMJD": "mjd",
            "observationStartLST": "lmst",
            "numExposures": "nexp",
            "visitTime": "visittime",
            "visitExposureTime": "exptime",
            "proposalId": "survey_id",
            "fieldId": "field_id",
            "fieldRA": "RA",
            "fieldDec": "dec",
            "altitude": "alt",
            "azimuth": "az",
            "filter": "filter",
            "airmass": "airmass",
            "skyBrightness": "skybrightness",
            "cloud": "clouds",
            "seeingFwhm500": "FWHM_500",
            "seeingFwhmGeom": "FWHM_geometric",
            "seeingFwhmEff": "FWHMeff",
            "fiveSigmaDepth": "fivesigmadepth",
            "slewTime": "slewtime",
            "slewDistance": "slewdist",
            "paraAngle": "pa",
            "rotTelPos": "rotTelPos",
            "rotTelPos_backup": "rotTelPos_backup",
            "rotSkyPos": "rotSkyPos",
            "rotSkyPos_desired": "rotSkyPos_desired",
            "moonRA": "moonRA",
            "moonDec": "moonDec",
            "moonAlt": "moonAlt",
            "moonAz": "moonAz",
            "moonDistance": "moonDist",
            "moonPhase": "moonPhase",
            "sunAlt": "sunAlt",
            "sunAz": "sunAz",
            "solarElong": "solarElong",
            "note": "note",
        }
        # Column(s) not bothering to remap:  'observationStartTime': None,
        self.inv_map = {v: k for k, v in self.convert_dict.items()}
        # angles to convert
        self.angles_rad2deg = [
            "fieldRA",
            "fieldDec",
            "altitude",
            "azimuth",
            "slewDistance",
            "paraAngle",
            "rotTelPos",
            "rotSkyPos",
            "rotSkyPos_desired",
            "rotTelPos_backup",
            "moonRA",
            "moonDec",
            "moonAlt",
            "moonAz",
            "moonDistance",
            "sunAlt",
            "sunAz",
            "sunRA",
            "sunDec",
            "solarElong",
            "cummTelAz",
        ]
        # Put LMST into degrees too
        self.angles_hours2deg = ["observationStartLST"]

    def obs2opsim(
        self,
        obs_array: np.ndarray,
        filename: str,
    ) -> None:
        """Convert an array of observations into a pandas dataframe
        with Opsim schema and store it in a sqlite database.

        Parameters
        ----------
        obs_array : `np.ndarray`
            Array of observations.
        filename : `str`
            Name of the database file.
        """

        df = pd.DataFrame(obs_array)
        df = df.rename(index=str, columns=self.inv_map)
        for colname in self.angles_rad2deg:
            df[colname] = np.degrees(df[colname])
        for colname in self.angles_hours2deg:
            df[colname] = df[colname] * 360.0 / 24.0

        if filename is not None:
            con = sqlite3.connect(filename)
            df.to_sql(
                "observations",
                con,
                if_exists="append",
                index=False,
            )

    def opsim2obs(self, filename: str) -> np.ndarray:
        """Read an opsim database and return an observation array.

        Parameters
        ----------
        filename : `str`
            Path to the observation database.

        Returns
        -------
        `np.ndarray`
            A numpy named array with observations. The format is defined by
            the feature scheduler observation.
        """

        df = self.opsim2df(filename)

        blank = empty_observation()
        final_result = np.empty(df.shape[0], dtype=blank.dtype)

        for i, key in enumerate(df.columns):
            if key in self.inv_map.keys():
                final_result[key] = df[key].values

        return final_result

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
