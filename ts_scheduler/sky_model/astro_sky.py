from enum import Enum
import logging
import numpy

from lsst.sims.skybrightness import SkyModel

from .date_profile import DateProfile

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

    def update(self, timestamp):
        """Update the internal timestamp.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to update the internal timestamp to.
        """
        self.date_profile.update(timestamp)

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
