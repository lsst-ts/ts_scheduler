# This file is part of ts_scheduler
#
# Developed for Vera C. Rubin Observatory.
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

import unittest

import pandas
from astropy import units
from astropy.time import Time, TimeDelta

from lsst.ts.scheduler.utils import get_efd_client, get_mock_efd_client


class TestEfdUtils(unittest.IsolatedAsyncioTestCase):
    def test_get_efd_client_mock(self):
        mock_efd_client = get_efd_client(efd_name="mock_efd", mock=True)
        assert isinstance(mock_efd_client, unittest.mock.AsyncMock)

    async def test_get_mock_efd_client(self):
        mock_efd_client = get_mock_efd_client("mock_efd")

        assert isinstance(mock_efd_client, unittest.mock.AsyncMock)

        assert "mock_efd" in mock_efd_client.list_efd_names()

        end_time = Time.now()
        start_time = end_time - TimeDelta(10 * units.second)

        data = await mock_efd_client.select_time_series(
            topic_name="lsst.sal.DIMM.logevent_dimmMeasurement",
            fields=["fwhm"],
            start=start_time,
            end=end_time,
            is_window=False,
            index=None,
        )

        assert isinstance(data, pandas.core.frame.DataFrame)
        assert "fwhm" in data
