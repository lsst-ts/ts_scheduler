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
import contextlib
import logging
import pathlib
import typing
import unittest

from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.utils import SchedulerModes
from lsst.ts.scheduler.utils.test.feature_scheduler_sim import FeatureSchedulerSim

SHORT_TIMEOUT = 5.0
LONG_TIMEOUT = 30.0
LONG_LONG_TIMEOUT = 120.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class TestSchedulerCscColdStart(
    salobj.BaseCscTestCase,
    unittest.IsolatedAsyncioTestCase,
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestSchedulerCSC")

    def setUp(self) -> None:
        self.scheduler_config_path = TEST_CONFIG_DIR / "fbs_config_good.py"
        self.driver_type = "feature_scheduler"

        return super().setUp()

    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return SchedulerCSC(
            index=1,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

    async def wait_lifeness(self):
        try:
            await self.remote.evt_heartbeat.next(flush=True, timeout=LONG_TIMEOUT)
        except asyncio.TimeoutError:
            raise RuntimeError(f"No heartbeats from CSC after {LONG_TIMEOUT}s.")

    @contextlib.contextmanager
    def generate_configuration_override(
        self,
        startup_database: str,
        scheduler_config_path: str,
    ) -> typing.Generator[pathlib.Path, None, None]:
        configuration_override = TEST_CONFIG_DIR / "fbs_test_cold_start.yaml"

        try:
            with open(configuration_override, "w") as fp:
                configuration = self._get_configuration(
                    startup_database=startup_database,
                    scheduler_config_path=scheduler_config_path,
                )
                fp.write(configuration)

            yield configuration_override
        finally:
            if configuration_override.exists():
                configuration_override.unlink()

    @contextlib.contextmanager
    def generate_scheduler_database(self) -> typing.Generator[pathlib.Path, None, None]:
        feature_scheduler_sim = FeatureSchedulerSim(self.log)

        feature_scheduler_sim.configure_scheduler_for_test_with_cwfs(TEST_CONFIG_DIR)

        observation_database_path = (
            feature_scheduler_sim.config.feature_scheduler_driver_configuration[
                "observation_database_name"
            ]
        )

        try:
            feature_scheduler_sim.run_observations(register_observations=True)

            yield observation_database_path
        finally:
            if observation_database_path.exists():
                observation_database_path.unlink()

    @contextlib.contextmanager
    def generate_scheduler_efd_database(self) -> typing.Generator[str, None, None]:
        feature_scheduler_sim = FeatureSchedulerSim(self.log)

        feature_scheduler_sim.configure_scheduler_for_test_with_cwfs_standard_obs_database(
            TEST_CONFIG_DIR
        )

        try:
            observations = feature_scheduler_sim.run_observations(
                register_observations=True
            )
            self.expected_number_of_targets = len(observations)

            # Select all samples of observation event from Main Telescope
            # Scheduler (SchedulerID = 1).
            yield (
                'SELECT * FROM "efd"."autogen"."lsst.sal.Scheduler.logevent_observation" WHERE '
                "SchedulerID = 1"
            )
        finally:
            if self.csc.model.driver.observation_database_name.exists():
                self.csc.model.driver.observation_database_name.unlink()

    def _get_configuration(
        self, startup_database: str, scheduler_config_path: str
    ) -> str:
        return f"""
maintel:
  mode: ADVANCE
  startup_type: COLD
  startup_database: >-
    {startup_database}
  driver_type: {self.driver_type}
  {self.driver_type}_driver_configuration:
    scheduler_config: {scheduler_config_path}
  telemetry:
    efd_name: summit_efd
    streams:
      - name: seeing
        efd_table: lsst.sal.DIMM.logevent_dimmMeasurement
        efd_columns:
          - fwhm
        efd_delta_time: 300.0
        fill_value: null
      - name: wind_speed
        efd_table: lsst.sal.WeatherStation.windSpeed
        efd_columns:
          - avg2M
        efd_delta_time: 300.0
        fill_value: null
      - name: wind_direction
        efd_table: lsst.sal.WeatherStation.windDirection
        efd_columns:
          - avg2M
        efd_delta_time: 300.0
        fill_value: null
"""

    async def test_no_startup_db(self):
        with self.generate_configuration_override(
            startup_database=" ",
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ):
                await self.wait_lifeness()

                with self.assertLogs(self.csc.log, level=logging.DEBUG) as csc_logs:
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

                assert (
                    f"INFO:Scheduler.Model:Loading driver {self.driver_type}"
                    in csc_logs.output
                )
                assert (
                    "INFO:Scheduler.Model:No observation history information provided."
                    in csc_logs.output
                )

    async def test_with_startup_db(self):
        with self.generate_scheduler_database() as startup_database, self.generate_configuration_override(
            startup_database=startup_database.as_posix(),
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ):
                await self.wait_lifeness()

                with self.assertLogs(self.csc.log, level=logging.DEBUG) as csc_logs:
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

                assert (
                    f"INFO:Scheduler.Model:Loading driver {self.driver_type}"
                    in csc_logs.output
                )
                assert (
                    "INFO:Scheduler.Model:Loading observation history from database: "
                    f"{startup_database.as_posix()}." in csc_logs.output
                )

    async def test_with_inexistent_startup_db(self):
        with self.generate_scheduler_database() as startup_database, self.generate_configuration_override(
            startup_database=startup_database.as_posix(),
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            if startup_database.exists():
                startup_database.unlink()

            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ):
                await self.wait_lifeness()

                expected_error_msg = (
                    "ERROR:Scheduler.Model:Specified startup database does not exists "
                    "and does not classify as an EFD query. "
                    f"Received: {startup_database}. "
                    "If this was supposed to be a path, it must be local to the CSC environment. "
                    "If this was supposed to be an EFD query, it should have the format: "
                    'SELECT * FROM "efd"."autogen"."lsst.sal.Scheduler.logevent_observation" WHERE '
                    "time >= '2021-06-09T00:00:00.000+00:00' AND time <= '2021-06-12T00:00:00.000+00:00'"
                )

                with self.assertLogs(
                    self.csc.log, level=logging.ERROR
                ) as csc_logs, self.assertRaises(RuntimeError):
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

                assert expected_error_msg in csc_logs.output

    async def test_with_efd_query(self):
        with self.generate_scheduler_efd_database() as startup_database, self.generate_configuration_override(
            startup_database=startup_database,
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            self.log.debug(f"startup database: {startup_database}")

            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ):
                await self.wait_lifeness()

                with self.assertLogs(self.csc.log, level=logging.DEBUG) as csc_logs:
                    try:
                        await salobj.set_summary_state(
                            remote=self.remote,
                            state=salobj.State.DISABLED,
                            override=override_path.name,
                        )
                    except Exception:
                        for record, message in zip(csc_logs.records, csc_logs.output):
                            self.log.log(record.levelno, message)
                        raise

                assert (
                    f"INFO:Scheduler.Model:Loading driver {self.driver_type}"
                    in csc_logs.output
                )
                assert (
                    "INFO:Scheduler.Model:Loading observation history from EFD. "
                    f"Query: {startup_database} yield {self.expected_number_of_targets} targets."
                    in csc_logs.output
                )

    async def test_load_twice(self):
        with self.generate_configuration_override(
            startup_database="",
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ):
                await self.wait_lifeness()

                with self.assertLogs(self.csc.log, level=logging.DEBUG) as csc_logs:
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.STANDBY,
                        override=override_path.name,
                    )

                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

                for log in csc_logs.output:
                    self.log.debug(log)

                assert (
                    f"INFO:Scheduler.Model:Loading driver {self.driver_type}"
                    in csc_logs.output
                )
                assert (
                    len(
                        [
                            log
                            for log in csc_logs.output
                            if log
                            == f"INFO:Scheduler.Model:Loading driver {self.driver_type}"
                        ]
                    )
                    == 2
                )
                assert (
                    "WARNING:Scheduler.Model:COLD start: driver already defined. "
                    "Resetting driver." in csc_logs.output
                )
                assert (
                    len(
                        [
                            log
                            for log in csc_logs.output
                            if log
                            == (
                                "WARNING:Scheduler.Model:COLD start: driver already defined. "
                                "Resetting driver."
                            )
                        ]
                    )
                    == 1
                )
