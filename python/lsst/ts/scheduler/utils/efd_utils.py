# This file is part of ts_scheduler
#
# Developed for the Vera C. Rubin Observatory..
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

__all__ = ["get_efd_client", "get_mock_efd_client"]

import warnings
from typing import Any, List, Union
from unittest.mock import AsyncMock, Mock

import astropy
import numpy as np
import pandas
import yaml

from ..driver.feature_scheduler import FeatureScheduler
from .csc_utils import efd_query_re
from .fbs_utils import SchemaConverter

try:
    import lsst_efd_client

    __with_lsst_efd_client__ = True
except ImportError:
    warnings.warn("Could not import lsst_efd_client. Telemetry stream will not work.")
    __with_lsst_efd_client__ = False


def get_efd_client(efd_name: str, mock: bool = False) -> Any:
    """Utility function to get an EFD client.

    This method helps deal with the condition where library cannot be imported
    and a mock client is needed for unit testing.

    Parameters
    ----------
    efd_name : `str`
        Name of the EFD instance.
    mock : `bool`
        Create a mock EFD client instead of creating a real instance.

    Returns
    -------
    efd_client : `lsst_efd_client.EfdClient` or `unittest.mock.AsyncMock`
        EFD client.

    Raises
    ------
    RuntimeError:
        If `efd_name` is not valid.
    """

    efd_client: Any = None

    if mock:
        efd_client = get_mock_efd_client(efd_name)

    elif not __with_lsst_efd_client__:
        warnings.warn("Running with no efd client library. Creating mock efd client.")

        efd_client = get_mock_efd_client(efd_name)

    elif efd_name not in lsst_efd_client.EfdClient.list_efd_names():
        raise RuntimeError(
            f"Unrecognizable efd_name ({efd_name}). "
            f"Must be one of {lsst_efd_client.EfdClient.list_efd_names()}."
        )

    else:
        efd_client = lsst_efd_client.EfdClient(efd_name)

    return efd_client


def get_mock_efd_client(efd_name: str) -> AsyncMock:
    """Create a mock EFD client.

    Parameters
    ----------
    efd_name : `str`
        Name of the EFD instance.

    Returns
    -------
    mock_efd_client : `unittest.mock.AsyncMock`
        Mock EFD client.
    """

    mock_efd_client = AsyncMock()

    mock_efd_client.configure_mock(
        **{
            "select_time_series.side_effect": mock_select_time_series,
            "get_topics.side_effect": mock_get_topics,
            "get_fields.side_effect": mock_get_fields,
            "influx_client.query.side_effect": mock_query,
        },
    )

    mock_efd_client.attach_mock(
        Mock(
            return_value=[
                efd_name,
            ],
        ),
        "list_efd_names",
    )

    return mock_efd_client


async def mock_select_time_series(
    topic_name: str,
    fields: Union[str, List[str]],
    start: astropy.time.Time,
    end: astropy.time.Time,
    is_window: bool = False,
    index: bool = None,
):
    """Mock for select time series method from EfdClient.

    Parameters
    ----------
    topic_name : `str`
        Name of topic to query.
    fields :  `str` or `list`
        Name of field(s) to query.
    start : `astropy.time.Time`
        Start time of the time range, if ``is_window`` is specified,
        this will be the midpoint of the range.
    end : `astropy.time.Time` or `astropy.time.TimeDelta`
        End time of the range either as an absolute time or
        a time offset from the start time.
    is_window : `bool`, optional
        If set and the end time is specified as a
        `~astropy.time.TimeDelta`, compute a range centered on the start
        time (default is `False`).
    index : `int`, optional
        For indexed topics set this to the index of the topic to query
        (default is `None`).

    Returns
    -------
    result : `pandas.DataFrame`
        A `pandas.DataFrame` containing the results of the query.
    """

    number_of_data_points = 10

    table_index = pandas.date_range(
        start=start.datetime,
        end=end.datetime,
        periods=number_of_data_points,
    )

    data = np.random.rand(number_of_data_points, len(fields))

    result = pandas.DataFrame(
        data=data,
        index=table_index,
        columns=fields,
    )

    return result


async def mock_get_topics() -> List:
    """Mock get topics method from EfdClient.

    Returns
    -------
    results : `list`
        List of valid topics in the database.
    """

    return [
        "lsst.sal.DIMM.logevent_dimmMeasurement",
        "lsst.sal.WeatherStation.windSpeed",
        "lsst.sal.WeatherStation.windDirection",
    ]


async def mock_get_fields(topic_name: str) -> List:
    """Mock get fields method from EfdClient.

    Parameters
    ----------
    topic_name : `str`
        Name of topic to query for field names.

    Returns
    -------
    results : `list`
        List of field names in specified topic.
    """

    fields = dict(
        [
            ("lsst.sal.DIMM.logevent_dimmMeasurement", ["fwhm"]),
            ("lsst.sal.WeatherStation.windSpeed", ["avg2M"]),
            ("lsst.sal.WeatherStation.windDirection", ["avg2M"]),
        ]
    )

    return fields[topic_name]


async def mock_query(efd_query: str) -> pandas.DataFrame:
    """Return a data frame for the associated query.

    Parameters
    ----------
    efd_query : `str`
        EFD query.

    Returns
    -------
    result : `pandas.DataFrame`
        Query results.
    """

    efd_query_match = efd_query_re.match(efd_query)

    if efd_query_match.groups() == (
        "*",
        '"efd"."autogen"."lsst.sal.Scheduler.logevent_observation"',
        "SchedulerID = 1",
    ):
        return get_observation_table()
    else:
        return pandas.DataFrame()


def get_observation_table() -> pandas.DataFrame:
    """Generate a table of observations and return as if it was an EFD
    query.

    Returns
    -------
    pandas.DataFrame
        Observation table.
    """

    schema_converter = SchemaConverter()

    opsim_database = FeatureScheduler.default_observation_database_name

    if not opsim_database.exists():
        raise RuntimeError(f"No opsim database in {opsim_database!r}")

    observations = schema_converter.opsim2obs(opsim_database.as_posix())

    fbs_observation_keyword = list(
        FeatureScheduler.fbs_observation_named_parameter_map()
    )

    additional_keywords = [
        keyword
        for keyword in observations.dtype.names
        if keyword not in fbs_observation_keyword
    ]
    data = []

    for observation in observations:
        properties = [observation[keyword] for keyword in fbs_observation_keyword]
        additional_properties = dict(
            zip(
                additional_keywords,
                [str(observation[keyword]) for keyword in additional_keywords],
            )
        )
        properties.append(yaml.safe_dump(additional_properties))
        data.append(properties)
    columns = [
        FeatureScheduler.fbs_observation_named_parameter_map()[key]
        for key in fbs_observation_keyword
    ] + ["additionalInformation"]

    return pandas.DataFrame(
        data=data,
        columns=columns,
    )
