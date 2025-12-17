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

import contextlib
import importlib
import logging
import pathlib
import pickle
import unittest

from lsst.ts import salobj
from lsst.ts.scheduler import SchedulerCSC
from lsst.ts.scheduler.utils import SchedulerModes
from rubin_scheduler.scheduler.model_observatory import ModelObservatory
from rubin_scheduler.utils import SURVEY_START_MJD as MJD_START

SHORT_TIMEOUT = 5.0
LONG_TIMEOUT = 30.0
LONG_LONG_TIMEOUT = 120.0
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class TestSchedulerCscHotStart(
    salobj.BaseCscTestCase,
    unittest.IsolatedAsyncioTestCase,
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger("TestSchedulerCSC")

    def setUp(self) -> None:
        self.scheduler_config_path = TEST_CONFIG_DIR / "fbs_config_good.py"
        self.scheduler_config_path_cwfs = (
            TEST_CONFIG_DIR / "fbs_config_good_with_cwfs.py"
        )
        self.driver_type = "feature_scheduler"

        return super().setUp()

    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return SchedulerCSC(
            index=1,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

    @contextlib.contextmanager
    def generate_scheduler_snapshot(self) -> pathlib.Path:
        snapshot_file_path = TEST_CONFIG_DIR / "fbs_test_snapshot.p"

        try:
            self.log.info(
                f"Loading scheduler from: {self.scheduler_config_path_cwfs.as_posix()}"
            )

            spec = importlib.util.spec_from_file_location(
                "config", self.scheduler_config_path_cwfs.as_posix()
            )
            conf = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(conf)

            observatory = ModelObservatory(nside=conf.nside, mjd_start=MJD_START)
            observatory.sky_model.load_length = 3
            conditions = observatory.return_conditions()

            with open(snapshot_file_path, "wb") as fp:
                pickle.dump(
                    [
                        conf.scheduler,
                        conditions,
                        [],
                    ],
                    fp,
                )

            yield snapshot_file_path
        finally:
            if snapshot_file_path.exists():
                snapshot_file_path.unlink()

    @contextlib.contextmanager
    def generate_configuration_override(
        self,
        startup_database: str,
        scheduler_config_path: str,
    ) -> pathlib.Path:
        configuration_override = TEST_CONFIG_DIR / "fbs_test_hot_start.yaml"

        try:
            with open(configuration_override, "w") as fp:
                fp.write(
                    self._get_configuration(
                        startup_database=startup_database,
                        scheduler_config_path=scheduler_config_path,
                    )
                )

            yield configuration_override
        finally:
            if configuration_override.exists():
                configuration_override.unlink()

    def _get_configuration(
        self, startup_database: str, scheduler_config_path: str
    ) -> str:
        return f"""
maintel:
  mode: ADVANCE
  startup_type: HOT
  startup_database: "{startup_database}"
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

    @contextlib.asynccontextmanager
    async def make_script_queue(self, running: bool) -> None:
        self.log.debug("Make queue.")
        async with salobj.Controller("ScriptQueue", index=1) as queue:

            async def show_schema(data) -> None:
                self.log.debug(f"Show schema: {data}")
                await queue.evt_configSchema.set_write(
                    path=data.path,
                    isStandard=data.isStandard,
                    configSchema="""
$schema: http://json-schema.org/draft-07/schema#
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
additionalProperties: true
                    """,
                )

            queue.cmd_showSchema.callback = show_schema
            await queue.evt_queue.set_write(running=running)
            yield

    async def test_no_startup_db(self):
        with self.generate_configuration_override(
            startup_database="",
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ), self.make_script_queue(running=True):
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
                    "DEBUG:Scheduler.Model:No scheduler snapshot provided."
                    in csc_logs.output
                )

    async def test_with_startup_db(self):
        with self.generate_scheduler_snapshot() as startup_database, self.generate_configuration_override(
            startup_database=startup_database.as_uri(),
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ), self.make_script_queue(running=True):
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
                    f"INFO:Scheduler.Model:Loading scheduler snapshot from {startup_database.as_uri()}."
                    in csc_logs.output
                )

    async def test_with_nonexistent_startup_db(self):
        with self.generate_scheduler_snapshot() as startup_database, self.generate_configuration_override(
            startup_database=startup_database.as_uri(),
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            startup_database.unlink()

            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ), self.make_script_queue(running=True):
                expected_exception_text = (
                    f"Could not retrieve {startup_database.as_uri()}. "
                    "Make sure it is a valid and accessible URI."
                )

                with self.assertRaisesRegex(
                    RuntimeError, expected_regex=expected_exception_text
                ):
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
                    )

    async def test_with_malformed_startup_db(self):
        startup_database = "malformed/filename.p"

        with self.generate_configuration_override(
            startup_database=startup_database,
            scheduler_config_path=self.scheduler_config_path.as_posix(),
        ) as override_path:
            async with self.make_csc(
                config_dir=TEST_CONFIG_DIR,
                initial_state=salobj.State.STANDBY,
                simulation_mode=SchedulerModes.MOCKS3,
            ), self.make_script_queue(running=True):
                expected_exception_text = (
                    f"Invalid startup_database: {startup_database}. "
                    "Make sure it is a valid and accessible URI."
                )

                with self.assertRaisesRegex(
                    RuntimeError, expected_regex=expected_exception_text
                ):
                    await salobj.set_summary_state(
                        remote=self.remote,
                        state=salobj.State.DISABLED,
                        override=override_path.name,
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
            ), self.make_script_queue(running=True):
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
                    == 1
                )
                assert (
                    "DEBUG:Scheduler.Model:No scheduler snapshot provided."
                    in csc_logs.output
                )
                assert (
                    len(
                        [
                            log
                            for log in csc_logs.output
                            if log
                            == "DEBUG:Scheduler.Model:No scheduler snapshot provided."
                        ]
                    )
                    == 1
                )
                assert (
                    "WARNING:Scheduler.Model:HOT start: driver already defined. "
                    "Skipping driver configuration." in csc_logs.output
                )
