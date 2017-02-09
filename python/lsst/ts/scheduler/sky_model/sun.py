# -*- coding: iso-8859-1 -*-
from __future__ import division
from datetime import datetime
import math

__all__ = ["Sun"]

class Sun(object):
    """
    This class is a partial port of the converted Python class provided by Henrik Härkönen <radix@kortis.to>.

    NOTE: Only the functions that provide the "rise" and "set" times for a given altitude on a given
    day and the supporting functions have been ported into this class. Their APIs were changed to fit the
    current use.

    The original header for this class is given below.

    ***********************************************************************************
    SUNRISET.C - computes Sun rise/set times, start/end of twilight, and
             the length of the day at any date and latitude

    Written as DAYLEN.C, 1989-08-16

    Modified to SUNRISET.C, 1992-12-01

    (c) Paul Schlyter, 1989, 1992

    Released to the public domain by Paul Schlyter, December 1992
    ***********************************************************************************
    """

    END_ANGLE = 360.0
    INV_END_ANGLE = 1 / 360
    HALF_DEGREE = 0.5
    # Sun Altitudes (degrees)
    RISE_SET = -35 / 60
    CIVIL_TWILIGHT = -6.0
    NAUTICAL_TWILIGHT = -12.0
    ASTRONOMICAL_TWILIGHT = -18.0

    def __init__(self):
        """Initialize the class.
        """
        pass

    def days_since_2000_jan_0(self, timestamp):
        """Compute number of days since 2000 Jan 0.0

        The 2000 Jan 0.0 is equivalent to 1999 Dec 31.

        Parameters
        ----------
        timestamp : float
            A UNIX timestamp for the date.

        Returns
        -------
        int
            The number of days elapsed.
        """
        date = datetime.utcfromtimestamp(timestamp)
        start = datetime(1999, 12, 31)
        return (date - start).days

    def gmst0(self, days):
        """Compute the Greenwich Mean Sidereal Time at 0h UT

        This function computes GMST0, the Greenwich Mean Sidereal Time
        at 0h UT (i.e. the sidereal time at the Greenwhich meridian at
        0h UT).  GMST is then the sidereal time at Greenwich at any
        time of the day.  I've generalized GMST0 as well, and define it
        as:  GMST0 = GMST - UT  --  this allows GMST0 to be computed at
        other times than 0h UT as well.  While this sounds somewhat
        contradictory, it is very practical:  instead of computing
        GMST like:

         GMST = (GMST0) + UT * (366.2422/365.2422)

        where (GMST0) is the GMST last time UT was 0 hours, one simply
        computes:

         GMST = GMST0 + UT

        where GMST0 is the GMST "at 0h UT" but at the current moment!
        Defined in this way, GMST0 will increase with about 4 min a
        day.  It also happens that GMST0 (in degrees, 1 hr = 15 degr)
        is equal to the Sun's mean longitude plus/minus 180 degrees!
        (if we neglect aberration, which amounts to 20 seconds of arc
        or 1.33 seconds of time)

        Parameters
        ----------
        day : int
            The number of days since 2000 Jan 0. adjusted for longitude.

        Returns
        -------
        float
            The Greenwich Mean Sidereal Time in degrees.
        """
        return self.normalize((180.0 + 356.0470 + 282.9404) + (0.9856002585 + 4.70935E-5) * days)

    def normalize(self, angle, from_minus_180=False):
        """Normalize angle into range.

        This function normalizes the given angle into the range 0 to 360. If the flag is
        used, the range becomes -180 to 180. NOTE: This function expects the angle in
        degrees.

        Parameters
        ----------
        angle : float
            The angle to normalize in degrees.
        from_minus_180 : bool
            Flag to make the range -180 to 180 if True.

        Returns
        -------
        float
            The normalized angle in degrees.
        """
        offset = 0.0
        if from_minus_180:
            offset = self.HALF_DEGREE
        return angle - self.END_ANGLE * math.floor(angle * self.INV_END_ANGLE + offset)

    def position(self, days):
        """Compute the ecliptic longitude and distance.

        This function computes the Sun's ecliptic longitude and distance at the days given.
        The Sun's eclipcit latitude is not computed since it's always very near zero.

        Parameters
        ----------
        day : int
            The number of days since 2000 Jan 0. adjusted for longitude.

        Returns
        -------
        (float, float)
            A tuple containing the ecliptic longitude (degrees) and distance (AU).
        """
        # Compute mean elements
        mean_anom = self.normalize(356.0470 + 0.9856002585 * days)
        mean_lon = 282.9404 + 4.70935E-5 * days
        eccen = 0.016709 - 1.151E-9 * days

        # Compute true longitude and radius vector
        mean_anom_rad = math.radians(mean_anom)
        e = mean_anom + math.degrees(eccen) * math.sin(mean_anom_rad) * \
            (1.0 + eccen * math.cos(mean_anom_rad))
        e_rad = math.radians(e)
        x = math.cos(e_rad) - eccen
        y = math.sqrt(1.0 - eccen * eccen) * math.sin(e_rad)
        # Solar distance
        distance = math.sqrt(x * x + y * y)
        # True anomaly
        true_anom = math.degrees(math.atan2(y, x))
        # True solar longitude
        longitude = true_anom + mean_lon
        if longitude >= 360.0:
            longitude -= 360.0   # Make it 0..360 degrees

        return (longitude, distance)

    def ra_dec(self, days):
        """Compute the right-ascension, declination and distance of the Sun.

        This function computes the right-ascension (RA), declination (Dec) and distance of the Sun
        at the given days.

        Parameters
        ----------
        day : int
            The number of days since 2000 Jan 0. adjusted for longitude.

        Returns
        -------
        (float, float, float)
            A tuple containing the RA (degrees), Dec (degrees) and distance (AU).
        """
        # Compute Sun's ecliptical coordinates
        (longitude, distance) = self.position(days)

        # Compute ecliptic rectangular coordinates (z=0)
        longitude_rad = math.radians(longitude)
        x = distance * math.cos(longitude_rad)
        y = distance * math.sin(longitude_rad)

        # Compute obliquity of ecliptic (inclination of Earth's axis)
        obl_ecl = 23.4393 - 3.563E-7 * days
        obl_ecl_rad = math.radians(obl_ecl)

        # Convert to equatorial rectangular coordinates - x is unchanged
        z = y * math.sin(obl_ecl_rad)
        y = y * math.cos(obl_ecl_rad)

        # Convert to spherical coordinates
        ra = math.degrees(math.atan2(y, x))
        dec = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))

        return (ra, dec, distance)

    def altitude_times(self, timestamp, longitude, latitude, altitude, upper_limb):
        """Compute times (morning, evening) when Sun is at a given altitude.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp from a specific date.
        longitude : float
            The longitude of the location on Earth (degrees). South is negative, North is positive
        latitude : float
            The latitude of the location on Earth (degrees). West is negative, East is positive.
        altitude : float
            The altitude of the Sun for time calculations (degrees).
        upper_limb : bool
            Flag to use the upper limb for Sun's altitude. False is Sun's center.

        Returns
        -------
        float, float
            A tuple containing the morning and evening times (hours UT) respectively for the given altitude.
        """
        # Compute d of 12h local mean solar time
        days = self.days_since_2000_jan_0(timestamp) + 0.5 - (longitude / 360.0)

        # Compute local sidereal time of this moment
        sid_time = self.normalize(self.gmst0(days) + 180.0 + longitude)

        # Compute Sun's RA + Decl at this moment
        (sun_ra, sun_dec, sun_dist) = self.ra_dec(days)

        # Compute time when Sun is at south - in hours UT
        time_south = 12.0 - self.normalize(sid_time - sun_ra, from_minus_180=True) / 15.0

        # Compute the Sun's apparent radius, degrees
        sun_radius = 0.2666 / sun_dist

        # Do correction to upper limb, if necessary
        if upper_limb:
            altitude -= sun_radius

        altitude_rad = math.radians(altitude)
        latitude_rad = math.radians(latitude)
        sun_dec_rad = math.radians(sun_dec)

        # Compute the diurnal arc that the Sun traverses to reach the specified altitude
        numer = math.sin(altitude_rad) - math.sin(latitude_rad) * math.sin(sun_dec_rad)
        denom = math.cos(latitude_rad) * math.cos(sun_dec_rad)
        cost = numer / denom

        if cost >= 1.0:
            # Sun always below altitude
            t = 0.0
        elif cost <= -1.0:
            # Sun always above altitude
            t = 12.0
        else:
            # The diurnal arc, hours
            t = math.degrees(math.acos(cost)) / 15.0

        # Store rise and set times - in hours UT
        return (time_south - t, time_south + t)

    def rise_set(self, timestamp, longitude, latitude):
        """Compute Sun rise and set times.

        Sun rise or set is considered to occur when the Sun's upper limb is 35 arc minutes below the
        horizon. This accounts for the refraction of the Earth's atmosphere.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp from a specific date.
        longitude : float
            The longitude of the location on Earth (degrees). South is negative, North is positive
        latitude : float
            The latitude of the location on Earth (degrees). West is negative, East is positive.

        Returns
        -------
        float, float
            A tuple containing the Sun rise and set times (hours UT).
        """
        return self.altitude_times(timestamp, longitude, latitude, self.RISE_SET, True)

    def civil_twilight(self, timestamp, longitude, latitude):
        """Compute times of civil twilight.

        Civil twilight starts and ends when the Sun's center is 6 degrees below the horizon.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp from a specific date.
        longitude : float
            The longitude of the location on Earth (degrees). South is negative, North is positive
        latitude : float
            The latitude of the location on Earth (degrees). West is negative, East is positive.

        Returns
        -------
        float, float
            A tuple containing the civil twilight times (hours UT).
        """
        return self.altitude_times(timestamp, longitude, latitude, self.CIVIL_TWILIGHT, False)

    def nautical_twilight(self, timestamp, longitude, latitude):
        """Compute times of nautical twilight.

        Nautical twilight starts and ends when the Sun's center is 12 degrees below the horizon.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp from a specific date.
        longitude : float
            The longitude of the location on Earth (degrees). South is negative, North is positive
        latitude : float
            The latitude of the location on Earth (degrees). West is negative, East is positive.

        Returns
        -------
        float, float
            A tuple containing the nautical twilight times (hours UT).
        """
        return self.altitude_times(timestamp, longitude, latitude, self.NAUTICAL_TWILIGHT, False)

    def astronomical_twilight(self, timestamp, longitude, latitude):
        """Compute times of astronomical twilight.

        Astronomical twilight starts and ends when the Sun's center is 18 degrees below the horizon.

        Parameters
        ----------
        timestamp : float
            The UNIX timestamp from a specific date.
        longitude : float
            The longitude of the location on Earth (degrees). South is negative, North is positive
        latitude : float
            The latitude of the location on Earth (degrees). West is negative, East is positive.

        Returns
        -------
        float, float
            A tuple containing the astronomical twilight times (hours UT).
        """
        return self.altitude_times(timestamp, longitude, latitude, self.ASTRONOMICAL_TWILIGHT, False)
