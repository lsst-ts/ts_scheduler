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
import os
import pickle
import typing

import astropy.units as u
import jsonschema
import yaml
from astropy.coordinates import Angle
from astropy.time import Time
from lsst.ts import observing
from lsst.ts.utils import index_generator

from .driver import Driver, DriverParameters
from .driver_target import DriverTarget
from .observation import Observation

__all__ = ["SequentialParameters", "SequentialScheduler"]


class SequentialParameters(DriverParameters):
    """Sequential driver parameters.

    Notes
    -----
    Example of a yaml configuration:

    .. code-block:: yaml

        targets:
          -
            ra: 12:00:00
            dec: -10:00:00
            name: tile1
            instrument_setup:
              -
                exptime: 15.
                filter: r
              -
                exptime: 15.
                filter: r
          -
            ra: 12:00:00
            dec: -13:30:00
            name: tile2
            instrument_setup:
              -
                exptime: 15.
                filter: r
              -
                exptime: 15.
                filter: r
    """

    observing_list: str = ""
    # File with the list of targets to observe with the configuration.


class SequentialScheduler(Driver):
    """A simple scheduler driver that implements a sequential scheduler
    algorithm.

    The driver reads from an input file of targets provided by the user and
    send one target at a time.

    Parameters
    ----------
    models : `dict`[`str`, `typing.Any`]
        Models.
    raw_telemetry : `dict`[`str`, `typing.Any`]
        Raw telemetry
    observing_blocks : `dict`[`str`, `observing.ObservingBlock`]
        Observing blocks.
    parameters : `typing.Any`, optional
        Driver parameters, by default None
    log : `logging.Logger` | None, optional
        Logger, by default None
    """

    def __init__(
        self,
        models: dict[str, typing.Any],
        raw_telemetry: dict[str, typing.Any],
        observing_blocks: dict[str, observing.ObservingBlock],
        parameters: typing.Any = None,
        log: logging.Logger | None = None,
    ):
        self.observing_list_dict = dict()

        self.index_gen = index_generator()

        self.validator = jsonschema.Draft7Validator(self.schema())

        super().__init__(
            models=models,
            raw_telemetry=raw_telemetry,
            observing_blocks=observing_blocks,
            parameters=parameters,
            log=log,
        )

    def configure_scheduler(self, config=None):
        """This method is responsible for running the scheduler configuration
        and returning the survey topology, which specifies the number, name
        and type of projects running by the scheduler.

        By default it will just return a test survey topology.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `lsst.ts.scheduler.kernel.SurveyTopology`

        """

        if not hasattr(config, "driver_configuration"):
            raise RuntimeError("No driver configuration section defined.")

        elif "observing_list" not in config.sequential_driver_configuration:
            raise RuntimeError("No observing list provided in configuration.")

        elif not os.path.exists(
            observing_list := config.sequential_driver_configuration["observing_list"]
        ):
            raise RuntimeError(f"Observing list {observing_list} not found.")

        self.log.debug(f"{config=}")

        with open(observing_list, "r") as f:
            config_yaml = f.read()

        observing_list_dict = yaml.safe_load(config_yaml)

        self.validator.validate(observing_list_dict)

        for target in observing_list_dict["targets"]:
            self.observing_list_dict[f"target_{next(self.index_gen)}"] = target

        self.log.debug(f"Got {len(self.observing_list_dict)} objects.")

        return super().configure_scheduler(config)

    def cold_start(self, observations: list[Observation]) -> None:
        """Rebuilds the internal state of the scheduler from a list of
        observations.

        Parameters
        ----------
        observations : `list`[`Observation`]
            List of observations.
        """
        raise RuntimeError("Cold start not supported by SequentialScheduler.")

    def select_next_target(self) -> DriverTarget:
        """Picks a target and returns it as a target object.

        Returns
        -------
        `DriverTarget`
            Target to observe.
        """
        if len(self.observing_list_dict) == 0:
            self.log.info(
                "Sequential Scheduler list empty. No more targets to schedule."
            )
            return None

        self.targetid += 1

        for tid in self.observing_list_dict:
            program = self.observing_list_dict[tid]["program"]
            observing_block = self.get_survey_observing_block(survey_name=program)

            config = self.observing_list_dict[tid]
            num_exp = len(config["instrument_setup"])

            target = DriverTarget(
                observing_block=observing_block,
                targetid=self.targetid,
                ra_rad=Angle(config["ra"], unit=u.hourangle).to(u.rad).value,
                dec_rad=Angle(config["dec"], unit=u.deg).to(u.rad).value,
                band_filter=config["instrument_setup"][0]["filter"],
                exp_times=[
                    config["instrument_setup"][i]["exptime"] for i in range(num_exp)
                ],
                ang_rad=Angle(config.get("rot", 0.0), unit=u.deg).to(u.rad).value,
                note=config["name"],
            )

            slew_time, error = self.models["observatory_model"].get_slew_delay(target)

            if error > 0:
                self.log.debug(
                    f"Error[{error}]: Cannot slew to target @ ra={target.ra}, dec={target.dec}."
                )
                continue
            else:
                target.slewtime = slew_time

                self.log.debug(f"Slewtime to target: {slew_time}s.")

                self.observing_list_dict.pop(tid)

                return target

        self.log.debug(
            f"No observable target available. Current target list size: {len(self.observing_list_dict)}."
        )

        return None

    def schema(self) -> dict[str, typing.Any]:
        """Get schema for the sequential scheduler algorithm configuration
        files.

        Returns
        -------
        `dict`[str, `typing.Any`]
            Schema.
        """
        schema = """$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/master/python/lsst/ts/scheduler/driver/sequential.yaml
title: SequentialScheduler v1
description: Schema for Sequential Scheduler algorith configuration files
type: object
additionalProperties: false
properties:
  targets:
    type: array
    items:
      type: object
      additionalProperties: false
      required: ["ra", "dec", "instrument_setup", "name", "program"]
      properties:
        ra:
          description: ICRS right ascension (hour).
          anyOf:
            - type: number
              minimum: 0
              maximum: 24
        dec:
          description: ICRS declination (deg).
          anyOf:
            - type: number
              minimum: -90
              maximum: 90
        rot_value:
          description: >-
            Rotator position value. Actual meaning depends on rot_type.
          type: number
        rot_type:
          description: >-
            Rotator strategy. Options are:
              Sky: Sky position angle strategy. The rotator is positioned with respect
                   to the North axis so rot_angle=0. means y-axis is aligned with North.
                   Angle grows clock-wise.

              SkyAuto: Same as sky position angle but it will verify that the requested
                       angle is achievable and wrap it to a valid range.

              Parallactic: This strategy is required for taking optimum spectra with
                           LATISS. If set to zero, the rotator is positioned so that the
                           y-axis (dispersion axis) is aligned with the parallactic
                           angle.

              PhysicalSky: This strategy allows users to select the **initial** position
                            of the rotator in terms of the physical rotator angle (in the
                            reference frame of the telescope). Note that the telescope
                            will resume tracking the sky rotation.

              Physical: Select a fixed position for the rotator in the reference frame of
                        the telescope. Rotator will not track in this mode.
          type: string
          enum: ["Sky", "SkyAuto", "Parallactic", "PhysicalSky", "Physical"]
        name:
          description: Target name.
          type: string
        program:
          description: Program name.
          type: string
        instrument_setup:
          description: Instrument setup.
          type: array
          items:
            type: object
            required: ["exptime", "filter"]
            properties:
              exptime:
                description: Exposure time (seconds).
                type: number
                minimum: 0
              filter:
                description: Filters for this exposure.
                type: string
        """
        return yaml.safe_load(schema)

    def load(self, config):
        """Load a new set of targets.

        Format of the input file must be the same as that for the configure
        method. The targets will be appended to the existing queue.

        Raises
        ------
        RuntimeError:
            If driver is not configured.

        """

        with open(config) as f:
            config_yaml = f.read()

        new_targets = yaml.safe_load(config_yaml)

        for target in new_targets:
            self.observing_list_dict[f"target_{next(self.index_gen)}"] = new_targets[
                target
            ]

        self.log.debug(f"Got {len(new_targets)} objects.")

    def save_state(self, targets_queue=None):
        """Save the current state of the scheduling algorithm to a file.

        Parameters
        ----------
        targets_queue : `list`[`DriverTarget`] | None
            List of targets already queued or pulled from the scheduler.

        Returns
        -------
        filename : `str`
            Name of the file with the state.
        """

        now = Time.now().to_value("isot")
        filename = f"sequential_{now}.p"

        with open(filename, "wb") as fp:
            pickle.dump(self.observing_list_dict, fp)

        return filename

    def reset_from_state(self, filename):
        """Load the state from a file.

        Parameters
        ----------
        filename : `str`
            Name of the file with the state.
        """
        with open(filename, "rb") as fp:
            self.observing_list_dict = pickle.load(fp)
