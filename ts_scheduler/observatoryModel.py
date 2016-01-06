import math
import re

import palpy as pal

from schedulerDefinitions import TWOPI, RAD2DEG, DEG2RAD, INFOX

#####################################################################
class ObservatoryLocation(object):

    def __init__(self,
                 latitude_RAD=0.0,
                 longitude_RAD=0.0,
                 height=0.0):
        # meters
        self.Height = height

        # radians
        self.latitude_RAD = latitude_RAD
        self.longitude_RAD = longitude_RAD

#####################################################################
class ObservatoryPosition(object):

    def __init__(self,
                 time=0.0,
                 ra_RAD=0.0,
                 dec_RAD=0.0,
                 ang_RAD=0.0,
                 filter='r',
                 tracking=False,
                 alt_RAD=1.5,
                 az_RAD=0.0,
                 pa_RAD=0.0,
                 rot_RAD=0.0):

        self.time = time
        self.ra_RAD = ra_RAD
        self.dec_RAD = dec_RAD
        self.ang_RAD = ang_RAD
        self.filter = filter
        self.tracking = tracking
        self.alt_RAD = alt_RAD
        self.az_RAD = az_RAD
        self.pa_RAD = pa_RAD
        self.rot_RAD = rot_RAD

    def __str__(self):
        return ("t=%.1f ra=%.3f dec=%.3f ang=%.3f filter=%s track=%s alt=%.3f az=%.3f rot=%.3f" %
                (self.time, self.ra_RAD * RAD2DEG, self.dec_RAD * RAD2DEG, self.ang_RAD * RAD2DEG,
                 self.filter, self.tracking, self.alt_RAD * RAD2DEG, self.az_RAD * RAD2DEG,
                 self.rot_RAD * RAD2DEG))

#####################################################################
class ObservatoryState(ObservatoryPosition):

    def __init__(self,
                 time=0.0,
                 ra_RAD=0.0,
                 dec_RAD=0.0,
                 ang_RAD=0.0,
                 filter='r',
                 tracking=False,
                 alt_RAD=1.5,
                 az_RAD=0.0,
                 pa_RAD=0.0,
                 rot_RAD=0.0,
                 telAlt_RAD=1.5,
                 telAz_RAD=0.0,
                 telRot_RAD=0.0,
                 domAlt_RAD=1.5,
                 domAz_RAD=0.0,
                 mountedFilters=['g', 'r', 'i', 'z', 'y'],
                 unmountedFilters=['u']):

        super(ObservatoryState, self).__init__(time,
                                               ra_RAD,
                                               dec_RAD,
                                               ang_RAD,
                                               filter,
                                               tracking,
                                               alt_RAD,
                                               az_RAD,
                                               pa_RAD,
                                               rot_RAD)

        self.telAlt_RAD = telAlt_RAD
        self.telAz_RAD = telAz_RAD
        self.telRot_RAD = telRot_RAD
        self.domAlt_RAD = domAlt_RAD
        self.domAz_RAD = domAz_RAD
        self.mountedFilters = list(mountedFilters)
        self.unmountedFilters = list(unmountedFilters)

    def set(self, newState):

        self.time = newState.time
        self.ra_RAD = newState.ra_RAD
        self.dec_RAD = newState.dec_RAD
        self.ang_RAD = newState.ang_RAD
        self.filter = newState.filter
        self.tracking = newState.tracking
        self.alt_RAD = newState.alt_RAD
        self.az_RAD = newState.az_RAD
        self.pa_RAD = newState.pa_RAD
        self.rot_RAD = newState.rot_RAD

        self.telAlt_RAD = newState.telAlt_RAD
        self.telAz_RAD = newState.telAz_RAD
        self.telRot_RAD = newState.telRot_RAD
        self.domAlt_RAD = newState.domAlt_RAD
        self.domAz_RAD = newState.domAz_RAD
        self.mountedFilters = list(newState.mountedFilters)
        self.unmountedFilters = list(newState.unmountedFilters)

    def setPosition(self, newPosition):

        self.time = newPosition.time
        self.ra_RAD = newPosition.ra_RAD
        self.dec_RAD = newPosition.dec_RAD
        self.ang_RAD = newPosition.ang_RAD
        self.filter = newPosition.filter
        self.tracking = newPosition.tracking
        self.alt_RAD = newPosition.alt_RAD
        self.az_RAD = newPosition.az_RAD
        self.pa_RAD = newPosition.pa_RAD
        self.rot_RAD = newPosition.rot_RAD

        self.telAlt_RAD = newPosition.alt_RAD
        self.telAz_RAD = newPosition.az_RAD
        self.telRot_RAD = newPosition.rot_RAD
        self.domAlt_RAD = newPosition.alt_RAD
        self.domAz_RAD = newPosition.az_RAD

