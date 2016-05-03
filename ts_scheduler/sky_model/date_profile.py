from datetime import datetime
import math

import palpy

__all__ = ["DateProfile"]

class DateProfile(object):
    """
    This class handles calculating the Modified Julian Date and the Local Sidereal Time for
    the internal timestamp and location coordinates.
    """

    def __init__(self, timestamp, location):
        """Initialize the class.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp for a given date/time.
        location : ts_scheduler.observatoryModel.ObservatoryLocation
            The location site information instance.
        """
        self.location = location
        self.update(timestamp)

    def __call__(self, timestamp):
        """Modified Julian Date and Local Sidereal Time from instance.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to get the MJD and LST for.

        Returns
        -------
        (float, float)
            A tuple of the Modified Julian Date and Local Sidereal Time (radians).
        """
        self.update(timestamp)
        return (self.mjd, self.lst_rad)

    @property
    def lst_rad(self):
        """Return the Local Sidereal Time (radians) for the internal timestamp.

        Returns
        -------
        float
        """
        value = palpy.gmst(self.mjd) + self.location.longitude_rad
        if value < 0.:
            value += 2.0 * math.pi
        return value

    @property
    def mjd(self):
        """Return the Modified Julian Date for the internal timestamp.

        Returns
        -------
        float
        """
        mjd = palpy.caldj(self.current_dt.year, self.current_dt.month, self.current_dt.day)
        mjd += (self.current_dt.hour / 24.0) + (self.current_dt.minute / 1440.) + \
               (self.current_dt.second / 86400.)
        return mjd

    def update(self, timestamp):
        """Change the internal timestamp to requested one.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp to update the internal timestamp to.
        """
        self.timestamp = timestamp
        self.current_dt = datetime.utcfromtimestamp(self.timestamp)
