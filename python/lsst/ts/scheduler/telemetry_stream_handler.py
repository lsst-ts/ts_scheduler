# This file is part of ts_scheduler
#
# Developed for the Vera C. Rubin Observatory.
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

__all__ = ["TelemetryStreamHandler"]

import logging
from typing import Any, Dict, List

import numpy
from astropy import units
from astropy.time import Time, TimeDelta

from lsst.ts import salobj

from . import CONFIG_SCHEMA
from .utils import get_efd_client


class TelemetryStreamHandler:
    """Handle telemetry stream.

    Parameters
    ----------
    log : `logging.Logger`
        Logger class.
    efd_name : `str`
        Name of the efd instance to query telemetry from.
    """

    def __init__(
        self,
        log: logging.Logger,
        efd_name: str,
    ) -> None:

        self.log = log.getChild(type(self).__name__)

        self.efd_name: str = efd_name
        self.telemetry_streams: Dict = dict()

        self.efd_client: Any = None

    async def configure_telemetry_stream(self, telemetry_stream: List[Dict]) -> None:
        """Configure telemetry streams.

        Parameters
        ----------
        telemetry_stream : `list` of `dict`
            List of telemetry streams to parse.

        Raises
        ------
        ValidationError:
            If one (or more) stream is invalid.
        RuntimeError:
            If selected efd_table are not in the selected EFD instance.
            If selected efd_columns are not in the topic attributes.
        """

        self._configure_efd_client()

        validated_telemetry_stream = self._get_validated_telemetry_stream(
            telemetry_stream
        )

        await self._check_efd_tables(validated_telemetry_stream)

        await self._check_efd_columns(validated_telemetry_stream)

        self.telemetry_streams = validated_telemetry_stream

    def _configure_efd_client(self) -> None:
        """Configure EFD client."""
        if self.efd_client is None:
            self.log.info(f"Initializing efd client for {self.efd_name} instance.")
            self.efd_client = get_efd_client(self.efd_name)

    def _get_validated_telemetry_stream(self, telemetry_stream: List[Dict]) -> Dict:
        """Get validate telemetry stream.

        Parameters
        ----------
        telemetry_stream : `list` of `dict`
            Input telemetry stream.

        Returns
        -------
        validated_telemetry_stream : `dict`
            Reformated telemetry stream with validated entries.

        Raises
        ------
        ValidationError:
            If one (or more) stream is invalid.
        """
        schema_validator = salobj.DefaultingValidator(self.telemetry_stream_schema)

        self.log.debug("Validating telemetry stream schema.")

        validated_telemetry_stream = dict()
        for stream in telemetry_stream:
            validated_stream = schema_validator.validate(stream)
            validated_telemetry_stream[validated_stream["name"]] = validated_stream

        return validated_telemetry_stream

    async def _check_efd_tables(self, validated_telemetry_stream: Dict) -> None:
        """Check EFD table entries in validated_telemetry_stream.

        Parameters
        ----------
        validated_telemetry_stream : `dict`
            A dictionary with validated telemetry stream.

        Raises
        ------
        RuntimeError:
            If selected efd_table are not in the selected EFD instance.
        """
        self.log.debug("Checking EFD tables.")

        valid_topics = set(await self.efd_client.get_topics())

        telemetry_topics = {
            stream["efd_table"] for stream in validated_telemetry_stream.values()
        }

        invalid_topics = telemetry_topics - valid_topics

        if len(invalid_topics) > 0:
            raise RuntimeError(
                f"Found {len(invalid_topics)} invalid topics: {invalid_topics}. "
                f"Efd table should be in the format '{valid_topics.pop()}', "
                f"and must be available in {self.efd_name} efd instance."
            )

    async def _check_efd_columns(self, validated_telemetry_stream: Dict) -> None:
        """Check topics in validated_telemetry_stream.

        Parameters
        ----------
        validated_telemetry_stream : `dict`
            A dictionary with validated telemetry stream.

        Raises
        ------
        RuntimeError:
            If selected efd_columns are not in the topic attributes.
        """
        self.log.debug("Checking efd_tables.")

        invalid_data = dict()

        for stream_name in validated_telemetry_stream:
            topic = validated_telemetry_stream[stream_name]["efd_table"]
            topic_attributes = set(
                validated_telemetry_stream[stream_name]["efd_columns"]
            )
            valid_topic_attributes = set(await self.efd_client.get_fields(topic))

            invalid_topic_attributes = topic_attributes - valid_topic_attributes

            if len(invalid_topic_attributes) > 0:
                invalid_data[stream_name] = dict(
                    topic=topic,
                    invalid_topic_attributes=invalid_topic_attributes,
                )

        if len(invalid_data) > 0:
            err_msg = "Found invalid efd columns in the following telemetry streams: "
            err_msg += f"{', '.join(invalid_data.keys())}. "
            for name in invalid_data:
                err_msg += f"\nInvalid attribute {', '.join(invalid_data[name]['invalid_topic_attributes'])} "
                err_msg += f" in {invalid_data[name]['topic']}."
            raise RuntimeError(err_msg)

    async def retrive_telemetry(self, stream_name: str) -> List[float]:
        """Retrieve telemetry for a given stream.

        Parameters
        ----------
        stream_name : `str`
            Name of the telemetry stream to retrieve data from.

        Returns
        -------
        telemetry_values : `list` of `float`
            Telemetry value, one for each entry in
            `telemetry_streams[stream_name]["efd_columns"]`.

        Raises
        ------
        RuntimeError:
            If `stream_name` is not in the list of configured streams.
        """

        if stream_name not in self.telemetry_streams:
            raise RuntimeError(
                f"Invalid stream name {stream_name}. Must be one of {self.telemetry_streams}."
            )

        time_query_end = Time.now()
        time_query_start = time_query_end - TimeDelta(
            self.telemetry_streams[stream_name]["efd_delta_time"] * units.second
        )

        self.log.debug(
            f"Retrieving {stream_name} telemetry between {time_query_start}::{time_query_end}."
        )

        efd_data = await self.efd_client.select_time_series(
            self.telemetry_streams[stream_name]["efd_table"],
            self.telemetry_streams[stream_name]["efd_columns"],
            time_query_start,
            time_query_end,
        )

        telemetry_values = self.get_fill_values_for(stream_name)

        for i, column_name in enumerate(efd_data):
            if len(efd_data[column_name]) > 0:
                telemetry_values[i] = efd_data[column_name].mean()
            else:
                self.log.warning(f"No value retrieved for {stream_name}::{column_name}")

        return telemetry_values

    def get_fill_values_for(self, stream_name: str) -> List[float]:
        """Return list of fill values for telemetry stream.

        Parameters
        ----------
        stream_name : `str`
            Name of the telemetry stream to retrieve data from.

        Returns
        -------
        `list` of `float`
            Fill values.
        """
        fill_value = self.telemetry_streams[stream_name]["fill_value"]

        return [
            fill_value if fill_value is not None else numpy.nan,
        ] * len(self.telemetry_streams[stream_name]["efd_columns"])

    @property
    def telemetry_stream_schema(self) -> Dict:
        return CONFIG_SCHEMA["properties"]["telemetry"]["properties"]["streams"][
            "items"
        ]
