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

__all__ = ["TooClient"]

import dataclasses
import logging

import healpy as hp
import lsst_efd_client
import numpy as np
from astropy import units
from astropy.time import Time, TimeDelta
from lsst.ts.utils import index_generator
from numpy.typing import NDArray


@dataclasses.dataclass
class TooAlert:
    """Data structure with the Target of opportunity alert payload."""

    source: str
    """A unique identifier for this event"""

    tooid: int
    """Unique identifier of the ToO."""

    instrument: list[str]
    """A list of names of instruments responsible for the
    observations which lead to issuing this alert"""

    alert_type: str
    """The categorization of this alert,
    defined by which filter criteria it passed"""

    event_trigger_timestamp: str
    """The UTC time of the event described by the alert
    in ISO-8601 format"""

    reward_map: NDArray[np.bool]
    """The pixels of a HEALPix map, in the nested ordering,
    with binary values indicating whether they should be
    targeted for observation"""

    reward_map_nside: int
    """The n_side parameter describing the resolution of the
    map data in reward_map"""

    is_test: bool
    """A flag indicating whether the event is a test or
    simulated alert"""

    is_update: bool
    """A flag indicating that this is an update to a previous
    version of the same event"""


class TooClient:
    """Handle Target of Oportunity alerts.

    Parameters
    ----------
    topic_name : `str`
        The name of the topic with the ToO data in the EFD.
    delta_time : `float`
        How long in the past to look for ToO alerts?
        Older alerts will be ignored.
    efd_name : `str`
        Name of the EFD instance alerts should be queried from.
    db_name : `str`, optional
        The database name where the topic is written (Default, efd).
    log : `logging.Logger`, optional
        Logger class.
    """

    def __init__(
        self,
        topic_name: str,
        delta_time: float,
        efd_name: str,
        db_name: str = "efd",
        log: logging.Logger | None = None,
    ) -> None:

        self.log = (
            logging.getLogger(type(self).__name__)
            if log is None
            else log.getChild(type(self).__name__)
        )
        self.topic_name = topic_name
        self.delta_time = delta_time
        self.efd_client = lsst_efd_client.EfdClient(
            efd_name,
            db_name=db_name,
        )

        self.too_alerts: dict[str, TooAlert] = dict()
        self.latest_update: Time | None = None

        self._index_generator = index_generator()

    def get_initial_query_parameters(self) -> list[str]:
        """Return the initial query parameters for the ToO Alert."""
        return [
            "source",
            "alert_type",
            "event_trigger_timestamp",
            "reward_map_nside",
            "is_test",
            "is_update",
        ]

    async def get_too_alerts(self) -> dict[str, TooAlert]:
        """Retrieve target of opportunity alerts from the EFD.

        Returns
        -------
        too_alerts : `dict`[`str`, `TooAlert`]
            Target of opportunity alerts.
        """
        await self._update_too_alerts()

        return self.too_alerts

    async def _update_too_alerts(self) -> None:
        """Update the ToO Alert information."""

        time_query_end = Time.now()
        time_query_start = (
            (time_query_end - TimeDelta(self.delta_time * units.second))
            if self.latest_update is None
            else self.latest_update
        )

        efd_data = await self.efd_client.select_time_series(
            self.topic_name,
            self.get_initial_query_parameters(),
            start=time_query_start,
            end=time_query_end,
        )

        self.latest_update = time_query_end

        if efd_data.empty:
            return

        for (
            source,
            alert_type,
            event_trigger_timestamp,
            reward_map_nside,
            is_test,
            is_update,
        ) in zip(
            efd_data.source,
            efd_data.alert_type,
            efd_data.event_trigger_timestamp,
            efd_data.reward_map_nside,
            efd_data.is_test,
            efd_data.is_update,
        ):

            self.log.info(
                f"Retrieving target of opportunity reward map for {source=}, {alert_type=}."
            )

            reward_map = await self._retrieve_reward_map(
                time_query_start=time_query_start,
                time_query_end=time_query_end,
                source=source,
                nside=reward_map_nside,
            )

            tooid = (
                next(self._index_generator)
                if source not in self.too_alerts
                else self.too_alerts[source].tooid
            )

            too_alert = TooAlert(
                source=source,
                tooid=tooid,
                alert_type=alert_type,
                event_trigger_timestamp=event_trigger_timestamp,
                reward_map_nside=reward_map_nside,
                is_test=is_test,
                is_update=is_update,
                instrument=[],
                reward_map=reward_map,
            )

            self.too_alerts[source] = too_alert

    async def _retrieve_reward_map(
        self, time_query_start: Time, time_query_end: Time, source: str, nside: int
    ) -> NDArray[np.bool]:
        """Retrieve the reward map for the specified event.

        Parameters
        ----------
        time_query_start : `Time`
            Start time for the query.
        time_query_end : `Time`
            End time for the query.
        source : `str`
            The unique identifier for the source.
        nside : `int`
            The healpix map resolution.

        Returns
        -------
        `NDArray`[`bool`]
            The reward map for the event.
        """
        npix = hp.nside2npix(nside)
        reward_map_query = self.efd_client.build_time_range_query(
            self.topic_name,
            [f"reward_map{i}" for i in range(npix)],
            start=time_query_start,
            end=time_query_end,
        )
        reward_map_query += f" AND source = '{source}'"
        reward_map = await self.efd_client._do_query(reward_map_query)
        return (
            reward_map.to_numpy()[-1][[hp.ring2nest(nside, i) for i in range(npix)]]
            if not reward_map.empty
            else np.zeros(npix, dtype=np.bool)
        )
