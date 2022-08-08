#!/usr/bin/env python
__all__ = ["StandardVisit"]

import asyncio

import yaml
from lsst.ts.salobj import BaseScript


class StandardVisit(BaseScript):
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

        self.targetid = 0
        self.fieldid = 0
        self.filter = None
        self.ra = None
        self.dec = None
        self.ang = None
        self.num_exp = 0
        self.exp_times = []

    @classmethod
    def get_schema(cls):
        schema_yaml = """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/develop/tests/data/standard/standard_visit.py
title: StandardVisit v1
description: Configuration for StandardVisit.
type: object
properties:
    target_id:
        description: A unique identifier for the given target.
        type: integer
        default: 0
    fieldid:
        description: The ID of the associated OpSim field for the target.
        type: integer
        default: 0
    ra:
        type: number
        description: The right ascension (degrees) of the target.
        default: 0.
    dec:
        type: number
        description: The declination (degrees) of the target.
        default: 0.
    name:
        type: string
        description: Target name.
        default: non_standard_visit_target
    program:
        type: string
        description: Program.
        default: ""
    ang:
        type: number
        description: The sky angle (degrees) of the target.
        default: 0.
    instrument_setup:
        type: array
        items:
            type: object
            additionalProperties: false
            required:
                - exptime
                - filter
            properties:
                exptime:
                    type: number
                filter:
                    type: string
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script."""

        self.log.info("Configure started")

        self.target_id = config.target_id
        self.fieldid = config.fieldid
        self.ra = config.ra
        self.dec = config.dec
        self.ang = config.ang
        self.instrument_setup = config.instrument_setup

        self.log.info("Configure succeeded")

    def set_metadata(self, metadata):
        """Fill in metadata information.

        Parameters
        ----------
        metadata

        """
        metadata.duration = sum([setup["exptime"] for setup in self.instrument_setup])

    async def run(self):
        """Mock standard visit."""

        self.log.info("Run started")
        await self.checkpoint("start")

        self.log.info("Mocking exposure")
        await asyncio.sleep(1.0)

        await self.checkpoint("end")
        self.log.info("Run succeeded")


if __name__ == "__main__":
    asyncio.run(StandardVisit.amain())
