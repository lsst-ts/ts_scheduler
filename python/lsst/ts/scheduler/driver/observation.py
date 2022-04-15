# This file is part of ts_scheduler
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the Vera C. Rubin Observatory
# Project (https://www.lsst.org).
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

import dataclasses


@dataclasses.dataclass
class Observation:
    """Dataclass for defining the observation data structure.

    This is a convenience class to convert the observation information to
    publish to the EFD.
    """

    targetId: int
    ra: float
    decl: float
    rotSkyPos: float
    mjd: float
    exptime: float
    filter: str
    nexp: int
    additionalInformation: str
