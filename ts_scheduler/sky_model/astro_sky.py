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

    def get_moon_separation(self, field_ra, field_dec):
        """Return the moon separation for a set of field coordinates.

        This function returns the separation (in radians) between the moon and a given field. It uses
        a list of (RA, Dec) coordinates. This function assumes that meth:`.get_sky_brightness` has been run.

        Parameters
        ----------
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
        return palpy.dsepVector(field_ra, field_dec, numpy.full_like(field_ra, attrs["moonRA"]),
                                numpy.full_like(field_dec, attrs["moonDec"]))

    def get_night_boundaries(self, sun_altitude, upper_limb_correction=False):
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

        Returns
        -------
        tuple (float, float)
            A tuple of the set and rise times, respectively, for the sun_altitiude.
        """
        longitude, latitude = (self.date_profile.location.longitude, self.date_profile.location.latitude)
        current_midnight_timestamp = self.date_profile.midnight_timestamp()
        (_, set_time) = self.sun.altitude_times(current_midnight_timestamp, longitude, latitude,
                                                sun_altitude, upper_limb_correction)
        set_timestamp = current_midnight_timestamp + (set_time * self.date_profile.SECONDS_IN_HOUR)
        next_midnight_timestamp = self.date_profile.next_midnight_timestamp()
        (rise_time, _) = self.sun.altitude_times(next_midnight_timestamp, longitude, latitude,
                                                 sun_altitude, upper_limb_correction)
        rise_timestamp = next_midnight_timestamp + (rise_time * self.date_profile.SECONDS_IN_HOUR)

        return (set_timestamp, rise_timestamp)

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

        return numpy.stack(mags)
