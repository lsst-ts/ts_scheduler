from enum import Enum
import logging
import numpy
import palpy

from lsst.sims.skybrightness import SkyModel

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
        self.sky_brightness = SkyModel(mags=True)
        self.sun = Sun()

    def update(self, timestamp):
        """Update the internal timestamp.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to update the internal timestamp to.
        """
        self.date_profile.update(timestamp)

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
        attrs = self.sky_brightness.getComputedVals()
        return palpy.dsepVector(field_ra, field_dec, numpy.full_like(field_ra, attrs["{}RA".format(body)]),
                                numpy.full_like(field_dec, attrs["{}Dec".format(body)]))

    def get_moon_sun_info(self, field_ra, field_dec, need_update=False):
        """Return the current moon and sun information.

        This function gets the right-ascension, declination, altitude, azimuth, phase and
        angular distance from target (by given ra and dec) for the moon and the altitude,
        azimuth ans elongation for the sun.

        Parameters
        ----------
        field_ra : float
            The target right-ascension (radians) for the moon distance.
        field_dec : float
            The target declination (radians) for the moon distance.
        need_update : boolean, optional
            Flag to request an update for sky brightness parameters.

        Returns
        -------
        dict
            The set of information pertaining to the moon and sun. All angles are in radians.
        """
        nra = numpy.array([field_ra])
        ndec = numpy.array([field_dec])
        if need_update:
            self.sky_brightness.setRaDecMjd(nra, ndec, self.date_profile.mjd)
        attrs = self.sky_brightness.getComputedVals()
        moon_distance = self.get_separation("moon", nra, ndec)
        sun_distance = self.get_separation("sun", nra, ndec)

        keys = ["moonAlt", "moonAz", "moonRA", "moonDec", "moonPhase",
                "sunAlt", "sunAz", "sunRA", "sunDec"]
        info_dict = {}
        for key in keys:
            info_dict[key] = attrs[key]
        info_dict["moonDist"] = moon_distance[0]
        info_dict["solarElong"] = sun_distance[0]
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

    def get_sky_brightness(self, ra, dec):
        """Get the LSST 6 filter sky brightness for a set of positions at a single time.

        This function retrieves the LSST 6 filter sky brightness magnitudes for a given set
        of sky positions at the MJD kept by the :class:`.DateProfile.`

        Parameters
        ----------
        ra : numpy.ndarray
            The right ascension values (radians) for the sky positions.
        dec : numpy.ndarray
            The declination values (radians) for the sky positions.

        Returns
        -------
        numpy.ndarray
            The LSST 6 filter sky brightness magnitudes.
        """
        self.sky_brightness.setRaDecMjd(ra, dec, self.date_profile.mjd)
        return self.sky_brightness.returnMags()

    def get_sky_brightness_timeblock(self, timestamp, timestep, num_steps, ra, dec):
        """Get LSST 6 filter sky brightness for a set of positions for a range of times.

        This function retrieves the LSST 6 filter sky brightness magnitudes for a given set
        of sky positions at a range of MJDs provided via the timeblock information.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to start the time block.
        timestep : float
            The number of seconds to increment the timestamp with.
        num_steps : int
            The number of steps to create for the time block.
        ra : numpy.ndarray
            The right ascension values (radians) for the sky positions.
        dec : numpy.ndarray
            The declination values (radians) for the sky positions.

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
            self.sky_brightness.setRaDecMjd(ra, dec, mjd)
            mags.append(self.sky_brightness.returnMags())

        return mags

    def get_target_information(self):
        """Get information about target(s).

        This function gathers airmass, altitude and azimuth information for the targets
        that were last computed.

        Returns
        -------
        dict
            Set of information about the target(s).
        """
        attrs = self.sky_brightness.getComputedVals()
        keys = ["airmass", "alts", "azs"]
        info_dict = {}
        for key in keys:
            info_dict[key] = attrs[key]
        return info_dict
