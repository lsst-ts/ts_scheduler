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
import importlib

import numpy as np
import healpy as hp

import lsst.pex.config as pex_config

from lsst.ts.salobj import index_generator

from lsst.sims.almanac import Almanac
from lsst.sims.utils import _raDec2Hpid
from lsst.sims.featureScheduler.features import Conditions

from .driver import Driver, DriverParameters, DriverTarget
from .survey_topology import SurveyTopology


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


class FeatureSchedulerTarget(DriverTarget):
    """Feature based scheduler target.

    Parameters
    ----------
    observation : `np.ndarray`
        Observation produced by the feature based scheduler.

    """

    def __init__(self, observation, targetid=0):

        self.observation = observation

        super().__init__(
            targetid=targetid,
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


class FeatureSchedulerParameters(DriverParameters):
    """Feature Scheduler driver parameters.
    """

    scheduler_config = pex_config.Field(
        "Python script with the feature scheduler configuration. It must define "
        "a `scheduler` object of the type `lsst.sims.featureScheduler.schedulers.Core_scheduler`.",
        str,
    )
    force = pex_config.Field(
        "Force reloading scheduler? If `False` and scheduler is already configured "
        "it will not be overritten.",
        bool,
    )


class FeatureScheduler(Driver):
    """Feature scheduler driver.
    """

    def __init__(self, models, raw_telemetry, parameters=None):

        self.scheduler = None

        self.nside = None

        self.conditions = None

        self.index_gen = index_generator()

        self.next_observation_mjd = None

        self.almanac = Almanac()

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

        Raises
        ------
        RuntimeError:
            If `config` does not have a `scheduler_config` attribute or if it
            points to a non-existing file.

        """

        if not hasattr(config, "scheduler_config"):
            raise RuntimeError("No feature scheduler configuration defined.")
        elif not os.path.exists(config.scheduler_config):
            raise RuntimeError(
                f"Feature scheduler configuration file {config.scheduler_config} not found."
            )

        if self.scheduler is None or config.get("force", False):
            self.log.info(
                f"Loading feature based scheduler configuration from {config.scheduler_config}."
            )
            spec = importlib.util.spec_from_file_location(
                "config", config.scheduler_config
            )
            conf = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(conf)
            if not hasattr(conf, "scheduler"):
                raise NoSchedulerError("No scheduler defined in configuration file.")
            self.scheduler = conf.scheduler
            if not hasattr(conf, "nside"):
                raise NoNsideError("No nside defined in configuration file.")
            self.nside = conf.nside
            self.conditions = Conditions(nside=self.nside)

            self.conditions.FWHMeff = dict(
                [
                    (key, np.empty(hp.nside2npix(self.nside), dtype=float))
                    for key in self.models["seeing"].filter_list
                ]
            )

        # self.scheduler.survey_lists is a list of lists with different surveys
        survey_names = [
            survey.survey_name
            for survey_list in self.scheduler.survey_lists
            for survey in survey_list
        ]

        survey_topology = SurveyTopology()

        survey_topology.num_general_props = len(survey_names)
        survey_topology.general_propos = survey_names
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
        raise RuntimeError("Cold start not supported by SequentialScheduler.")

    def update_conditions(self):
        """Update conditions on the scheduler.
        """

        super().update_conditions()

        self._format_conditions()

        # Update conditions on the scheduler
        self.scheduler.update_conditions(self.conditions)

        # Set time from next observation based on the current time on the
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

        desired_obs = self.scheduler.request_observation(mjd=self.next_observation_mjd)

        if desired_obs is not None:
            target = FeatureSchedulerTarget(desired_obs)

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
                target.observation["FWHMeff"] = self.conditions.FWHMeff[target.filter][
                    hpid
                ]
                target.observation["airmass"] = self.conditions.airmass[hpid]
                # target.observation["fivesigmadepth"] = m5_flat_sed(
                #     filtername,
                #     target.observation["skybrightness"],
                #     target.observation["FWHMeff"],
                #     target.observation["exptime"],
                #     target.observation["airmass"],
                # )
                target.observation["alt"] = target.alt_rad
                target.observation["az"] = target.az_rad
                target.observation["rotSkyPos"] = target.ang_rad
                target.observation["clouds"] = self.conditions.bulk_cloud
                # target.observation["sunAlt"] = telemetry_stream["sunAlt"]
                # target.observation["moonAlt"] = telemetry_stream["moonAlt"]

                target.slewtime = slew_time
                target.airmass = target.observation["airmass"]
                target.sky_brightness = target.observation["skybrightness"]

                return target
        else:
            return None

    def register_observation(self, observation):
        """Validates observation and returns a list of successfully completed
        observations.

        Parameters
        ----------
        observation : `list` of `Target`
            Python list of Targets observed.

        Returns
        -------
        Python list of one or more Observations
        """
        for obs in observation:
            self.log.debug(obs.observation)
            self.scheduler.add_observation(obs.observation)

        return [observation]

    def load(self, config):
        """Load a new set of targets.
        """
        raise NotImplementedError("Load method not implemented yet.")

    def _format_conditions(self):
        """Format telemetry and observatory conditions for the feature
        scheduler.

        Returns
        -------
        conditions : `lsst.sims.featureScheduler.features.Conditions`

        """

        self.conditions.mjd = self.models["observatory_model"].dateprofile.mjd

        almanac_indx = self.almanac.mjd_indx(self.conditions.mjd)

        self.conditions.night = self.almanac.sunsets["night"][almanac_indx]

        # Clouds. Just the raw value
        self.conditions.bulk_cloud = self.raw_telemetry["bulkCloud"]

        # use conditions object itself to get aprox altitude of each healpx
        # These are in radians.
        alts = self.conditions.alt
        azs = self.conditions.az

        good = np.where(
            alts > self.models["observatory_model"].params.telalt_minpos_rad
        )

        # Compute the airmass at each heapix
        airmass = np.zeros(alts.size, dtype=float)
        airmass.fill(np.nan)
        airmass[good] = 1.0 / np.cos(np.pi / 2.0 - alts[good])
        self.conditions.airmass = airmass

        # Use the model to get the seeing at this time and airmasses.
        FWHM_500 = self.raw_telemetry["seeing"]
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
        self.conditions.sunrise = self.almanac.sunsets["sunrise"][almanac_indx]
        self.conditions.moonrise = self.almanac.sunsets["moonrise"][almanac_indx]
        self.conditions.moonset = self.almanac.sunsets["moonset"][almanac_indx]

        # Planet positions from almanac
        self.conditions.planet_positions = self.almanac.get_planet_positions(
            self.conditions.mjd
        )
