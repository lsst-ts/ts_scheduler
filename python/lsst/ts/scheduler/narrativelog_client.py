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

__all__ = ["NarrativelogClient"]

import logging

import requests


class NarrativelogClient:
    """A class to handle requests to the Narrativelog REST API.

    Parameters
    ----------
    host : `str`
        The host address of the Narrativelog REST API.
    log : `logging.Logger`, optional
        Logger instance.
    """

    def __init__(
        self,
        host: str,
        log: logging.Logger | None = None,
    ) -> None:

        self.log = (
            logging.getLogger(type(self).__name__)
            if log is None
            else log.getChild(type(self).__name__)
        )
        self.host = host

    def add_message(self, data: dict) -> None:
        """Add a message to the narrative log.

        Parameters
        ----------
        data : `dict`
            The data to add to the narrative log.
        """
        url = f"https://{self.host}/narrativelog/message"
        try:
            response = requests.post(
                url,
                json={
                    **data,
                    "is_human": False,
                    "user_id": "Scheduler",
                    "user_agent": "Scheduler",
                },
            )
            response.raise_for_status()
            message_id = response.json().get("id")
            self.log.info(
                f"Message with ID {message_id} added to narrative log successfully."
            )
        except requests.exceptions.RequestException as e:
            self.log.error(f"Failed to add message to narrative log: {e}")
