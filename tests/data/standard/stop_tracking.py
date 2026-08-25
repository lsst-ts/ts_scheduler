#!/usr/bin/env python
# This file is part of ts-scheduler.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["StopTracking"]

import asyncio

from lsst.ts.salobj import BaseScript


class StopTracking(BaseScript):
    """A dummy stop tracking script to test the scheduler interaction with
    the queue.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Wait for the specified time, then exit. See `configure` for details.
    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index, descr=""):
        super().__init__(index=index, descr=descr)
        self.sleep_time = 1.0

    @classmethod
    def get_schema(cls):
        return None

    async def configure(self, config):
        """Configure the script."""
        pass

    def set_metadata(self, metadata):
        """Fill in metadata information.

        Parameters
        ----------
        metadata

        """
        metadata.duration = self.sleep_time

    async def run(self):
        """Mock standard visit."""

        self.log.info("Run started")
        await self.checkpoint("start")

        self.log.info("Mocking stop tracking")
        await asyncio.sleep(self.sleep_time)

        await self.checkpoint("end")
        self.log.info("Run succeeded")


if __name__ == "__main__":
    asyncio.run(StopTracking.amain())
