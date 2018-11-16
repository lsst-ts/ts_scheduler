
import asyncio
import os
import unittest
import warnings

import SALPY_Script
import SALPY_ScriptQueue
import lsst.ts.salobj as salobj
from lsst.ts import scriptqueue
from lsst.ts.scheduler import SchedulerCSC

I0 = scriptqueue.script_queue.SCRIPT_INDEX_MULT  # initial Script SAL index


class SimpleTargetLoopTestCase(unittest.TestCase):
    """This unit test is designed to test the interaction of the simple target production loop of the Scheduler CSC
    with the LSST Queue.

    """
    def setUp(self):
        salobj.test_utils.set_random_lsst_dds_domain()
        self.datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        standardpath = os.path.join(self.datadir, "standard")
        externalpath = os.path.join(self.datadir, "external")
        self.queue = scriptqueue.ScriptQueue(index=1,
                                             standardpath=standardpath,
                                             externalpath=externalpath)
        self.queue.summary_state = salobj.State.DISABLED
        self.queue_remote = salobj.Remote(SALPY_ScriptQueue, index=1)
        self.process = None

        self.scheduler = SchedulerCSC(index=1)
        self.scheduler.parameters.mode = 'SIMPLE'

    def test_simple_loop(self):
        """Test the simple target production loop."""

        # Test 1 - Queue is not enable. Scheduler should go to a fault state



if __name__ == "__main__":
    unittest.main()