#####################################################################
class ObservatoryModel(object):

    def __init__(self, log):

        self.log = log

        self.location = ObservatoryLocation()
        self.parkState = ObservatoryState()
        self.currentState = ObservatoryState()

    def __str__(self):
        return self.currentState.__str__()

    def configure(self, observatoryConf):

        self.location.latitude_RAD = math.radians(observatoryConf["obs_site"]["latitude"])
        self.location.longitude_RAD = math.radians(observatoryConf["obs_site"]["longitude"])
        self.location.height = observatoryConf["obs_site"]["height"]

        self.TelAlt_MinPos_RAD = math.radians(observatoryConf["telescope"]["altitude_minpos"])
        self.TelAlt_MaxPos_RAD = math.radians(observatoryConf["telescope"]["altitude_maxpos"])
        self.TelAz_MinPos_RAD = math.radians(observatoryConf["telescope"]["azimuth_minpos"])
        self.TelAz_MaxPos_RAD = math.radians(observatoryConf["telescope"]["azimuth_maxpos"])
        self.TelRot_MinPos_RAD = math.radians(observatoryConf["rotator"]["minpos"])
        self.TelRot_MaxPos_RAD = math.radians(observatoryConf["rotator"]["maxpos"])
        self.TelRot_FilterPos_RAD = math.radians(observatoryConf["rotator"]["filter_pos"])

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MinPos_RAD=%.3f" % (self.TelAlt_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxPos_RAD=%.3f" % (self.TelAlt_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MinPos_RAD=%.3f" % (self.TelAz_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxPos_RAD=%.3f" % (self.TelAz_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MinPos_RAD=%.3f" % (self.TelRot_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MaxPos_RAD=%.3f" % (self.TelRot_MaxPos_RAD))
        self.log.log(INFOX,
                     "ObservatoryModel: configure TelRot_FilterPos_RAD=%.3f" % (self.TelRot_FilterPos_RAD))

        self.Rotator_FollowSky = observatoryConf["rotator"]["follow_sky"]
        self.Rotator_ResumeAngle = observatoryConf["rotator"]["resume_angle"]

        self.log.log(INFOX, "ObservatoryModel: configure Rotator_FollowSky=%s" % (self.Rotator_FollowSky))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_ResumeAngle=%s" % (self.Rotator_ResumeAngle))

        self.Filter_MountedList = observatoryConf["camera"]["filter_mounted"]
        self.Filter_RemovableList = observatoryConf["camera"]["filter_removable"]
        self.Filter_UnmountedList = observatoryConf["camera"]["filter_unmounted"]

        self.log.log(INFOX, "ObservatoryModel: configure Filter_MountedList=%s" % (self.Filter_MountedList))
        self.log.log(INFOX,
                     "ObservatoryModel: configure Filter_RemovableList=%s" % (self.Filter_RemovableList))
        self.log.log(INFOX,
                     "ObservatoryModel: configure Filter_UnmountedList=%s" % (self.Filter_UnmountedList))

        self.TelAlt_MaxSpeed_RAD = math.radians(observatoryConf["telescope"]["altitude_maxspeed"])
        self.TelAlt_Accel_RAD = math.radians(observatoryConf["telescope"]["altitude_accel"])
        self.TelAlt_Decel_RAD = math.radians(observatoryConf["telescope"]["altitude_decel"])
        self.TelAz_MaxSpeed_RAD = math.radians(observatoryConf["telescope"]["azimuth_maxspeed"])
        self.TelAz_Accel_RAD = math.radians(observatoryConf["telescope"]["azimuth_accel"])
        self.TelAz_Decel_RAD = math.radians(observatoryConf["telescope"]["azimuth_decel"])
        self.TelRot_MaxSpeed_RAD = math.radians(observatoryConf["rotator"]["maxspeed"])
        self.TelRot_Accel_RAD = math.radians(observatoryConf["rotator"]["accel"])
        self.TelRot_Decel_RAD = math.radians(observatoryConf["rotator"]["decel"])
        self.DomAlt_MaxSpeed_RAD = math.radians(observatoryConf["dome"]["altitude_maxspeed"])
        self.DomAlt_Accel_RAD = math.radians(observatoryConf["dome"]["altitude_accel"])
        self.DomAlt_Decel_RAD = math.radians(observatoryConf["dome"]["altitude_decel"])
        self.DomAz_MaxSpeed_RAD = math.radians(observatoryConf["dome"]["azimuth_maxspeed"])
        self.DomAz_Accel_RAD = math.radians(observatoryConf["dome"]["azimuth_accel"])
        self.DomAz_Decel_RAD = math.radians(observatoryConf["dome"]["azimuth_decel"])

        self.log.log(INFOX,
                     "ObservatoryModel: configure TelAlt_MaxSpeed_RAD=%.3f" % (self.TelAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Accel_RAD=%.3f" % (self.TelAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Decel_RAD=%.3f" % (self.TelAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxSpeed_RAD=%.3f" % (self.TelAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Accel_RAD=%.3f" % (self.TelAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Decel_RAD=%.3f" % (self.TelAz_Decel_RAD))
        self.log.log(INFOX,
                     "ObservatoryModel: configure TelRot_MaxSpeed_RAD=%.3f" % (self.TelRot_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Accel_RAD=%.3f" % (self.TelRot_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Decel_RAD=%.3f" % (self.TelRot_Decel_RAD))
        self.log.log(INFOX,
                     "ObservatoryModel: configure DomAlt_MaxSpeed_RAD=%.3f" % (self.DomAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Accel_RAD=%.3f" % (self.DomAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Decel_RAD=%.3f" % (self.DomAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_MaxSpeed_RAD=%.3f" % (self.DomAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Accel_RAD=%.3f" % (self.DomAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Decel_RAD=%.3f" % (self.DomAz_Decel_RAD))

        self.Filter_ChangeTime = observatoryConf["camera"]["filter_change_time"]
        self.Mount_SettleTime = observatoryConf["telescope"]["settle_time"]
        self.DomAz_SettleTime = observatoryConf["dome"]["settle_time"]
        self.ReadoutTime = observatoryConf["camera"]["readout_time"]
        self.ShutterTime = observatoryConf["camera"]["shutter_time"]

        self.log.log(INFOX, "ObservatoryModel: configure Filter_ChangeTime=%.1f" % (self.Filter_ChangeTime))
        self.log.log(INFOX, "ObservatoryModel: configure Mount_SettleTime=%.1f" % (self.Mount_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_SettleTime=%.1f" % (self.DomAz_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure ReadoutTime=%.1f" % (self.ReadoutTime))
        self.log.log(INFOX, "ObservatoryModel: configure ShutterTime=%.1f" % (self.ShutterTime))

        # Shouldn't these be converted to radians?
        self.OpticsOL_Slope = observatoryConf["slew"]["tel_optics_ol_slope"]
        self.OpticsCL_Delay = observatoryConf["slew"]["tel_optics_cl_delay"]
        self.OpticsCL_AltLimit = observatoryConf["slew"]["tel_optics_cl_alt_limit"]

        self.log.log(INFOX, "ObservatoryModel: configure OpticsOL_Slope=%.3f" % (self.OpticsOL_Slope))
        self.log.log(INFOX, "ObservatoryModel: configure OpticsCL_Delay=%s" % (self.OpticsCL_Delay))
        self.log.log(INFOX, "ObservatoryModel: configure OpticsCL_AltLimit=%s" % (self.OpticsCL_AltLimit))

        self.activities = ["TelAlt",
                           "TelAz",
                           "TelRot",
                           "DomAlt",
                           "DomAz",
                           "Filter",
                           "TelSettle",
                           "DomAzSettle",
                           "Readout",
                           "TelOpticsOL",
                           "TelOpticsCL",
                           "Exposure"]

        # Split on camel case and acronyms
        key_re = re.compile(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))')
        self.prerequisites = {}
        for activity in self.activities:
            activity_key = "_".join([s.lower() for s in key_re.findall(activity)])
            key = "prereq_" + activity_key
            self.prerequisites[activity] = observatoryConf["slew"][key]
            self.log.log(INFOX,
                         "ObservatoryModel: configure prerequisites[%s]=%s" %
                         (activity, self.prerequisites[activity]))

        self.parkState.alt_RAD = math.radians(observatoryConf["park"]["telescope_altitude"])
        self.parkState.az_RAD = math.radians(observatoryConf["park"]["telescope_azimuth"])
        self.parkState.rot_RAD = math.radians(observatoryConf["park"]["telescope_rotator"])
        self.parkState.telAlt_RAD = math.radians(observatoryConf["park"]["telescope_altitude"])
        self.parkState.telAz_RAD = math.radians(observatoryConf["park"]["telescope_azimuth"])
        self.parkState.telRot_RAD = math.radians(observatoryConf["park"]["telescope_rotator"])
        self.parkState.domAlt_RAD = math.radians(observatoryConf["park"]["dome_altitude"])
        self.parkState.domAz_RAD = math.radians(observatoryConf["park"]["dome_azimuth"])
        self.parkState.filter = observatoryConf["park"]["filter_position"]
        self.parkState.mountedFilters = self.Filter_MountedList
        self.parkState.unmountedFilters = self.Filter_UnmountedList
        self.parkState.tracking = False

        self.log.log(INFOX, "ObservatoryModel: configure park_TelAlt_RAD=%.3f" % (self.parkState.telAlt_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_TelAz_RAD=%.3f" % (self.parkState.telAz_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_TelRot_RAD=%.3f" % (self.parkState.telRot_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_DomAlt_RAD=%.3f" % (self.parkState.domAlt_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_DomAz_RAD=%.3f" % (self.parkState.domAz_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_Filter=%s" % (self.parkState.filter))

        self.reset()

    def reset(self):

        self.setState(self.parkState)

    def setState(self, newState):

        self.currentState.set(newState)

    def observe(self, topicObservation):
        return

    def slewAltAzRot(self, time, alt, az, rot):

        targetPosition = ObservatoryPosition()
        targetPosition.time = time
        targetPosition.tracking = False
        targetPosition.alt_RAD = alt * DEG2RAD
        targetPosition.az_RAD = az * DEG2RAD
        targetPosition.rot_RAD = rot * DEG2RAD

        self.currentState.setPosition(targetPosition)

    def estimateSlewTime(self):
        return

    def park(self):
        return

    def slew(self, target):
        return

    def Date2Lst(self, time):
        """
        Computes the Local Sidereal Time for the given TIME.
        inputs:
               TIME: Time in seconds since simulation reference (SIMEPOCH)
        output:
               LST:  Local Sidereal Time in radians.
        """

        UT_day = 57388 + time / 86400.0

        # LSST convention of West=negative, East=positive
        LST_RAD = pal.gmst(UT_day) + self.location.longitude_RAD

        return LST_RAD

    def AltAz2RaDecPa(self, time, alt_RAD, az_RAD):
        """
        Converts ALT, AZ coordinates into RA DEC for the given TIME.

        inputs:
               alt_RAD: Altitude in radians [-90.0deg  90.0deg] 90deg=>zenith
               az_RAD:  Azimuth in radians [  0.0deg 360.0deg] 0deg=>N 90deg=>E
               time:    Time in seconds since simulation reference (SIMEPOCH)
        output:
               (ra_RAD, dec_RAD)
               ra_RAD:  Right Ascension in radians
               dec_RAD: Declination in radians
        """
        LST_RAD = self.Date2Lst(time)

        (HA_RAD, dec_RAD) = pal.dh2e(az_RAD, alt_RAD, self.location.latitude_RAD)
        pa_RAD = pal.pa(HA_RAD, dec_RAD, self.location.latitude_RAD)
        ra_RAD = LST_RAD - HA_RAD

        return (ra_RAD, dec_RAD, pa_RAD)

    def RaDec2AltAzPa(self, time, ra_RAD, dec_RAD):
        """
        Converts RA_RAD, DEC_RAD coordinates into ALT_RAD AZ_RAD for given DATE.
        inputs:
               RA_RAD:  Right Ascension in radians
               DEC_RAD: Declination in radians
               DATE: Time in seconds since simulation reference (SIMEPOCH)
        output:
               (ALT_RAD, AZ_RAD, PA_RAD, HA_HOU)
               ALT_RAD: Altitude in radians [-90.0  90.0] 90=>zenith
               AZ_RAD:  Azimuth in radians [  0.0 360.0] 0=>N 90=>E
               PA_RAD:  Parallactic Angle in radians
               HA_HOU:  Hour Angle in hours
        """
        LST_RAD = self.Date2Lst(time)
        HA_RAD = LST_RAD - ra_RAD

        (az_RAD, alt_RAD) = pal.de2h(HA_RAD, dec_RAD, self.location.latitude_RAD)
        pa_RAD = pal.pa(HA_RAD, dec_RAD, self.location.latitude_RAD)

        return (alt_RAD, az_RAD, pa_RAD)

    def startTracking(self, time):
        if not self.currentState.tracking:
            self.updateState(time)
            self.currentState.tracking = True

    def stopTracking(self, time):
        if self.currentState.tracking:
            self.updateState(time)
            self.currentState.tracking = False

    def updateState(self, time):

        if self.currentState.tracking:
            (alt_RAD, az_RAD, pa_RAD) = self.RaDec2AltAzPa(time,
                                                           self.currentState.ra_RAD,
                                                           self.currentState.dec_RAD)
            az_RAD = divmod(az_RAD, TWOPI)[1]
            pa_RAD = divmod(pa_RAD, TWOPI)[1]
            rot_RAD = pa_RAD + self.currentState.ang_RAD

            self.currentState.time = time
            self.currentState.alt_RAD = alt_RAD
            self.currentState.az_RAD = az_RAD
            self.currentState.pa_RAD = pa_RAD
            self.currentState.rot_RAD = rot_RAD

            self.currentState.telAlt_RAD = alt_RAD
            self.currentState.telAz_RAD = az_RAD
            self.currentState.telRot_RAD = rot_RAD
            self.currentState.domAlt_RAD = alt_RAD
            self.currentState.domAz_RAD = az_RAD
        else:
            (ra_RAD, dec_RAD, pa_RAD) = self.AltAz2RaDecPa(time,
                                                           self.currentState.alt_RAD,
                                                           self.currentState.az_RAD)
            pa_RAD = divmod(pa_RAD, TWOPI)[1]
            self.currentState.time = time
            self.currentState.ra_RAD = ra_RAD
            self.currentState.dec_RAD = dec_RAD
            self.currentState.ang_RAD = self.currentState.rot_RAD - pa_RAD
