# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import typing
from string import Template

import numpy as np
import yaml
from astropy import units
from astropy.coordinates import Angle
from lsst.ts.observatory.model import Target
from lsst.ts.observing import ObservingBlock
from lsst.ts.salobj import DefaultingValidator

from ..exceptions.exceptions import NonConsecutiveIndexError
from .observation import Observation


class DriverTarget(Target):
    """This class provides a wrapper around `lsst.ts.observatory.model.Target`
    to add utility methods used by the Scheduler. The base class itself
    provides utility methods to interface with the observatory model. The
    methods added here are scheduler-specific, hence the need to subclass.

    Parameters
    ----------
    observing_block : ObservingBlock
        Observing block for this target.
    targetid : int
        A unique identifier for the given target.
    fieldid : int
        The ID of the associated OpSim field for the target.
    band_filter : str
        The single character name of the associated band filter.
    ra_rad : float
        The right ascension (radians) of the target.
    dec_rad : float
        The declination (radians) of the target.
    ang_rad : float
        The sky angle (radians) of the target.
    obs_time : float
        Time of the observation. If zero (default) slew as soon as possible.
    num_exp : int
        The number of requested exposures for the target.
    exp_times : list[float]
        The set of exposure times (seconds) for the target. Needs to length
        of num_exp.

    """

    def __init__(
        self,
        observing_block: ObservingBlock,
        block_configuration: dict = dict(),
        targetid: int = 0,
        fieldid: int = 0,
        band_filter: str = "",
        ra_rad: float = 0.0,
        dec_rad: float = 0.0,
        ang_rad: float = 0.0,
        obs_time: float = 0.0,
        num_exp: float = 0,
        exp_times: typing.List[float] = [],
        log: typing.Optional[logging.Logger] = None,
        note: str = "Target",
    ) -> None:
        if log is None:
            self.log = logging.getLogger(type(self).__name__)
        else:
            self.log = log.getChild(type(self).__name__)

        self.observing_block = observing_block
        self.obs_time = obs_time
        super().__init__(
            targetid=targetid,
            fieldid=fieldid,
            band_filter=band_filter,
            ra_rad=ra_rad,
            dec_rad=dec_rad,
            ang_rad=ang_rad,
            num_exp=num_exp,
            exp_times=exp_times,
        )
        self.note = note
        self._sal_indices = []

        self.block_configuration = dict()

        if observing_block.configuration_schema:

            block_configuration_validator = DefaultingValidator(
                schema=yaml.safe_load(observing_block.configuration_schema)
            )
            self.block_configuration = block_configuration_validator.validate(
                block_configuration
            )

    def get_sal_indices(self) -> list[int]:
        """Get the list of SAL indices for the target scripts.

        Returns
        -------
        `list`[`int`]
            List of SAL indices.
        """
        return self._sal_indices

    def add_sal_index(self, sal_index: int) -> None:
        """Add SAL index.

        Parameters
        ----------
        sal_index : `int`
            Index of a SAL Script that is executing this observation.

        Raises
        ------
        RuntimeError
            If sal_index is non-consecutive.
        """
        if sal_index in self._sal_indices:
            self.log.warning(f"Index {sal_index} already included.")
            return

        self._sal_indices.append(sal_index)

        if len(self._sal_indices) > 1 and sal_index != self._sal_indices[-2] + 1:
            raise NonConsecutiveIndexError(
                "Non-consecutive SAL index for target observations. "
                f"Got {sal_index}, currently with {self._sal_indices}."
            )

    def format_config(self) -> None:
        """Format the observing scripts configuration using the information
        for the driver.

        Raises
        ------
        RuntimeError
            If formatting fails, log the original exception and then raise a
            `RuntimeError`.
        """
        script_config = self.get_script_config()
        for observing_script in self.observing_block.scripts:
            observing_script_config = observing_script.get_script_configuration()
            try:
                observing_script_config = Template(observing_script_config).substitute(
                    **script_config
                )
                observing_script.parameters = yaml.safe_load(
                    Template(observing_script_config).substitute(**script_config)
                )
            except Exception:
                self.log.exception(
                    f"Error parsing script configuration for observing block: {self.observing_block}."
                )
                raise RuntimeError(
                    f"Failed to parse configuration: {observing_script_config}"
                )

    def get_script_config(self) -> dict:
        """Returns a dictionary with the parameters to be used for the
        observing scripts.

        Returns
        -------
        script_config : `dict`
            Script configuration.
        """
        script_config = {
            "targetid": int(self.targetid),
            "band_filter": str(self.filter),
            "name": self.get_target_name(),
            "ra": self.get_ra(),
            "dec": self.get_dec(),
            "rot_sky": float(self.ang),
            "alt": float(self.alt),
            "az": float(self.az),
            "rot": float(self.rot),
            "obs_time": float(self.obs_time),
            "num_exp": int(self.num_exp),
            "exp_times": [float(exptime) for exptime in self.exp_times],
            "estimated_slew_time": float(self.slewtime),
            "program": self.observing_block.program,
        }
        script_config.update(self.block_configuration)

        return script_config

    def get_dec(self) -> str:
        """Get declination formatted as a colon-separated hexagesimal string.

        The returned value is wrapped within single quote ('00:00:00.0') such
        that it can be safely used in yaml string formatting.

        Returns
        -------
        `str`
            Declination as hexagesimal string (DD:MM:SS.S).
        """
        dec = str(
            Angle(self.dec, unit=units.degree).to_string(
                unit=units.degree, sep=":", alwayssign=True
            )
        )
        return f"{dec!r}"

    def get_ra(self) -> str:
        """Get right right ascension formatted as a colon-separated hexagesimal
        string.

        The returned value is wrapped within single quote ('00:00:00.0') such
        that it can be safely used in yaml string formatting.

        Returns
        -------
        `str`
            Right ascension as hexagesimal string (HH:MM:SS.S).
        """
        ra = str(
            Angle(self.ra, unit=units.degree).to_string(
                unit=units.hourangle, sep=":", alwayssign=True
            )
        )
        return f"{ra!r}"

    def get_target_name(self) -> str:
        """Parse the note field to get the target name.

        Returns
        -------
        `str`
            Target name.
        """
        return str(self.note).split(":", maxsplit=1)[-1]

    def get_observing_block(self) -> ObservingBlock:
        """Get observing block for this target.

        Returns
        -------
        `ObservingBlock`
            Observing Block.
        """
        self.format_config()
        return self.observing_block

    def as_dict(
        self, exposure_times_size: int = 10, proposal_id_size: int = 5
    ) -> typing.Dict[str, typing.Any]:
        """Returns a dictionary with the Target information.

        Returns
        -------
        topic_target: `dict`
            Dictionary with target information.
        """
        topic_target = dict()

        topic_target["targetId"] = self.targetid
        topic_target["filter"] = self.filter
        topic_target["requestTime"] = self.obs_time
        topic_target["ra"] = self.ra
        topic_target["decl"] = self.dec
        topic_target["skyAngle"] = self.ang
        topic_target["numExposures"] = self.num_exp
        topic_target["exposureTimes"] = np.zeros(exposure_times_size)
        for i, exptime in enumerate(self.exp_times):
            topic_target["exposureTimes"][i] = exptime
        topic_target["airmass"] = self.airmass
        topic_target["skyBrightness"] = self.sky_brightness
        topic_target["cloud"] = self.cloud
        topic_target["seeing"] = self.seeing
        topic_target["slewTime"] = self.slewtime
        topic_target["numProposals"] = self.num_props
        topic_target["proposalId"] = np.zeros(proposal_id_size, dtype=int)
        for i, prop_id in enumerate(self.propid_list):
            topic_target["proposalId"][i] = int(prop_id)
        topic_target["note"] = self.note

        return topic_target

    def get_observation(self) -> Observation:
        """Return observation from current target information.

        Returns
        -------
        `Observation`
            Observation object with information about the target.
        """
        return Observation(
            targetId=self.targetid,
            ra=self.ra,
            decl=self.dec,
            rotSkyPos=self.ang,
            mjd=self.obs_time,
            exptime=np.sum(self.exp_times),
            filter=self.filter,
            nexp=len(self.exp_times),
            additionalInformation=self.get_additional_information(),
        )

    def get_additional_information(self) -> str:
        """Return additional information about the target.

        Returns
        -------
        `str`
            Target additional information.
        """
        return ""
