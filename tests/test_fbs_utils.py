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

import math

from lsst.ts.scheduler.driver.driver_target import DriverTarget
from lsst.ts.scheduler.utils.fbs_utils import make_fbs_observation_from_target
from lsst.ts.scheduler.utils.test.block_utils import get_test_obs_block


def test_make_fbs_observation_from_target() -> None:
    obs_block = get_test_obs_block()
    ra = 10.0
    dec = 20.0
    target = DriverTarget(
        observing_block=obs_block,
        ra_rad=math.radians(ra),
        dec_rad=math.radians(dec),
        num_exp=2,
        exp_times=[15, 15],
        note="Test",
    )

    fbs_observation = make_fbs_observation_from_target(target=target)

    print(f"{fbs_observation!r}")

    assert fbs_observation["RA"][0] == target.ra_rad
    assert fbs_observation["dec"][0] == target.dec_rad
    assert fbs_observation["note"][0] == target.note
    assert fbs_observation["exptime"][0] == sum(target.exp_times)
