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

__all__ = ["CWFS"]

import asyncio

import yaml
from lsst.ts.salobj import BaseScript


class CWFS(BaseScript):
    """A dummy non standard visit script to test the scheduler interaction with
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

        self.config = None

    @classmethod
    def get_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/develop/tests/data/standard/standard_visit.py
title: StandardVisit v1
description: Configuration for StandardVisit.
type: object
properties:
  program:
    type: string
    description: Name of the program these observations are part of.
  find_target:
    type: object
    additionalProperties: false
    required:
      - az
      - el
      - mag_limit
    description: >-
        Optional configuration section. Find a target to perform CWFS in the given
        position and magnitude range. If not specified, the step is ignored.
    properties:
      az:
        type: number
        description: Azimuth (in degrees) to find a target.
      el:
        type: number
        description: Elevation (in degrees) to find a target.
      mag_limit:
        type: number
        description: Minimum (brightest) V-magnitude limit.
required:
  - find_target
  - program
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script."""

        self.config = config

    def set_metadata(self, metadata):
        """Fill in metadata information.

        Parameters
        ----------
        metadata

        """
        pass

    async def run(self):
        """Mock cwfs."""
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(CWFS.amain())
