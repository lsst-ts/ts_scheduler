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

        self.filter = None
        self.exp_times = []
        self.program = None
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
    exp_times:
        type: array
        description: Exposure times.
        items:
            type: number
    band_filter:
        type: string
        description: Filter.
    program:
        type: string
        description: Name of the program these observations are part of.
    note:
        type: string
        description: Note to attribute to these observations.
required:
    - exp_times
    - band_filter
    - program
additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        """Configure the script."""

        self.log.info("Configure started")

        self.filter = config.band_filter
        self.exp_times = config.exp_times
        self.program = config.program
        self.note = config.note

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
        await asyncio.sleep(1.0)

        await self.checkpoint("end")
        self.log.info("Run succeeded")


if __name__ == "__main__":
    asyncio.run(StandardVisit.amain())
