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

__all__ = ["ObservatoryStateMock"]

import asyncio

from lsst.ts import salobj, utils
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel


class ObservatoryStateMock:
    def __init__(self):
        self.ptg = salobj.Controller("MTPtg")

        self.location = ObservatoryLocation()
        self.location.for_lsst()

        self.model = ObservatoryModel(self.location)
        self.model.configure_from_module()

        self.telemetry_sleep_time = 0.02
        self.run_current_target_status_loop = True
        self.current_target_status_task = None

        self._started = False
        self.start_task = asyncio.create_task(self.start())

    async def current_target_status(self):
        while self.run_current_target_status_loop:
            time = utils.current_tai()
            self.model.update_state(time)
            await self.ptg.tel_currentTargetStatus.set_write(
                timestamp=time,
                demandAz=self.model.current_state.telaz,
                demandEl=self.model.current_state.telalt,
                demandRot=self.model.current_state.telrot,
                demandRa=self.model.current_state.ra,
                demandDec=self.model.current_state.dec,
                parAngle=self.model.current_state.pa,
            )
            await asyncio.sleep(self.telemetry_sleep_time)

    async def start(self):
        if not self._started:
            self._started = True
            await self.ptg.start_task

            self.run_current_target_status_loop = True
            self.current_target_status_task = asyncio.create_task(
                self.current_target_status()
            )

    async def close(self):
        self.run_current_target_status_loop = False
        try:
            await asyncio.wait_for(
                self.current_target_status_task, timeout=self.telemetry_sleep_time * 5
            )
        finally:
            await self.ptg.close()

    async def __aenter__(self):
        await self.start_task
        return self

    async def __aexit__(self, type, value, traceback):
        await self.close()
