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
import logging
import yaml

import numpy as np

from dataclasses import dataclass

from .survey_topology import SurveyTopology

from lsst.ts.observatory.model import Target

__all__ = ["Driver", "DriverParameters"]

WORDY = logging.DEBUG - 5


class DriverTarget(Target):
    """This class provides a wrapper around `lsst.ts.observatory.model.Target`
    to add utility methods used by the Scheduler. The base class itself
    provides utility methods to interface with the observatory model. The
    methods added here are scheduler-specific, hence the need to subclass.

    Parameters
    ----------
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
        sal_index=0,
        targetid=0,
        fieldid=0,
        band_filter="",
        ra_rad=0.0,
        dec_rad=0.0,
        ang_rad=0.0,
        obs_time=0.0,
        num_exp=0,
        exp_times=[],
    ):
        self.sal_index = sal_index
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

        # TODO: This method might need to be expanded in the future.
        # Keeping it here as placeholder for now.

    def get_script_config(self):
        """Returns a yaml string representation of a dictionary with the
        configuration to be used for the observing script.

        Returns
        -------
        config_str: str
        """
        script_config = {
            "targetid": self.targetid,
            "band_filter": self.filter,
            "ra": self.ra,
            "dec": self.dec,
            "ang": self.ang,
            "obs_time": self.obs_time,
            "num_exp": self.num_exp,
            "exp_times": self.exp_times,
        }

        return yaml.safe_dump(script_config)

    def as_evt_topic(self, exposure_times_size=10, proposal_id_size=5):
        """Returns a SAL target topic with the Target information.

        Returns
        -------
        topic_target: `Scheduler_logevent_target`

        """
        topic_target = dict()

        topic_target["targetId"] = self.targetid
        topic_target["filter"] = self.filter
        topic_target["requestTime"] = self.time
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


@dataclass
class DriverParameters:
    """Actual global driver configuration parameters.

    This can be expanded for other scheduler drivers. For instance, if your
    scheduler uses a certain configuration file it is possible to subclass
    this and add the required parameters (e.g. file paths or else). Then,
    replace `self.params` on the Driver by the subclassed configuration.
    """

    night_boundary: float = -12.0
    new_moon_phase_threshold: float = 20.0

    def setDefaults(self):
        """Set defaults for the LSST Scheduler's Driver."""
        self.night_boundary = -12.0
        self.new_moon_phase_threshold = 20.0


