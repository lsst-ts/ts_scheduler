from enum import Enum
import logging
import numpy
import palpy

from lsst.sims.skybrightness_pre import SkyModelPre
from lsst.sims.skybrightness_pre import __version__ as sky_model_pre_version

from .date_profile import DateProfile
from .sun import Sun

class Planets(Enum):
    """Handle planet values for palpy calls.
    """
    SUN = 0
    MERCURY = 1
    VENUS = 2
    MOON = 3
    MARS = 4
    JUPITER = 5
    SATURN = 6
    URANUS = 7
    NEPTUNE = 8
    PLUTO = 9

__all__ = ["AstronomicalSkyModel"]

class AstronomicalSkyModel(object):

    def __init__(self, location):
        """Initialize the class.

        Parameters
        ----------
        location : ts_scheduler.observatoryModel.ObservatoryLocation
            The instance containing the observatory location information.
        """
        self.log = logging.getLogger("sky_model.AstronomicalSkyModel")
        self.date_profile = DateProfile(0, location)
        self.sky_brightness = SkyModelPre(opsimFields=True)
        self.sun = Sun()
        self.exclude_planets = True

    def configure(self, exclude_planets):
        """Add configuration for the sky brightness model.

        Parameters
        ----------
        exclude_planets : bool
            Flag to mask planets in sky brightness information.
        """
        self.exclude_planets = exclude_planets

    def update(self, timestamp):
        """Update the internal timestamp.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to update the internal timestamp to.
        """
        self.date_profile.update(timestamp)

    def get_airmass(self, ids):
        """Get the airmass of the fields.

        The field ids stored in the airmass data are off-by-one from the stored field ids,
        hence the subtraction.

        Parameters
        ----------
        ids : list or numpy.array
            The set of fields to retrieve the airmass for.

        Returns
        -------
        numpy.array
            The set of airmasses.
        """
        return self.sky_brightness.returnAirmass(self.date_profile.mjd, indx=ids - 1, badval=float('nan'))

    def get_alt_az(self, ra, dec):
        """Get the altitude (radians) and azimuth (radians) of a given sky position.

        Parameters
        ----------
        ra : numpy.array
            The right-ascension (radians) of the sky position.
        dec : numpy.array
            The declination (radians) of the sky position.

        Returns
        -------
        tuple
            The altitude and azimuth of the sky position.
        """
        hour_angle = self.date_profile.lst_rad - ra
        azimuth, altitude = palpy.de2hVector(hour_angle, dec, self.date_profile.location.latitude_rad)
        return altitude, azimuth

    def get_moon_sun_info(self, field_ra, field_dec):
        """Return the current moon and sun information.

        This function gets the right-ascension, declination, altitude, azimuth, phase and
        angular distance from target (by given ra and dec) for the moon and the right-ascension,
        declination, altitude, azimuth and solar elongation from target (by given ra and dec) for the sun.

        Parameters
        ----------
        field_ra : numpy.array
            The target right-ascension (radians).
        field_dec : numpy.array
            The target declination (radians).

        Returns
        -------
        dict
            The set of information pertaining to the moon and sun. All angles are in radians.
        """
        attrs = self.sky_brightness.returnSunMoon(self.date_profile.mjd)
        moon_distance = self.get_separation("moon", field_ra, field_dec)
        sun_distance = self.get_separation("sun", field_ra, field_dec)

        keys = ["moonRA", "moonDec", "sunRA", "sunDec"]
        info_dict = {}
        for key in keys:
            info_dict[key] = attrs[key]
        # moonSunSep is in degrees! Oops!
        info_dict["moonPhase"] = attrs["moonSunSep"] / 180.0 * 100.0
        info_dict["moonAlt"], info_dict["moonAz"] = self.get_alt_az(numpy.array([attrs["moonRA"]]),
                                                                    numpy.array([attrs["moonDec"]]))
        info_dict["sunAlt"], info_dict["sunAz"] = self.get_alt_az(numpy.array([attrs["sunRA"]]),
                                                                  numpy.array([attrs["sunDec"]]))
        info_dict["moonDist"] = moon_distance
        info_dict["solarElong"] = sun_distance
        return info_dict

    def get_night_boundaries(self, sun_altitude, upper_limb_correction=False, precision=6):
        """Return the set/rise times of the sun for the given altitude.

        This function calculates the night boundaries (the set and rise times) for a
        given sun altitude. It uses the currently stored timestamp in the :class:`DateProfile`
        instance.

        Parameters
        ----------
        sun_altitude : float
            The altitude of the sun to get the set/rise times for.
        upper_limb_correction : bool
            Set to True is the upper limb correction should be calculated.
        precision : int, optional
            The place to round the rise/set times.

        Returns
        -------
        tuple (float, float)
            A tuple of the set and rise times, respectively, for the sun_altitiude.
        """
        longitude, latitude = (self.date_profile.location.longitude, self.date_profile.location.latitude)

        current_timestamp = self.date_profile.timestamp

        midnight_timestamp = self.date_profile.midnight_timestamp()
        (rise_time, set_time) = self.sun.altitude_times(midnight_timestamp, longitude, latitude,
                                                        sun_altitude, upper_limb_correction)

        set_timestamp = midnight_timestamp + (set_time * self.date_profile.SECONDS_IN_HOUR)
        rise_timestamp = midnight_timestamp + (rise_time * self.date_profile.SECONDS_IN_HOUR)

        if current_timestamp < rise_timestamp:
            midnight_timestamp = self.date_profile.previous_midnight_timestamp()
            (_, set_time) = self.sun.altitude_times(midnight_timestamp, longitude, latitude,
                                                    sun_altitude, upper_limb_correction)

            set_timestamp = midnight_timestamp + (set_time * self.date_profile.SECONDS_IN_HOUR)

        else:
            midnight_timestamp = self.date_profile.next_midnight_timestamp()
            (rise_time, _) = self.sun.altitude_times(midnight_timestamp, longitude, latitude,
                                                     sun_altitude, upper_limb_correction)

            rise_timestamp = midnight_timestamp + (rise_time * self.date_profile.SECONDS_IN_HOUR)

        return (round(set_timestamp, precision), round(rise_timestamp, precision))

    def get_separation(self, body, field_ra, field_dec):
        """Return the separation between a body and a set of field coordinates.

        This function returns the separation (in radians) between the given body (either moon or
        sun) and a given set of fields. It uses a list of (RA, Dec) coordinates. This function
        assumes that meth:`.get_sky_brightness` has been run.

        Parameters
        ----------
        body : str
            The name of the body to calculate the separation. Either moon or sun.
        field_ra : numpy.array(float)
            The list of field Righ Ascensions in radians.
        field_dec : numpy.array(float)
            The list of field Declinations in radians.

        Returns
        -------
        numpy.array(float)
            The list of field-moon separations in radians.
        """
        attrs = self.sky_brightness.returnSunMoon(self.date_profile.mjd)
        return palpy.dsepVector(field_ra, field_dec, numpy.full_like(field_ra, attrs["{}RA".format(body)]),
                                numpy.full_like(field_dec, attrs["{}Dec".format(body)]))

    def get_sky_brightness(self, ids, extrapolate=False, override_exclude_planets=None):
        """Get the LSST 6 filter sky brightness for a set of fields at a single time.

        This function retrieves the LSST 6 filter sky brightness magnitudes for a given set
        of fields at the MJD kept by the :class:`.DateProfile.`

        The field ids stored in the sky brightness data are off-by-one from the stored field ids,
        hence the subtraction.

        Parameters
        ----------
        ids : list or numpy.array
            The set of fields to retrieve the sky brightness for.
        extrapolate : boolean, optional
            Flag to extrapolate fields with bad sky brightness to nearest field that is good.
        override_exclude_planets : boolean, optional
            Override the internally stored exclude_planets flag.

        Returns
        -------
        numpy.ndarray
            The LSST 6 filter sky brightness magnitudes.
        """
        if override_exclude_planets is not None:
            exclude_planets = override_exclude_planets
        else:
            exclude_planets = self.exclude_planets

        return self.sky_brightness.returnMags(self.date_profile.mjd, indx=ids - 1,
                                              badval=float('nan'), zenith_mask=False,
                                              planet_mask=exclude_planets,
                                              extrapolate=extrapolate)

    def get_sky_brightness_timeblock(self, timestamp, timestep, num_steps, ids):
        """Get LSST 6 filter sky brightness for a set of fields for a range of times.

        This function retrieves the LSST 6 filter sky brightness magnitudes for a given set
        of fields at a range of MJDs provided via the timeblock information.

        The field ids stored in the sky brightness data are off-by-one from the stored field ids,
        hence the subtraction.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to start the time block.
        timestep : float
            The number of seconds to increment the timestamp with.
        num_steps : int
            The number of steps to create for the time block.
        ids : list or numpy.array
            The set of fields to retrieve the sky brightness for.

        Returns
        -------
        numpy.ndarray
            The LSST 6 filter sky brightness magnitudes.
        """
        dp = DateProfile(0, self.date_profile.location)
        mags = []
        for i in xrange(num_steps):
            ts = timestamp + i * timestep
            mjd, _ = dp(ts)
            mags.append(self.sky_brightness.returnMags(dp.mjd, indx=ids - 1,
                                                       badval=float('nan'),
                                                       zenith_mask=False,
                                                       planet_mask=self.exclude_planets,
                                                       extrapolate=False))

        return mags

    def get_target_information(self, fid, ra, dec):
        """Get information about target(s).

        This function gathers airmass, altitude (radians) and azimuth (radians) information
        for the target.

        Parameters
        ----------
        fid : numpy.array
           The field id.
        ra : numpy.array
            The field right-ascension (radians).
        dec : numpy.array
            The field declination (radians).

        Returns
        -------
        dict
            Set of information about the target(s).
        """
        info_dict = {}
        info_dict["airmass"] = self.get_airmass(fid)
        altitude, azimuth = self.get_alt_az(ra, dec)
        info_dict["altitude"] = altitude
        info_dict["azimuth"] = azimuth
        return info_dict

    def sky_brightness_config(self):
        """Get the configuration from the SkyModelPre files.

        Returns
        -------
        list[tuple(key, value)]
        """
        config = []
        header = self.sky_brightness.header
        config.append(("sky_brightness_pre/program_version", sky_model_pre_version))
        config.append(("sky_brightness_pre/file_version", header['version']))
        config.append(("sky_brightness_pre/fingerprint", header['fingerprint']))
        config.append(("sky_brightness_pre/moon_dist_limit", header['moon_dist_limit']))
        config.append(("sky_brightness_pre/planet_dist_limit", header['planet_dist_limit']))
        config.append(("sky_brightness_pre/airmass_limit", header['airmass_limit']))
        config.append(("sky_brightness_pre/timestep", header['timestep'] * 24 * 3600))
        config.append(("sky_brightness_pre/timestep_max", header['timestep_max'] * 24 * 3600))
        config.append(("sky_brightness_pre/dm", header['dm']))
        return config
