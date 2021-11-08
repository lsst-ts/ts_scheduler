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

import astropy
import pandas
import unittest
import warnings

import numpy as np

from typing import List, Any, Union

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


def get_mock_efd_client(efd_name: str) -> unittest.mock.AsyncMock:
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

    mock_efd_client = unittest.mock.AsyncMock()

    mock_efd_client.configure_mock(
        **{
            "select_time_series.side_effect": mock_select_time_series,
            "get_topics.side_effect": mock_get_topics,
            "get_fields.side_effect": mock_get_fields,
        },
    )

    mock_efd_client.attach_mock(
        unittest.mock.Mock(
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

    index = pandas.date_range(
        start=start.datetime,
        end=end.datetime,
        periods=number_of_data_points,
    )

    data = np.random.rand(number_of_data_points, len(fields))

    result = pandas.DataFrame(
        data=data,
        index=index,
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
