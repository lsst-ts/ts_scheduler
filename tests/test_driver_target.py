# This file is part of ts_scheduler
#
# Developed for the Vera Rubin Observatory.
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest

import pytest
import yaml
from astropy import units
from astropy.coordinates import Angle
from astropy.time import Time
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.scheduler.driver.driver_target import DriverTarget
from lsst.ts.scheduler.exceptions import NonConsecutiveIndexError
from lsst.ts.scheduler.utils.test.block_utils import get_test_obs_block


class TestDriverTarget(unittest.TestCase):
    def setUp(self) -> None:
        self.observatory_model = ObservatoryModel()
        self.observatory_model.configure_from_module()

        start_time = Time(59847.18611, format="mjd", scale="tai")

        self.observatory_model.update_state(start_time.unix)

        return super().setUp()

    def test_constructor(self) -> None:
        observing_block = get_test_obs_block()

        target = DriverTarget(
            observing_block=observing_block,
            band_filter="r",
        )

        slew_time, error = self.observatory_model.get_slew_delay(target)

        self.assertEqual(error, 0)
        self.assertGreater(slew_time, 0.0)

    def test_get_script_config(self) -> None:
        observing_block = get_test_obs_block()

        target = DriverTarget(
            observing_block=observing_block,
            band_filter="r",
        )

        script_config_expected = self.get_expected_script_config(target=target)

        script_config = target.get_script_config()

        self.assertEqual(script_config_expected, script_config)

    def test_get_observing_block(self) -> None:
        observing_block = get_test_obs_block()

        target = DriverTarget(
            observing_block=observing_block,
            band_filter="r",
        )

        observing_block = target.get_observing_block()

        script1_expected_parameters = {
            "name": target.get_target_name(),
            "rot_sky": target.ang,
            "estimated_slew_time": target.slewtime,
            "obs_time": target.obs_time,
            "note": "Static note will be preserved.",
        }

        script2_expected_parameters = {
            "exp_times": target.exp_times,
            "band_filter": target.filter,
            "program": observing_block.program,
            "note": "Static note will be preserved.",
        }

        script1_config = yaml.safe_load(
            observing_block.scripts[0].get_script_configuration()
        )
        script2_config = yaml.safe_load(
            observing_block.scripts[1].get_script_configuration()
        )

        ra_expected = Angle(target.ra, unit=units.degree).to_string(
            unit=units.degree, sep=":", alwayssign=True
        )
        dec_expected = Angle(target.dec, unit=units.degree).to_string(
            unit=units.degree, sep=":", alwayssign=True
        )

        ra_parsed = Angle(script1_config.pop("ra"), unit=units.hourangle).to_string(
            unit=units.degree, sep=":", alwayssign=True
        )
        dec_parsed = Angle(script1_config.pop("dec"), unit=units.degree).to_string(
            unit=units.degree, sep=":", alwayssign=True
        )
        assert ra_expected == ra_parsed
        assert dec_expected == dec_parsed
        assert script1_config == script1_expected_parameters
        assert script2_config == script2_expected_parameters

    def test_sal_index(self) -> None:
        observing_block = get_test_obs_block()

        target = DriverTarget(
            observing_block=observing_block,
            band_filter="r",
        )

        assert len(target.get_sal_indices()) == 0

        target.add_sal_index(2000)
        target.add_sal_index(2001)
        sal_indices = target.get_sal_indices()
        assert len(sal_indices) == 2
        assert sal_indices[0] == 2000
        assert sal_indices[1] == 2001

        with pytest.raises(
            NonConsecutiveIndexError,
            match="Non-consecutive SAL index for target observations. ",
        ):
            target.add_sal_index(2003)

    def get_expected_script_config(self, target: DriverTarget) -> dict:
        script_config_expected = {
            "targetid": target.targetid,
            "band_filter": target.filter,
            "name": target.note,
            "ra": target.get_ra(),
            "dec": target.get_dec(),
            "rot_sky": target.ang,
            "alt": float(target.alt),
            "az": float(target.az),
            "rot": float(target.rot),
            "obs_time": target.obs_time,
            "num_exp": target.num_exp,
            "exp_times": target.exp_times,
            "estimated_slew_time": target.slewtime,
            "program": target.observing_block.program,
        }

        return script_config_expected
