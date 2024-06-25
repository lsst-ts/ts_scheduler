#!/usr/bin/env python
__all__ = ["Slew"]

import asyncio

import yaml
from lsst.ts.salobj import BaseScript


class Slew(BaseScript):
    """A dummy standard visit script to test the scheduler interaction with
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

        self.name = ""
        self.ra = None
        self.dec = None
        self.rot_sky = None
        self.estimated_slew_time = 0.0
        self.obs_time = 0.0
        self.note = ""

    @classmethod
    def get_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/develop/tests/data/standard/standard_visit.py
title: StandardVisit v1
description: Configuration for StandardVisit.
type: object
properties:
    name:
        type: string
        description: Target name.
    ra:
        type: string
        description: >-
            The right ascension of the target in hexagesimal format,
            e.g. HH:MM:SS.S.
    dec:
        type: string
        description: >-
            The declination of the target in hexagesimal format,
            e.g. DD:MM:SS.S.
    rot_sky:
        type: number
        description: The sky angle (degrees) of the target.
    estimated_slew_time:
        type: number
        description: Estimated slew time (seconds).
        default: 0.
    obs_time:
        type: number
        description: Estimated observing time (seconds).
        default: 0.
    note:
        type: string
        description: Survey note.
        default: ""
required:
    - name
    - ra
    - dec
    - rot_sky
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script."""

        self.log.info("Configure started")

        self.name = config.name
        self.ra = config.ra
        self.dec = config.dec
        self.rot_sky = config.rot_sky
        self.estimated_slew_time = config.estimated_slew_time
        self.obs_time = config.obs_time
        self.note = config.note

        self.log.info("Configure succeeded")

    def set_metadata(self, metadata):
        """Fill in metadata information.

        Parameters
        ----------
        metadata
            Script metadata.
        """
        metadata.duration = self.estimated_slew_time + self.obs_time

    async def run(self):
        """Mock standard visit."""

        self.log.info("Run started")
        await self.checkpoint("start")

        self.log.info("Mocking exposure")
        await asyncio.sleep(1.0)

        await self.checkpoint("end")
        self.log.info("Run succeeded")


if __name__ == "__main__":
    asyncio.run(Slew.amain())