class Driver:
    """The Scheduler Driver is the module that normalizes the interface between
    any scheduling algorithm to the LSST Scheduler CSC. The interface
    implements three main behaviours; configure an underlying algorithm,
    request targets and register successful observations.

    If the Scheduler algorithm requires a specific set of parameters the user
    must subclass `DriverParameters`, in the same module as the `Driver`, and
    add the appropriate parameters using the LSST pexConfig module.

    Access to the telemetry stream and models are also interfaced by `Driver`.
    The full list of default available telemetry data is shown in the
    scheduler_csc module. Nevertheless, the full list of telemetry may vary
    depending on the models used. The user has control over this while
    configuring the Scheduler CSC.

    Parameters
    ----------
    models: `dict`
        A dictionary with models available for the scheduling algorithm.
    raw_telemetry: `dict`
        A dictionary with available raw telemetry.
    """

    def __init__(self, models, raw_telemetry, parameters=None, log=None):
        if log is None:
            self.log = logging.getLogger(type(self).__name__)
        else:
            self.log = log.getChild(type(self).__name__)

        if parameters is None:
            self.parameters = DriverParameters()
        else:
            self.parameters = parameters
        self.models = models
        self.raw_telemetry = raw_telemetry
        self.targetid = 0

        self.is_night = None
        self.night = 1
        self.current_sunset = None
        self.current_sunrise = None

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
        survey_topology = SurveyTopology()

        survey_topology.num_general_props = 1
        survey_topology.general_propos = ["Test"]
        survey_topology.num_seq_props = 0
        survey_topology.sequence_propos = []

        return survey_topology

    def cold_start(self, observations):
        """Rebuilds the internal state of the scheduler from a list of
        observations.

        Parameters
        ----------
        observations : list of Observation objects

        """
        raise NotImplementedError("Cold start is not implemented.")

    def update_conditions(self):
        """Update driver internal conditions.

        When subclassing this method, make sure to call it at the start of the
        method, as it performs operations like running the observatory through
        the current targets on the queue.
        """
        self.log.debug("Updating conditions.")
        # Update observatory model with current observatory state.
        self.models["observatory_model"].set_state(self.models["observatory_state"])

        self.models["sky"].update(self.models["observatory_state"].time)

        if self.is_night is None:
            self.log.debug("Driver not initialized yet. Computing night parameters.")
            # Driver was not initialized yet. Need to compute night
            # boundaries

            (self.current_sunset, self.current_sunrise) = self.models[
                "sky"
            ].get_night_boundaries(self.parameters.night_boundary)

            self.is_night = (
                self.current_sunset
                <= self.models["observatory_state"].time
                < self.current_sunrise
            )

            self.log.debug(
                f"Sunset/Sunrise: {self.current_sunset}/{self.current_sunrise} "
            )

        is_night = self.is_night

        self.is_night = (
            self.current_sunset
            <= self.models["observatory_state"].time
            < self.current_sunrise
        )

        # Only compute night boundaries when we transition from nighttime to
        # daytime. Possibilities are:
        # 1 - self.is_night=True and is_night = True: During the night (no need
        #     to compute anything).
        # 2 - self.is_night=False and is_night = True: Transitioned from
        #     night/day (need to recompute night boundaries).
        # 3 - self.is_night=True and is_night = False: Transitioned from
        #     day/night (no need to compute anything).
        # 4 - self.is_night=False and is_night = False: During the day, no need
        #     to compute anything.
        if not self.is_night and is_night:
            self.log.debug("Night over. Computing next nigth boundaries.")
            self.night += 1
            (self.current_sunset, self.current_sunrise) = self.models[
                "sky"
            ].get_night_boundaries(self.parameters.night_boundary)

            self.log.debug(
                f"[{self.night}]: Sunset/Sunrise: {self.current_sunset}/{self.current_sunrise} "
            )

        # Run observatory model over current targets on the queue
        for target in self.raw_telemetry["scheduled_targets"]:
            self.models["observatory_model"].observe(target)

    def select_next_target(self):
        """Picks a target and returns it as a target object.

        By default it will just return a dummy test target.

        Returns
        -------
        Target

        """
        self.log.log(WORDY, "Selecting next target.")

        self.targetid += 1
        target = DriverTarget(targetid=self.targetid)

        target.num_exp = 2
        target.exp_times = [15.0, 15.0]
        target.num_props = 1
        target.propid_list = [0]

        return target

    def register_observation(self, observation):
        """Validates observation and returns a list of successfully completed
        observations.

        Parameters
        ----------
        observation : Observation or a python list of Observations

        Returns
        -------
        Python list of one or more Observations
        """
        self.log.log(WORDY, "Registering observation %s.", observation)

        return [observation]

    def load(self, config):
        """Load a modifying configuration.

        The input is a file that the Driver must be able to parse. It should
        contain that the driver can parse to reconfigure the current scheduler
        algorithm. For instance, it could contain new targets to add to a queue
        or project.

        Each Driver must implement its own load method. This method just checks
        that the file exists.

        Parameters
        ----------
        config : `str`
            Configuration to load

        Raises
        ------
        RuntimeError:
            If input configuration file does not exists.

        """
        if not os.path.exists(config):
            raise RuntimeError(f"Input configuration file {config} does not exist.")

    def save_state(self):
        """Save the current state of the scheduling algorithm to a file.

        Returns
        -------
        filename: `str`
            The name of the file with the state.
        """
        raise NotImplementedError("Save state is is not implemented.")

    def reset_from_state(self, filename):
        """Load the state from a file."""
        raise NotImplementedError("Reset from state is not implemented.")
