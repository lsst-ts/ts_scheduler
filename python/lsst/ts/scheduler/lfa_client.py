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

__all__ = ["LFAClient"]

import logging
import pathlib
from urllib.parse import urlparse

import aiohttp
import h5py
import lsst_efd_client
from astropy import units
from astropy.time import Time, TimeDelta


class DreamCloudMap:
    """Class to handle DREAM cloud maps."""

    def __init__(self, clouds) -> None:
        self.clouds = clouds

    @classmethod
    def from_file(cls, filename):
        data = h5py.File(filename, "r")
        return cls(clouds=data["clouds"][:])


class LFAClient:
    """A class to handle retrieving telemetry in the form of
    a Large File Annex object.

    Parameters
    ----------
    source : `str`
        The name of the component that is generating the LFA
        data.
    delta_time : `float`
        How long in the past to look for data.
    efd_name : `str`
        Name of the EFD instance events should be queried from.
    db_name : `str`, optional
        The database name where the event is written (Default, efd).
    log : `logging.Logger`, optional
        Logger class.
    """

    def __init__(
        self,
        source: str,
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
        self.source = source
        self.delta_time = delta_time
        self.efd_client = lsst_efd_client.EfdClient(
            efd_name,
            db_name=db_name,
        )

        self.lfa_data: dict[str, DreamCloudMap] = dict()
        self.latest_update: Time | None = None

    async def retrieve_lfa_data(self) -> dict[str, DreamCloudMap]:
        await self._update_lfa_data()

        return self.lfa_data

    async def _update_lfa_data(self) -> None:
        """Update the list of LFA Data."""

        time_query_end = Time.now()
        time_query_start = (
            (time_query_end - TimeDelta(self.delta_time * units.second))
            if self.latest_update is None
            else self.latest_update
        )

        efd_data = await self.efd_client.select_time_series(
            f"lsst.sal.{self.source}.logevent_largeFileObjectAvailable",
            ["url"],
            start=time_query_start,
            end=time_query_end,
        )

        self.latest_update = time_query_end

        if efd_data.empty:
            return

        for url in efd_data.url:

            save_path = get_filename_from_url(url)

            save_path_name = save_path.name

            if not save_path.exists():
                await retrieve_lfa_file(url=url, save_path=save_path_name)

            self.lfa_data[save_path_name] = DreamCloudMap.from_file(save_path_name)


async def retrieve_lfa_file(url, save_path):
    """Retrieve file from the LFA server.

    Parameters
    ----------
    url : `str`
        Url address to retrieve file.
    save_path : `str`
        Location to store the file.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            with open(save_path, "wb") as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)


def get_filename_from_url(url):
    return pathlib.PosixPath(urlparse(url).path)
