#!/usr/bin/env python
__all__ = ["StandardVisit"]

import yaml
import asyncio

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
    band_filter:
        anyOf:
            - type: array
                minItems: 1
                items:
                type: string
            - type: string
        description: The single character name of the associated band filter.
        default: ""
    ra:
        type: number
        description: The right ascension (degrees) of the target.
        default: 0.
    dec:
        type: number
        description: The declination (degrees) of the target.
        default: 0.
    ang:
        type: number
        description: The sky angle (degrees) of the target.
        default: 0.
    num_exp:
        type: integer
        description: The number of requested exposures for the target.
        default:  0
    exp_times:
        type: array
        items:
            type: number
        description: The set of exposure times for the target. Needs to length of num_exp.
        default: []
    program:
        type: string
        description: Program.
        default: ""
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script."""

        self.log.info("Configure started")

        self.targetid = config.targetid
        self.fieldid = config.fieldid
        self.filter = config.band_filter
        self.ra = config.ra
        self.dec = config.dec
        self.ang = config.ang
        self.num_exp = config.num_exp
        self.exp_times = config.exp_times

        self.log.info("Configure succeeded")

    def set_metadata(self, metadata):
        """Fill in metadata information.

        Parameters
        ----------
        metadata

        """
        metadata.duration = sum(self.exp_times)

    async def run(self):
        """Mock standard visit."""

        self.log.info("Run started")
        await self.checkpoint("start")

        self.log.info("Mocking exposure")
        await asyncio.sleep(sum(self.exp_times))

        await self.checkpoint("end")
        self.log.info("Run succeeded")


if __name__ == "__main__":
    asyncio.run(StandardVisit.amain())
