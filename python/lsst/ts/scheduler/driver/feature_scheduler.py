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

import io
import os
import math
import yaml
import typing
import pandas
import pickle
import pathlib
import importlib

import numpy as np
import healpy as hp

from astropy.time import Time

from lsst.ts.utils import index_generator

from rubin_sim.site_models import Almanac
from rubin_sim.utils import _raDec2Hpid
from rubin_sim.scheduler.features import Conditions
from rubin_sim.scheduler.utils import empty_observation

from .driver import Driver, DriverParameters
from .driver_target import DriverTarget
from .observation import Observation
from .feature_scheduler_target import FeatureSchedulerTarget
from ..utils import SchemaConverter

__all__ = ["FeatureScheduler", "NoSchedulerError", "NoNsideError"]


class NoSchedulerError(Exception):
    """Exception raised when scheduler is not defined in the feature scheduler
    configuration.
    """

    pass


class NoNsideError(Exception):
    """Exception raised when nside is not defined in the feature scheduler
    configuration.
    """

    pass


class FeatureSchedulerParameters(DriverParameters):
    """Feature Scheduler driver parameters."""

    scheduler_config: str = ""
    # Python script with the feature scheduler configuration. It must define
    # a `scheduler` object of the type
    # `lsst.sims.featureScheduler.schedulers.Core_scheduler`.

    force: bool = False
    # Force reloading scheduler? If `False` and scheduler is already configured
    # it will not be overritten.


