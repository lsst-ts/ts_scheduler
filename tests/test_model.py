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
import pytest

from unittest.mock import patch, Mock, AsyncMock

from lsst.ts.scheduler.model import Model


@pytest.mark.asyncio
@patch.multiple(
    Model,
    update_telemetry=AsyncMock(),
    synchronize_observatory_model=Mock(),
    register_scheduled_targets=Mock(),
    update_conditions=AsyncMock(),
    select_next_targets=AsyncMock(return_value=[None]),
)
async def test_generate_target_queue_no_target() -> None:
    """Test for when select_next_targets returns no target in
    generate_target_queue.
    """
    log = logging.getLogger()
    model = Model(log=log)

    n_targets = 0
    async for _ in model.generate_target_queue([], 5):
        n_targets += 1

    assert n_targets == 0
