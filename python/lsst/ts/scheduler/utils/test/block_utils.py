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
    "get_test_obs_block",
]

from lsst.ts import observing


def get_test_obs_block() -> observing.ObservingBlock:
    """Return an observing block suitable for testing.

    Returns
    -------
    `observing.ObservingBlock`
        Observing block.
    """
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
