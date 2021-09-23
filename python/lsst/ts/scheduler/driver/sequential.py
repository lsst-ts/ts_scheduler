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

import os
import yaml
import pickle
import jsonschema

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import Angle

from lsst.ts.salobj import index_generator

from .driver import Driver, DriverParameters
from .driver_target import DriverTarget


__all__ = ["SequentialParameters", "SequentialScheduler"]


class SequentialTarget(DriverTarget):
    def __init__(self, config, targetid=0):
        super().__init__(targetid=targetid, num_exp=1, exp_times=[0.0])
        self.config = config
        # config = self.get_script_config()

        self.ra_rad = Angle(self.config["ra"], unit=u.hourangle).to(u.rad).value
        self.dec_rad = Angle(self.config["dec"], unit=u.deg).to(u.rad).value
        self.num_exp = len(self.config["instrument_setup"])
        self.filter = self.config["instrument_setup"][0]["filter"]
        self.exp_times = [
            self.config["instrument_setup"][i]["exptime"] for i in range(self.num_exp)
        ]

        self.rot_rad = Angle(self.config.get("rot", 0.0), unit=u.deg).to(u.rad).value

    def get_script_config(self):
        """Returns a yaml string representation of a dictionary with the
        configuration to be used for the observing script.

        Returns
        -------
        config_str: str
        """

        return yaml.safe_dump(
            self.config["script_config"]
            if "script_config" in self.config
            else self.config
        )


class SequentialParameters(DriverParameters):
    """Sequential driver parameters.

    Notes
    -----

    Example of a yaml configuration.

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

    """

    def __init__(self, models, raw_telemetry, parameters=None):

        self.observing_list_dict = dict()

        self.index_gen = index_generator()

        self.validator = jsonschema.Draft7Validator(self.schema())

        super().__init__(models, raw_telemetry, parameters)

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

        if not hasattr(config, "observing_list"):
            raise RuntimeError("No observing list provided in configuration.")

        if not os.path.exists(config.observing_list):
            raise RuntimeError(f"Observing list {config.observing_list} not found.")

        with open(config.observing_list, "r") as f:
            config_yaml = f.read()

        observing_list_dict = yaml.safe_load(config_yaml)

        self.validator.validate(observing_list_dict)

        for target in observing_list_dict["targets"]:
            self.observing_list_dict[f"target_{next(self.index_gen)}"] = target

        self.log.debug(f"Got {len(self.observing_list_dict)} objects.")

        return super().configure_scheduler(config)

    def cold_start(self, observations):
        """Rebuilds the internal state of the scheduler from a list of
        observations.

        Parameters
        ----------
        observations : list of Observation objects

        """
        raise RuntimeError("Cold start not supported by SequentialScheduler.")

    def select_next_target(self):
        """Picks a target and returns it as a target object.

        Returns
        -------
        Target

        """
        if len(self.observing_list_dict) == 0:
            self.log.info(
                "Sequential Scheduler list empty. No more targets to schedule."
            )
            return None

        self.targetid += 1

        for tid in self.observing_list_dict:

            target = SequentialTarget(
                config=self.observing_list_dict[tid],
                targetid=self.targetid,
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

        self.log.info(
            f"No observable target available. Current target list size: {len(self.observing_list_dict)}."
        )

        return None

    def schema(self):
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
          description: Target name
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
        script_config:
          type: object
          description: Script configuration.
          additionalProperties: true
      # Disable support for providing name only. Need to check how to support it.
      # if:
      #   properties:
      #     ra:
      #       const: null
      #     dec:
      #       const: null
      #   required: ["name", "instrument_setup"]
      # else:
        required: ["ra", "dec", "instrument_setup"]
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

    def save_state(self):
        """Save the current state of the scheduling algorithm to a file.

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