class FeatureScheduler(Driver):
    """Feature scheduler driver."""

    default_observation_database_name = (
        pathlib.Path.home() / "fbs_observation_database.sql"
    )

    def __init__(self, models, raw_telemetry, parameters=None, log=None):

        self.scheduler = None

        self.nside = None

        self.conditions = None

        self.index_gen = index_generator()

        self.next_observation_mjd = None

        self._desired_obs = None

        self.almanac = Almanac()

        self.seed = 42

        self.script_configuration = dict()

        self.observation_database_name = self.default_observation_database_name

        self.schema_converter = SchemaConverter()

        super().__init__(models, raw_telemetry, parameters, log=log)

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

        Raises
        ------
        RuntimeError:
            If `config` does not have a `scheduler_config` attribute or if it
            points to a non-existing file.
        NoSchedulerError:
            If scheduler configuration does not define `scheduler` attribute.
        NoNsideError:
            If scheduler configuration does not define `nside` attribute.

        """

        self._desired_obs = None

        if not hasattr(config, "driver_configuration"):
            raise RuntimeError("No driver configuration section defined.")
        elif "scheduler_config" not in config.driver_configuration:
            raise RuntimeError("No feature scheduler configuration defined.")
        elif not os.path.exists(
            scheduler_config := config.driver_configuration["scheduler_config"]
        ):
            raise RuntimeError(
                f"Feature scheduler configuration file {scheduler_config} not found."
            )

        if self.scheduler is None or config.driver_configuration.get("force", False):

            self.log.info(
                f"Loading feature based scheduler configuration from: {scheduler_config}."
            )

            spec = importlib.util.spec_from_file_location("config", scheduler_config)
            conf = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(conf)

            if not hasattr(conf, "scheduler"):
                raise NoSchedulerError("No scheduler defined in configuration file.")

            if not hasattr(conf, "nside"):
                raise NoNsideError("No nside defined in configuration file.")

            if not hasattr(conf, "seed"):
                self.log.warning(
                    "Feature Based Scheduler configuration does not specify a random seed. "
                    f"Assuming seed={self.seed}."
                )
            else:
                self.seed = conf.seed

            self.nside = conf.nside

            np.random.seed(self.seed)
            self.scheduler = conf.scheduler
            self.conditions = Conditions(nside=self.nside)

            self.conditions.FWHMeff = dict(
                [
                    (key, np.empty(hp.nside2npix(self.nside), dtype=float))
                    for key in self.models["seeing"].filter_list
                ]
            )

        if "observation_database_name" in config.driver_configuration:
            self.observation_database_name = pathlib.Path(
                config.driver_configuration["observation_database_name"]
            )
            self.log.debug(f"Observation database: {self.observation_database_name}")
        else:
            self.log.warning(
                "Observation database name not defined in driver configuration. "
                f"Using default: {self.observation_database_name}. "
                "This database is used for warm start the scheduler, you might "
                "want to define a destination with persistent storage."
            )

        self.script_configuration = config.driver_configuration.get(
            "script_configuration", dict()
        )
        survey_topology = super().configure_scheduler(config)

        # self.scheduler.survey_lists is a list of lists with different surveys
        survey_names = [
            survey.survey_name
            for survey_list in self.scheduler.survey_lists
            for survey in survey_list
        ]

        survey_topology.num_general_props = len(survey_names)
        survey_topology.general_propos = survey_names
        survey_topology.num_seq_props = 0
        survey_topology.sequence_propos = []

        return survey_topology

    def cold_start(self, observations: typing.List[DriverTarget]) -> None:
        """Rebuilds the internal state of the scheduler from a list of
        Targets.

        Parameters
        ----------
        observations : `list` of `DriverTarget`
        """
        for observation in observations:
            self.scheduler.add_observation(observation)

    def parse_observation_database(self, filename: str) -> None:
        """Parse an observation database into a list of observations.

        Parameters
        ----------
        filename : `str`

        Returns
        -------
        observations : `list` of `DriverTarget`
        """

        fbs_observations = self.schema_converter.opsim2obs(filename=filename)
        observations = []
        for fbs_observation in fbs_observations:
            (
                observing_script_name,
                observing_script_is_standard,
            ) = self.get_survey_observing_script(
                self._get_survey_name_from_observation(fbs_observation)
            )

            target = FeatureSchedulerTarget(
                observing_script_name=observing_script_name,
                observing_script_is_standard=observing_script_is_standard,
                observation=np.array(fbs_observation, ndmin=1),
                log=self.log,
                **self.script_configuration,
            )

            observations.append(target)

        return observations

    def update_conditions(self):
        """Update conditions on the scheduler."""

        super().update_conditions()

        self._format_conditions()

        # Update conditions on the scheduler
        self.scheduler.update_conditions(self.conditions)

        # Set time for next observation based on the current time on the
        # observatory model, which accounts for current observations on the
        # queue.
        self.next_observation_mjd = self.models["observatory_model"].dateprofile.mjd

    def select_next_target(self):
        """Picks a target and returns it as a target object.

        Returns
        -------
        Target

        """

        if self.next_observation_mjd is None:
            raise RuntimeError(
                "Time for next observation not set. Call `update_conditions` before requesting a target."
            )

        desired_obs = (
            self.scheduler.request_observation(mjd=self.next_observation_mjd)
            if self._desired_obs is None
            else self._desired_obs
        )

        return self._handle_desired_observation(desired_observation=desired_obs)

    def _handle_desired_observation(self, desired_observation):
        """Handler desired observation.

        Parameters
        ----------
        desired_observation : `np.array`
            Feature based scheduler observation.

        Returns
        -------
        desired_target : `Target`
            Desidered target.
        """

        desired_target = None

        if desired_observation is not None:

            desired_target = self._get_validated_target_from_observation(
                observation=desired_observation
            )

            if desired_target is None:
                self._desired_obs = None
                return None
            elif self._check_need_cwfs(desired_target):
                self.log.debug(f"Scheduling cwfs observation before {desired_target}.")
                self._desired_obs = desired_observation
                return self._get_cwfs_target_for_observation(desired_observation)
            else:
                self._desired_obs = None
                return desired_target
        else:
            return desired_target

    def _get_validated_target_from_observation(self, observation):
        """Validate a feature based scheduler observation and convert it to a
        Target.

        Parameters
        ----------
        desired_observation : `np.array`
            Feature based scheduler observation.

        Returns
        -------
        Target
        """

        (
            observing_script_name,
            observing_script_is_standard,
        ) = self.get_survey_observing_script(
            self._get_survey_name_from_observation(observation)
        )

        target = FeatureSchedulerTarget(
            observing_script_name=observing_script_name,
            observing_script_is_standard=observing_script_is_standard,
            observation=observation,
            log=self.log,
            **self.script_configuration,
        )

        slew_time, error = self.models["observatory_model"].get_slew_delay(target)

        if error > 0:
            self.log.error(
                f"Error[{error}]: Cannot slew to target @ ra={target.ra}, dec={target.dec}."
            )
            self.scheduler.flush_queue()
            return None
        else:
            target.slewtime = slew_time

            target.observation["mjd"] = (
                self.conditions.mjd + slew_time / 60.0 / 60.0 / 24.0
            )
            target.observation["night"] = self.conditions.night
            target.observation["slewtime"] = slew_time

            hpid = _raDec2Hpid(self.nside, target.ra_rad, target.dec_rad)

            target.observation["skybrightness"] = self.conditions.skybrightness[
                target.filter
            ][hpid]
            target.observation["FWHMeff"] = self.conditions.FWHMeff[target.filter][hpid]
            target.observation["airmass"] = self.conditions.airmass[hpid]
            target.observation["alt"] = target.alt_rad
            target.observation["az"] = target.az_rad
            target.observation["rotSkyPos"] = target.ang_rad
            target.observation["clouds"] = self.conditions.bulk_cloud

            target.slewtime = slew_time
            target.airmass = target.observation["airmass"]
            target.sky_brightness = target.observation["skybrightness"]

            return target

    def _check_need_cwfs(self, target):
        """Check if the target needs curvature wavefront sensing (cwfs).

        Parameters
        ----------
        target : `Target`
            Target to check if cwfs is required.

        Returns
        -------
        `bool`
            `True` if cwfs is needed.
        """

        try:
            self.assert_survey_observing_script("cwfs")
        except AssertionError:
            self.log.debug("CWFS survey not configured.")
            return False

        if target.observation["note"][0] == "cwfs":
            self.log.debug("Scheduled target already cwfs.")
            return False

        current_telescope_elevation = self.models[
            "observatory_model"
        ].current_state.alt_rad

        target_elevation = target.observation["alt"][0]

        delta_elevation = np.abs(current_telescope_elevation - target_elevation)
        delta_elevation_limit = self.models[
            "observatory_model"
        ].params.optics_cl_altlimit[1]

        if delta_elevation >= delta_elevation_limit:
            self.log.debug(
                f"Change in elevation ({math.degrees(delta_elevation):0.2f} deg) larger "
                f"than threshold ({math.degrees(delta_elevation_limit):0.2f} deg). "
                "Scheduling CWFS."
            )
            return True
        else:
            return False

    def _get_cwfs_target_for_observation(self, observation):
        """Return a target for cwfs suitable for the input target.

        Parameters
        ----------
        observation : `np.array`

        Returns
        -------
        `Target`
            Validated target for CWFS.
        """
        self.assert_survey_observing_script("cwfs")

        cwfs_observation = observation.copy()
        cwfs_observation["note"][0] = "cwfs"

        self.log.debug(f"Get cwfs target for: {observation}.")

        return self._get_validated_target_from_observation(observation=cwfs_observation)

    def register_observed_target(self, target: DriverTarget) -> Observation:
        """Validates observation and returns a list of successfully completed
        observations.

        Add target observation to the feature based scheduler.

        Parameters
        ----------
        observation : `list` of `Target`
            Python list of Targets observed.

        Returns
        -------
        Observation
        """

        self.scheduler.add_observation(target.observation[0])

        return super().register_observed_target(target)

    def register_observation(self, target: FeatureSchedulerTarget) -> None:
        """Register observation.

        Write the target observation into the observation database.

        Parameters
        ----------
        target : `FeatureSchedulerTarget`
            Target to register.
        """

        self.schema_converter.obs2opsim(
            target.observation,
            filename=self.observation_database_name.as_posix(),
        )

        return super().register_observation(target)

    def load(self, config):
        """Load a new set of targets."""

        self.reset_from_state(config)

    def _format_conditions(self):
        """Format telemetry and observatory conditions for the feature
        scheduler.

        Returns
        -------
        conditions : `lsst.sims.featureScheduler.features.Conditions`

        """

        self.conditions.mjd = self.models["observatory_model"].dateprofile.mjd

        self.log.debug(f"Format conditions. mjd={self.conditions.mjd}")

        almanac_indx = self.almanac.mjd_indx(self.conditions.mjd)

        self.conditions.night = self.almanac.sunsets["night"][almanac_indx]

        # Clouds. Just the raw value
        self.conditions.bulk_cloud = self.raw_telemetry.get("bulk_cloud", np.nan)

        # Wind speed and direction
        self.conditions.wind_speed = self.raw_telemetry.get("wind_speed", np.nan)
        self.conditions.wind_direction = self.raw_telemetry.get(
            "wind_direction", np.nan
        )

        # use conditions object itself to get aprox altitude of each healpx
        # These are in radians.
        alts = self.conditions.alt
        azs = self.conditions.az

        good = np.where(
            alts > self.models["observatory_model"].params.telalt_minpos_rad
        )

        # Compute the airmass at each healpix
        airmass = np.zeros(alts.size, dtype=float)
        airmass.fill(np.nan)
        airmass[good] = 1.0 / np.cos(np.pi / 2.0 - alts[good])
        self.conditions.airmass = airmass

        # Seeing measurement
        FWHM_500 = self.raw_telemetry.get("seeing", np.nan)

        # Use the model to get the seeing at this time and airmasses.
        seeing_dict = self.models["seeing"](FWHM_500, airmass[good])
        fwhm_eff = seeing_dict["fwhmEff"]
        for i, key in enumerate(self.models["seeing"].filter_list):
            self.conditions.FWHMeff[key].fill(np.nan)
            self.conditions.FWHMeff[key][good] = fwhm_eff[i, :]

        # sky brightness
        self.conditions.skybrightness = self.models["sky"].sky_brightness.returnMags(
            self.conditions.mjd,
            airmass_mask=False,
            planet_mask=False,
            moon_mask=False,
            zenith_mask=False,
        )

        self.conditions.mounted_filters = self.models[
            "observatory_state"
        ].mountedfilters
        # Use observatory_model current state because some target in the queue
        # may as well change the current filter, and this is not captured by
        # observatory_state which actually reflects the current observatory
        # state
        self.conditions.current_filter = self.models[
            "observatory_model"
        ].current_state.filter

        # Compute the slewtimes
        slewtimes = np.empty(alts.size, dtype=float)
        slewtimes.fill(np.nan)

        slewtimes[good] = self.models["observatory_model"].get_approximate_slew_delay(
            alt_rad=alts[good],
            az_rad=azs[good],
            goal_filter=self.models["observatory_state"].filter,
            lax_dome=True,
        )

        self.conditions.slewtime = slewtimes

        # Let's get the sun and moon
        sun_moon_info = self.models["sky"].get_moon_sun_info(
            np.array([0.0]), np.array([0.0])
        )

        # self.almanac.get_sun_moon_positions(self.mjd)
        # convert these to scalars
        for key in sun_moon_info:
            sun_moon_info[key] = sun_moon_info[key].max()

        self.conditions.moonPhase = sun_moon_info["moonPhase"]
        self.conditions.moonAlt = sun_moon_info["moonAlt"]
        self.conditions.moonAz = sun_moon_info["moonAz"]
        self.conditions.moonRA = sun_moon_info["moonRA"]
        self.conditions.moonDec = sun_moon_info["moonDec"]
        self.conditions.sunAlt = sun_moon_info["sunAlt"]
        self.conditions.sunRA = sun_moon_info["sunRA"]
        self.conditions.sunDec = sun_moon_info["sunDec"]

        # Again using observatory_model for information as it will account for
        # any observation in the queue.
        self.conditions.lmst = (
            self.models["observatory_model"].dateprofile.lst_rad * 12.0 / np.pi % 24.0
        )

        self.conditions.telRA = self.models["observatory_model"].current_state.ra_rad
        self.conditions.telDec = self.models["observatory_model"].current_state.dec_rad
        self.conditions.telAlt = self.models["observatory_model"].current_state.alt_rad
        self.conditions.telAz = self.models["observatory_model"].current_state.az_rad

        self.conditions.rotTelPos = self.models[
            "observatory_model"
        ].current_state.rot_rad
        self.conditions.cumulative_azimuth_rad = self.models[
            "observatory_model"
        ].current_state.telaz_rad

        # Add in the almanac information
        self.conditions.sunset = self.almanac.sunsets["sunset"][almanac_indx]
        self.conditions.sun_0_setting = Time(
            self.current_sunset,
            format="unix",
            scale="utc",
        ).mjd
        self.conditions.sun_n12_setting = self.almanac.sunsets["sun_n12_setting"][
            almanac_indx
        ]
        self.conditions.sun_n18_setting = self.almanac.sunsets["sun_n18_setting"][
            almanac_indx
        ]
        self.conditions.sun_n18_rising = self.almanac.sunsets["sun_n18_rising"][
            almanac_indx
        ]
        self.conditions.sun_n12_rising = self.almanac.sunsets["sun_n12_rising"][
            almanac_indx
        ]
        self.conditions.sun_0_rising = Time(
            self.current_sunrise,
            format="unix",
            scale="utc",
        ).mjd

        self.conditions.sunrise = self.almanac.sunsets["sunrise"][almanac_indx]
        self.conditions.moonrise = self.almanac.sunsets["moonrise"][almanac_indx]
        self.conditions.moonset = self.almanac.sunsets["moonset"][almanac_indx]

        # Planet positions from almanac
        self.conditions.planet_positions = self.almanac.get_planet_positions(
            self.conditions.mjd
        )

    def save_state(self):
        """Save the current state of the scheduling algorithm to a file.

        Returns
        -------
        filename : `str`
            Name of the file with the state.
        """

        now = Time.now().to_value("isot")
        filename = f"fbs_scheduler_{now}.p"

        with open(filename, "wb") as fp:
            pickle.dump(
                [
                    self.scheduler,
                    self.conditions,
                ],
                fp,
            )

        return filename

    def get_state_as_file_object(self):
        """Get the current state of the scheduling algorithm as a file object.

        Returns
        -------
        file_object : `io.BytesIO`
            File object with the current.
        """
        file_object = io.BytesIO()

        pickle.dump(
            [
                self.scheduler,
                self.conditions,
            ],
            file_object,
        )

        file_object.seek(0)

        return file_object

    def reset_from_state(self, filename):
        """Load the state from a file.

        Parameters
        ----------
        filename : `str`
            Name of the file with the state.
        """
        # Reset random number generator
        np.random.seed(self.seed)
        with open(filename, "rb") as fp:
            self.scheduler, _ = pickle.load(fp)

    def _get_survey_name_from_observation(self, observation):
        """Get the survey name for the feature scheduler observation.

        Parameters
        ----------
        observation : `numpy.ndarray`
            Feature based scheduler observation.

        Returns
        -------
        survey_name : `str`
            Survey name parsed from observation
        """
        # For now simply return the "notes" field.
        return observation["note"][0].split(":")[0]

    def _get_driver_target_from_observation_data_frame(
        self, observation_data_frame: typing.Tuple[pandas.Timestamp, pandas.Series]
    ) -> FeatureSchedulerTarget:
        """Convert an observation data frame into a FeatureSchedulerTarget.

        Override super class method to deal with Feature Scheduler Target
        custom requirements.

        Parameters
        ----------
        observation_data_frame :
                `typing.Tuple` [`pandas.Timestamp`, `pandas.Series`]
            An observation data frame.

        Returns
        -------
        target : `FeatureSchedulerTarget`
            Feature scheduler target.
        """

        fbs_observation = self._get_fbs_observation_from_observation_data_frame(
            observation_data_frame
        )

        (
            observing_script_name,
            observing_script_is_standard,
        ) = self.get_survey_observing_script(
            self._get_survey_name_from_observation(fbs_observation)
        )

        target = FeatureSchedulerTarget(
            observing_script_name=observing_script_name,
            observing_script_is_standard=observing_script_is_standard,
            observation=np.array(fbs_observation, ndmin=1),
            log=self.log,
            **self.script_configuration,
        )

        return target

    def _get_fbs_observation_from_observation_data_frame(
        self, observation_data_frame: typing.Tuple[pandas.Timestamp, pandas.Series]
    ) -> np.ndarray:
        """Convert observation pandas data fram to an fbs observation.

        Parameters
        ----------
        observation_data_frame :
                `typing.Tuple` [`pandas.Timestamp`, `pandas.Series`]
            An observation data frame.

        Returns
        -------
        fbs_observation : `np.ndarray`
            Feature scheduler observation.
        """
        fbs_observation = empty_observation()

        for key in self.fbs_observation_named_parameter_map():
            fbs_observation[key] = observation_data_frame[1][
                self.fbs_observation_named_parameter_map()[key]
            ]

        additional_information = yaml.safe_load(
            observation_data_frame[1]["additionalInformation"]
        )

        for name in fbs_observation.dtype.names:
            if name not in self.fbs_observation_named_parameter_map():
                fbs_observation[name] = additional_information[name]

        return fbs_observation

    @staticmethod
    def fbs_observation_named_parameter_map() -> typing.Dict[str, str]:
        """Return the mapping between feature scheduler observation parameter
        keywords and the `Observation` parameter name keywords

        Returns
        -------
        `dict`
            Mapping between fbs observations keywords and `Observation`
            keywords.
        """
        return dict(
            ID="targetId",
            RA="ra",
            dec="decl",
            mjd="mjd",
            exptime="exptime",
            filter="filter",
            rotSkyPos="rotSkyPos",
            nexp="nexp",
        )
