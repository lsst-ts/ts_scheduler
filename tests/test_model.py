# This file is part of ts_scheduler
#
# Developed for the Vera Rubin Observatory Telescope and Site Systems.
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

import logging
import pathlib
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import yaml
from lsst.ts.idl.enums.Script import ScriptState
from lsst.ts.salobj import DefaultingValidator
from lsst.ts.scheduler.driver.driver_target import DriverTarget
from lsst.ts.scheduler.model import Model
from lsst.ts.scheduler.utils.csc_utils import BlockStatus
from lsst.ts.scheduler.utils.types import ValidationRules

TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


@patch.multiple(
    Model,
    update_telemetry=AsyncMock(),
    synchronize_observatory_model=Mock(),
    register_scheduled_targets=Mock(),
    update_conditions=AsyncMock(),
    select_next_targets=AsyncMock(return_value=[None]),
)
class TestModel(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log = logging.getLogger()
        return super().setUpClass()

    def setUp(self) -> None:
        self.model = Model(log=self.log, config_dir=TEST_CONFIG_DIR)

        return super().setUp()

    async def test_configure(self) -> None:
        config = self.get_sample_configuration()

        await self.model.configure(config)

        assert self.model.max_scripts == config.max_scripts
        assert set(self.model.raw_telemetry.keys()) == {
            "scheduled_targets",
            "observing_queue",
        }
        assert self.model.models.keys() == {
            "location",
            "observatory_model",
            "observatory_state",
            "sky",
            "sky",
            "seeing",
            "cloud",
        }
        assert (
            set(self.model.observing_blocks.keys())
            == self.get_expected_observing_blocks()
        )
        assert self.model.driver is not None

    async def test_generate_target_queue_no_target(self) -> None:
        """Test for when select_next_targets returns no target in
        generate_target_queue.
        """

        n_targets = 0
        async for _ in self.model.generate_target_queue([], 5):
            n_targets += 1

        assert n_targets == 0

    async def test_load_observing_block(self) -> None:
        config = self.get_sample_configuration()

        await self.model.configure(config)

        await self.model.load_observing_blocks("../observing_blocks")

        observing_blocks_expected = self.get_expected_observing_blocks()

        assert self.model.observing_blocks.keys() == observing_blocks_expected

    async def test_validate_observing_blocks(self) -> None:
        config = self.get_sample_configuration()

        await self.model.configure(config)

        await self.model.load_observing_blocks("../observing_blocks")
        observing_scripts_config_validator = (
            self.get_observing_scripts_config_validator()
        )
        await self.model.validate_observing_blocks(observing_scripts_config_validator)

        for block_name in self.model.observing_blocks:
            for script in self.model.observing_blocks[block_name].scripts:
                if "name" in script.parameters:
                    assert script.parameters["name"] == "$name"

    async def test_scheduled_targets(self) -> None:
        config = self.get_sample_configuration()

        await self.model.configure(config)

        assert len(self.model.get_scheduled_targets()) == 0

        await self.model.load_observing_blocks("../observing_blocks")

        self.model.add_scheduled_target(
            target=DriverTarget(observing_block=self.model.observing_blocks["BLOCK-6"])
        )

        assert len(self.model.get_scheduled_targets()) == 1

        self.model.reset_scheduled_targets()

        assert len(self.model.get_scheduled_targets()) == 0

    async def test_check_scheduled_targets(self) -> None:
        config = self.get_sample_configuration()
        await self.model.configure(config=config)

        await self.model.load_observing_blocks("../observing_blocks")

        target = DriverTarget(observing_block=self.model.observing_blocks["BLOCK-6"])

        target.add_sal_index(10000)
        target.add_sal_index(10001)
        target.add_sal_index(10002)

        self.model.add_scheduled_target(target=target)

        # Targets still not on queue
        scheduled_target_info = await self.model.check_scheduled_targets()

        assert scheduled_target_info.failed == []
        assert scheduled_target_info.observed == []
        assert scheduled_target_info.unrecognized == []

        # Target 10000 in the queue
        await self.add_script(sal_index=10000)

        # 1 target in the queue
        scheduled_target_info = await self.model.check_scheduled_targets()

        assert scheduled_target_info.failed == []
        assert scheduled_target_info.observed == []
        assert scheduled_target_info.unrecognized == []

        # Targets 10001 and 10002 in the queue
        await self.add_script(sal_index=10001)
        await self.add_script(sal_index=10002)

        # all targets in the queue, all in unknown state
        scheduled_target_info = await self.model.check_scheduled_targets()

        assert scheduled_target_info.failed == []
        assert scheduled_target_info.observed == []
        assert scheduled_target_info.unrecognized == []
        assert len(self.model.script_info) == 3

        # targets done
        self.model.script_info[10000].scriptState = ScriptState.DONE
        self.model.script_info[10001].scriptState = ScriptState.DONE
        self.model.script_info[10002].scriptState = ScriptState.DONE

        scheduled_target_info = await self.model.check_scheduled_targets()

        assert scheduled_target_info.failed == []
        assert len(scheduled_target_info.observed) == 1
        assert scheduled_target_info.observed[0].get_sal_indices() == [
            10000,
            10001,
            10002,
        ]
        assert scheduled_target_info.unrecognized == []
        assert len(self.model.script_info) == 0
        assert len(self.model.get_scheduled_targets()) == 0

        target = DriverTarget(observing_block=self.model.observing_blocks["BLOCK-6"])

        target.add_sal_index(sal_index=10003)
        target.add_sal_index(sal_index=10004)
        target.add_sal_index(sal_index=10005)

        self.model.add_scheduled_target(target=target)

        await self.add_script(sal_index=10003)
        await self.add_script(sal_index=10004)
        await self.add_script(sal_index=10005)

        # One target failed
        self.model.script_info[10003].scriptState = ScriptState.DONE
        self.model.script_info[10004].scriptState = ScriptState.DONE
        self.model.script_info[10005].scriptState = ScriptState.FAILED

        scheduled_target_info = await self.model.check_scheduled_targets()

        assert len(scheduled_target_info.failed) == 1
        assert scheduled_target_info.failed[0].get_sal_indices() == [
            10003,
            10004,
            10005,
        ]
        assert scheduled_target_info.observed == []
        assert scheduled_target_info.unrecognized == []
        assert len(self.model.script_info) == 0
        assert len(self.model.get_scheduled_targets()) == 0

    async def add_script(self, sal_index: int) -> None:
        script_info = types.SimpleNamespace(
            scriptSalIndex=sal_index,
            scriptState=ScriptState.UNKNOWN,
        )
        await self.model.callback_script_info(script_info)

    def get_expected_observing_blocks(self) -> set[str]:
        return {
            "BLOCK-1",
            "BLOCK-2",
            "BLOCK-3",
            "BLOCK-4",
            "BLOCK-5",
            "BLOCK-6",
            "BLOCK-7",
            "BLOCK-8",
        }

    def get_expected_block_status(self) -> dict[str, BlockStatus]:
        return {
            "BLOCK-1": BlockStatus.AVAILABLE,
            "BLOCK-2": BlockStatus.AVAILABLE,
            "BLOCK-6": BlockStatus.AVAILABLE,
            "BLOCK-7": BlockStatus.INVALID,
            "BLOCK-8": BlockStatus.AVAILABLE,
        }

    def get_sample_configuration(self):
        config = types.SimpleNamespace(
            max_scripts=100,
            telemetry=dict(
                efd_name="unit_test",
            ),
            models=dict(),
            path_observing_blocks="../observing_blocks",
            startup_type="COLD",
            driver_type="driver",
            driver_configuration=dict(
                stop_tracking_observing_script_name="stop_tracking.py",
                stop_tracking_observing_script_is_standard=True,
            ),
            startup_database="",
        )

        return config

    def get_observing_scripts_config_validator(self) -> ValidationRules:
        with open(TEST_CONFIG_DIR.parent / "schema" / "cwfs.yaml", "r") as fp:
            cwfs_schema = yaml.safe_load(fp)

        with open(TEST_CONFIG_DIR.parent / "schema" / "slew.yaml", "r") as fp:
            slew_schema = yaml.safe_load(fp)

        return {
            ("cwfs.py", False): DefaultingValidator(cwfs_schema),
            ("slew.py", True): DefaultingValidator(slew_schema),
        }
