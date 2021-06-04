# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
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

import asyncio
import os
import glob
import logging
import pathlib
import unittest

from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.mock import ObservatoryStateMock
from lsst.ts.scheduler.utils.error_codes import OBSERVATORY_STATE_UPDATE

SHORT_TIMEOUT = 5.0
LONG_TIMEOUT = 30.0
LONG_LONG_TIMEOUT = 120.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")

logging.basicConfig()


class TestSchedulerCSC(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        self.assertEqual(initial_state, salobj.State.STANDBY)

        return SchedulerCSC(
            index=1, config_dir=config_dir, simulation_mode=simulation_mode
        )

    async def test_fail_no_observatory_state(self):
        """Test CSC goes to FAULT if no observatory state."""

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=1,
        ):

            try:
                self.remote.evt_summaryState.flush()

                try:
                    await self.remote.cmd_start.start(timeout=LONG_TIMEOUT)
                except asyncio.TimeoutError:
                    pass

                self.assert_next_summary_state(salobj.State.DISABLED, flush=False)

                self.assert_next_summary_state(salobj.State.FAULT, flush=False)

                # Check error code
                error_code = await self.remote.evt_errorCode.aget(timeout=SHORT_TIMEOUT)
                self.assertEqual(error_code.errorCode, OBSERVATORY_STATE_UPDATE)
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_standard_state_transitions(self):
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=1,
        ), ObservatoryStateMock():

            await self.check_standard_state_transitions(
                enabled_commands=("resume", "stop", "load"),
            )

    async def test_configuration(self):
        """Test basic configuration."""
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=1,
        ), ObservatoryStateMock():
            try:
                self.assertEqual(self.csc.summary_state, salobj.State.STANDBY)
                state = await self.remote.evt_summaryState.next(
                    flush=False, timeout=LONG_TIMEOUT
                )
                self.assertEqual(state.summaryState, salobj.State.STANDBY)

                invalid_files = glob.glob(
                    os.path.join(TEST_CONFIG_DIR, "invalid_*.yaml")
                )
                bad_config_names = [os.path.basename(name) for name in invalid_files]
                bad_config_names.append("no_such_file.yaml")
                for bad_config_name in bad_config_names:
                    with self.subTest(bad_config_name=bad_config_name):
                        self.remote.cmd_start.set(settingsToApply=bad_config_name)
                        with salobj.testutils.assertRaisesAckError():
                            await self.remote.cmd_start.start(timeout=SHORT_TIMEOUT)

                self.remote.cmd_start.set(settingsToApply="all_fields")
                await self.remote.cmd_start.start(timeout=SHORT_TIMEOUT)
                self.assertEqual(self.csc.summary_state, salobj.State.DISABLED)
                state = await self.remote.evt_summaryState.next(
                    flush=False, timeout=SHORT_TIMEOUT
                )
                self.assertEqual(state.summaryState, salobj.State.DISABLED)
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)

    async def test_load(self):
        """Test load command."""
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
            simulation_mode=1,
        ), ObservatoryStateMock():
            config = (
                pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "test_observing_list.yaml")
            )

            bad_config = (
                pathlib.Path(__file__)
                .parents[1]
                .joinpath("tests", "data", "bad_config.yaml")
            )

            try:
                await salobj.set_summary_state(self.remote, salobj.State.ENABLED)

                await self.remote.cmd_load.set_start(
                    uri=config.as_uri(), timeout=SHORT_TIMEOUT
                )

                with salobj.assertRaisesAckError():
                    await self.remote.cmd_load.set_start(
                        uri=bad_config.as_uri(), timeout=SHORT_TIMEOUT
                    )
            finally:
                await salobj.set_summary_state(self.remote, salobj.State.STANDBY)


if __name__ == "__main__":
    unittest.main()
