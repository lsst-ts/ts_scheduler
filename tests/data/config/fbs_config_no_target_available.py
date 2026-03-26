# This file is part of ts_config_ocs.
#
# Developed for the Vera Rubin Observatory Telescope and Site System.
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

import copy

import astropy.units as u
from astropy.time import Time
from lsst.ts.fbs.utils.maintel.lsst_surveys import safety_masks
from rubin_scheduler.scheduler import basis_functions
from rubin_scheduler.scheduler.detailers import (
    AltAz2RaDecDetailer,
    CopyValueDetailer,
    Rottep2RotspDesiredDetailer,
)
from rubin_scheduler.scheduler.schedulers import CoreScheduler
from rubin_scheduler.scheduler.surveys import FieldAltAzSurvey


def get_scheduler():
    """Construct feature based scheduler with two alt/az targets,
    alternating between these targets every hour after enabling
    the scheduler.

    Returns
    -------
    nside : int
        Healpix map resolution.
    scheduler : Core_scheduler
        Feature based scheduler.
    """

    nside = 32

    # Mapping from band to filter from
    # obs_lsst/python/lsst/obs/lsst/filters.py
    band_to_filter = {
        "u": "u_24",
        "g": "g_6",
        "r": "r_57",
        "i": "i_39",
        "z": "z_20",
        "y": "y_10",
    }

    safety_mask_params = {
        "nside": nside,
        "wind_speed_maximum": 20,
        "shadow_minutes": 0,
        "apply_time_limited_shadow": False,
        "time_to_sunrise": 3.0,
        "min_az_sunrise": 144,
        "max_az_sunrise": 255,
    }

    t_start = Time.now() + 2.0 * u.min
    t_end = Time.now() + 30.0 * u.min

    first_windows = basis_functions.InTimeWindowBasisFunction(
        [[t_start.mjd, t_end.mjd]]
    )

    # Choose the alt/az targets here
    first_alt = 70.0
    first_az = 0.0

    first_target_name = f"UnitTest alt:{first_alt:.1f} az:{first_az:.1f}"

    block_name = "BLOCK-6"

    sequence = ["i"]
    nvisits = {"u": 1, "g": 1, "r": 1, "i": 1, "z": 1, "y": 1}
    exptimes = {"u": 38, "g": 30, "r": 30, "i": 30, "z": 30, "y": 30}

    detailers = [
        AltAz2RaDecDetailer(),
        Rottep2RotspDesiredDetailer(),
        CopyValueDetailer(source="rotSkyPos_desired", destination="rotSkyPos"),
    ]

    survey = FieldAltAzSurvey(
        basis_functions=safety_masks(**safety_mask_params) + [first_windows],
        alt=first_alt,
        az=first_az,
        sequence=sequence,
        nvisits=nvisits,
        exptimes=exptimes,
        ignore_obs=None,
        survey_name=first_target_name,
        target_name=first_target_name,
        science_program=block_name,
        observation_reason="fbs driven test",
        scheduler_note=first_target_name,
        nside=nside,
        flush_pad=30.0,
        detailers=copy.deepcopy(detailers),
    )

    survey_lists = [
        [
            survey,
        ],
    ]

    return nside, CoreScheduler(
        survey_lists,
        nside=nside,
        band_to_filter=band_to_filter,
    )


if __name__ == "config":
    nside, scheduler = get_scheduler()
