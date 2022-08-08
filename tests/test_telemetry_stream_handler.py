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

import logging
import unittest

import numpy as np
from jsonschema.exceptions import ValidationError

from lsst.ts.scheduler import TelemetryStreamHandler


class TestTelemetryStreamHandler(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestTelemetryStreamHandler")
        cls.efd_name = "unit_test_efd"

    def setUp(self) -> None:

        self.telemetry_stream_handler = TelemetryStreamHandler(
            log=self.log,
            efd_name=self.efd_name,
        )

    async def test_retrive_telemetry_no_stream(self):
        """Test calling retrieve telemetry when no telemetry stream is
        defined.
        """

        with self.assertRaises(RuntimeError):
            await self.telemetry_stream_handler.retrive_telemetry(stream_name="seeing")

    async def test_retrive_telemetry(self):
        """Test calling retrieve telemetry when no telemetry stream is
        defined.
        """

        telemetry_stream = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        await self.telemetry_stream_handler.configure_telemetry_stream(
            telemetry_stream=telemetry_stream
        )

        seeing = (
            await self.telemetry_stream_handler.retrive_telemetry(stream_name="seeing")
        )[0]

        assert np.isfinite(seeing)

    async def test_configure_telemetry_stream(self):

        valid_telemetry_stream = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
            dict(
                name="wind_speed",
                efd_table="lsst.sal.WeatherStation.windSpeed",
                efd_columns=["avg2M"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
            dict(
                name="wind_direction",
                efd_table="lsst.sal.WeatherStation.windDirection",
                efd_columns=["avg2M"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        await self.telemetry_stream_handler.configure_telemetry_stream(
            telemetry_stream=valid_telemetry_stream
        )

        for name in [stream["name"] for stream in valid_telemetry_stream]:
            assert name in self.telemetry_stream_handler.telemetry_streams

    async def test_configure_telemetry_stream_bad_efd_table(self):

        bad_efd_columns = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_inexistentTopic",
                efd_columns=["fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        with self.assertRaises(RuntimeError) as runtime_error:
            await self.telemetry_stream_handler.configure_telemetry_stream(
                telemetry_stream=bad_efd_columns
            )

        assert bad_efd_columns[0]["efd_table"] in str(runtime_error.exception)

    async def test_configure_telemetry_stream_bad_efd_columns(self):

        bad_efd_columns = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["not_fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        with self.assertRaises(RuntimeError) as runtime_error:
            await self.telemetry_stream_handler.configure_telemetry_stream(
                telemetry_stream=bad_efd_columns
            )

        assert bad_efd_columns[0]["name"] in str(runtime_error.exception)
        assert bad_efd_columns[0]["efd_table"] in str(runtime_error.exception)
        assert bad_efd_columns[0]["efd_columns"][0] in str(runtime_error.exception)

    async def test_configure_telemetry_stream_bad_efd_delta_time(self):

        bad_efd_columns = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["fwhm"],
                efd_delta_time=0.0,
                fill_value=None,
            ),
        ]

        with self.assertRaises(ValidationError):
            await self.telemetry_stream_handler.configure_telemetry_stream(
                telemetry_stream=bad_efd_columns
            )

        bad_efd_columns[0]["efd_delta_time"] = -1.0

        with self.assertRaises(ValidationError):
            await self.telemetry_stream_handler.configure_telemetry_stream(
                telemetry_stream=bad_efd_columns
            )

    async def test_configure_telemetry_stream_invalid_stream_schema(self):

        invalid_stream_schema_typo = [
            dict(
                namx="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["not_fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        invalid_stream_schema_missing_name = [
            dict(
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["not_fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        invalid_stream_schema_missing_efd_table = [
            dict(
                name="seeing",
                efd_columns=["not_fwhm"],
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        invalid_stream_schema_missing_efd_columns = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_delta_time=300.0,
                fill_value=None,
            ),
        ]

        invalid_stream_schema_missing_efd_delta_time = [
            dict(
                name="seeing",
                efd_table="lsst.sal.DIMM.logevent_dimmMeasurement",
                efd_columns=["not_fwhm"],
                fill_value=None,
            ),
        ]

        for invalid_schema in [
            invalid_stream_schema_typo,
            invalid_stream_schema_missing_name,
            invalid_stream_schema_missing_efd_table,
            invalid_stream_schema_missing_efd_columns,
            invalid_stream_schema_missing_efd_delta_time,
        ]:
            with self.assertRaises(ValidationError):
                await self.telemetry_stream_handler.configure_telemetry_stream(
                    telemetry_stream=invalid_schema
                )
