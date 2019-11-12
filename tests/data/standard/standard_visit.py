#!/usr/bin/env python
__all__ = ["StandardVisit"]

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
        super().__init__(index=index, descr=descr,
                         remotes_dict={})

        self.targetid = 0
        self.fieldid = 0
        self.filter = None
        self.ra = None
        self.dec = None
        self.ang = None
        self.num_exp = 0
        self.exp_times = []

    async def configure(self, targetid=0, fieldid=0, band_filter="",
                        ra=0.0, dec=0.0, ang=0.0,
                        num_exp=0, exp_times=[]):
        """Configure the script.


        Parameters
        ----------
        targetid : int
            A unique identifier for the given target.
        fieldid : int
            The ID of the associated OpSim field for the target.
        band_filter : str
            The single character name of the associated band filter.
        ra : float
            The right ascension (degrees) of the target.
        dec : float
            The declination (degrees) of the target.
        ang : float
            The sky angle (degrees) of the target.
        num_exp : int
            The number of requested exposures for the target.
        exp_times : list[float]
            The set of exposure times for the target. Needs to length
            of num_exp.

        Raises
        ------
        salobj.ExpectedError
            If ``wait_time < 0``. This can be used to make config fail.
        """

        self.log.info("Configure started")

        self.targetid = targetid
        self.fieldid = fieldid
        self.filter = band_filter
        self.ra = ra
        self.dec = dec
        self.ang = ang
        self.num_exp = num_exp
        self.exp_times = list(exp_times)

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
    StandardVisit.main(descr="Mock standard visit.")
