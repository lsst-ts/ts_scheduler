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

import numpy as np

from lsst.ts import observing

from .driver_target import DriverTarget


class FeatureSchedulerTarget(DriverTarget):
    """Feature based scheduler target.

    Parameters
    ----------
    observing_block: `observing.ObservingBlock`
        Observing block.
    observation: `np.ndarray`
        Observation produced by the feature based scheduler.
    """

    def __init__(
        self,
        observing_block: observing.ObservingBlock,
        observation: np.ndarray,
        **kwargs,
    ):
        self.observation = observation

        super().__init__(
            observing_block=observing_block,
            targetid=observation["ID"][0],
            band_filter=observation["filter"][0],
            ra_rad=observation["RA"][0],
            dec_rad=observation["dec"][0],
            ang_rad=observation["rotSkyPos"][0],
            num_exp=observation["nexp"][0],
            exp_times=[
                observation["exptime"][0] / observation["nexp"][0]
                for i in range(observation["nexp"][0])
            ],
        )
        self.note = str(observation["note"][0])
        self.slewtime = float(observation["slewtime"][0])
