import math

from ts_scheduler.observatoryModel import ObservatoryLocation

"""Set timestamp as 2022-01-01 0h UTC"""
LSST_START_TIMESTAMP = 1640995200.0

"""Set MJD for 2022-01-01 0h UTC"""
LSST_START_MJD = 59580.0

"""LSST latitude (degrees)"""
LSST_LATITUDE = -30.2444

"""LSST longitude (degrees)"""
LSST_LONGITUDE = -70.7494

"""LSST elevation (meters)"""
LSST_ELEVATION = 2650.0

"""LSST observing site information"""
LSST_SITE = ObservatoryLocation(math.radians(LSST_LATITUDE), math.radians(LSST_LONGITUDE), LSST_ELEVATION)

"Number of LSST Filters"
LSST_NUM_FILTERS = 6
