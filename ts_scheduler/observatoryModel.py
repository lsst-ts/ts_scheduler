from schedulerDefinitions import *
import palpy as pal

#####################################################################
class ObservatoryLocation(object):

    def __init__ (self, 
                  latitude_RAD,
                  longitude_RAD,
                  height):
        # meters
        self.Height    = height

        # radians 
        self.latitude_RAD  = latitude_RAD
        self.longitude_RAD = longitude_RAD

        return

#####################################################################
class ObservatoryPosition(object):

    def __init__(self,
                    time     = 0.0,
                    ra_RAD   = 0.0,
                    dec_RAD  = 0.0,
                    ang_RAD  = 0.0,
                    filter   = 'r',
                    tracking = False,
                    alt_RAD  = 1.5,
                    az_RAD   = 0.0,
                    pa_RAD   = 0.0,
                    rot_RAD  = 0.0):

        self.time     = time
        self.ra_RAD   = ra_RAD
        self.dec_RAD  = dec_RAD
        self.ang_RAD  = ang_RAD
        self.filter   = filter
        self.tracking = tracking
        self.alt_RAD  = alt_RAD
        self.az_RAD   = az_RAD
        self.pa_RAD   = pa_RAD
        self.rot_RAD  = rot_RAD
        
        return

    def __str__(self):
        return "t=%.1f ra=%.3f dec=%.3f ang=%.3f filter=%s track=%s alt=%.3f az=%.3f rot=%.3f" % (self.time, self.ra_RAD*RAD2DEG, self.dec_RAD*RAD2DEG, self.ang_RAD*RAD2DEG, self.filter, self.tracking, self.alt_RAD*RAD2DEG, self.az_RAD*RAD2DEG, self.rot_RAD*RAD2DEG) 

#####################################################################
class ObservatoryState(ObservatoryPosition):

    def __init__(self,
                    time       = 0.0,
                    ra_RAD     = 0.0,
                    dec_RAD    = 0.0,
                    ang_RAD    = 0.0,
                    filter     = 'r',
                    tracking   = False,
                    alt_RAD    = 1.5,
                    az_RAD     = 0.0,
                    pa_RAD     = 0.0,
                    rot_RAD    = 0.0,
                    telAlt_RAD = 1.5,
                    telAz_RAD  = 0.0,
                    telRot_RAD = 0.0,
                    domAlt_RAD = 1.5,
                    domAz_RAD  = 0.0,
                    mountedFilters   = ['g','r','i','z','y'],
                    unmountedFilters = ['u']):

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
        self.telAz_RAD  = telAz_RAD
        self.telRot_RAD = telRot_RAD
        self.domAlt_RAD = domAlt_RAD
        self.domAz_RAD  = domAz_RAD
        self.mountedFilters   = list(mountedFilters)
        self.unmountedFilters = list(unmountedFilters)

        return

    def set(self, newState):

        self.time       = newState.time
        self.ra_RAD     = newState.ra_RAD
        self.dec_RAD    = newState.dec_RAD
        self.ang_RAD    = newState.ang_RAD
        self.filter     = newState.filter
        self.tracking   = newState.tracking
        self.alt_RAD    = newState.alt_RAD
        self.az_RAD     = newState.az_RAD
        self.pa_RAD     = newState.pa_RAD
        self.rot_RAD    = newState.rot_RAD

        self.telAlt_RAD = newState.telAlt_RAD
        self.telAz_RAD  = newState.telAz_RAD
        self.telRot_RAD = newState.telRot_RAD
        self.domAlt_RAD = newState.domAlt_RAD
        self.domAz_RAD  = newState.domAz_RAD
        self.mountedFilters   = list(newState.mountedFilters)
        self.unmountedFilters = list(newState.unmountedFilters)

        return

#####################################################################
class ObservatoryModel(object):

    def __init__(self, log):

        self.log = log

        siteConf, pairs  = readConfFile("../conf/system/site.conf")
        latitude_RAD   = eval(str(siteConf["latitude"]))*DEG2RAD
        longitude_RAD  = eval(str(siteConf["longitude"]))*DEG2RAD
        height         = eval(str(siteConf["height"]))*DEG2RAD
        self.location  = ObservatoryLocation(latitude_RAD, longitude_RAD, height)

        observatoryConf, pairs = readConfFile("../conf/system/observatoryModel.conf")
    	self.configure(observatoryConf)

        self.parkState = ObservatoryState()
        self.parkState.filter     = self.park_Filter
        self.parkState.tracking   = False
        self.parkState.alt_RAD    = self.park_TelAlt_RAD
        self.parkState.az_RAD     = self.park_TelAz_RAD
        self.parkState.rot_RAD    = self.park_TelRot_RAD
        self.parkState.telAlt_RAD = self.park_TelAlt_RAD
        self.parkState.telAz_RAD  = self.park_TelAz_RAD
        self.parkState.telRot_RAD = self.park_TelRot_RAD
        self.parkState.domAlt_RAD = self.park_DomAlt_RAD
        self.parkState.domAz_RAD  = self.park_DomAz_RAD
        self.parkState.mountedFilters   = list(self.Filter_MountedList)
        self.parkState.unmountedFilters = list(self.Filter_UnmountedList)

        self.currentState = ObservatoryState()
        self.reset()

        return

    def __str__(self):
        return self.currentState.__str__()

    def configure(self, observatoryConf):

        self.TelAlt_MinPos_RAD    = eval(str(observatoryConf["TelAlt_MinPos"]))*DEG2RAD
        self.TelAlt_MaxPos_RAD    = eval(str(observatoryConf["TelAlt_MaxPos"]))*DEG2RAD
        self.TelAz_MinPos_RAD     = eval(str(observatoryConf["TelAz_MinPos"]))*DEG2RAD
        self.TelAz_MaxPos_RAD     = eval(str(observatoryConf["TelAz_MaxPos"]))*DEG2RAD
        self.TelRot_MinPos_RAD    = eval(str(observatoryConf["TelRot_MinPos"]))*DEG2RAD
        self.TelRot_MaxPos_RAD    = eval(str(observatoryConf["TelRot_MaxPos"]))*DEG2RAD
        self.TelRot_FilterPos_RAD = eval(str(observatoryConf["TelRot_FilterPos"]))*DEG2RAD

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MinPos_RAD=%.3f"    % (self.TelAlt_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxPos_RAD=%.3f"    % (self.TelAlt_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MinPos_RAD=%.3f"     % (self.TelAz_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxPos_RAD=%.3f"     % (self.TelAz_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MinPos_RAD=%.3f"    % (self.TelRot_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MaxPos_RAD=%.3f"    % (self.TelRot_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_FilterPos_RAD=%.3f" % (self.TelRot_FilterPos_RAD))

        self.Rotator_FollowSky   = eval(str(observatoryConf["Rotator_FollowSky"]))
        self.Rotator_ResumeAngle = eval(str(observatoryConf["Rotator_ResumeAngleAfterFilterChange"]))

        self.log.log(INFOX, "ObservatoryModel: configure Rotator_FollowSky=%s"   % (self.Rotator_FollowSky))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_ResumeAngle=%s" % (self.Rotator_ResumeAngle))

        self.Filter_MountedList = observatoryConf["Filter_Mounted"]
    	if observatoryConf.has_key("Filter_Removable"):
            self.Filter_RemovableList = observatoryConf["Filter_Removable"]
            if (not isinstance(self.Filter_RemovableList,list)):
                self.Filter_RemovableList = [self.Filter_RemovableList]
    	else:
	        self.Filter_RemovableList = []

        if observatoryConf.has_key("Filter_Unmounted"):
            self.Filter_UnmountedList = observatoryConf["Filter_Unmounted"]
    	    if (not isinstance(self.Filter_UnmountedList,list)):
                self.Filter_UnmountedList = [self.Filter_UnmountedList]
        else:
            self.Filter_UnmountedList = []

        self.log.log(INFOX, "ObservatoryModel: configure Filter_MountedList=%s"   % (self.Filter_MountedList))
        self.log.log(INFOX, "ObservatoryModel: configure Filter_RemovableList=%s" % (self.Filter_RemovableList))
        self.log.log(INFOX, "ObservatoryModel: configure Filter_UnmountedList=%s" % (self.Filter_UnmountedList))

        self.TelAlt_MaxSpeed_RAD = eval(str(observatoryConf["TelAlt_MaxSpeed"]))*DEG2RAD
        self.TelAlt_Accel_RAD    = eval(str(observatoryConf["TelAlt_Accel"]))*DEG2RAD
        self.TelAlt_Decel_RAD    = eval(str(observatoryConf["TelAlt_Decel"]))*DEG2RAD
        self.TelAz_MaxSpeed_RAD  = eval(str(observatoryConf["TelAz_MaxSpeed"]))*DEG2RAD
        self.TelAz_Accel_RAD     = eval(str(observatoryConf["TelAz_Accel"]))*DEG2RAD
        self.TelAz_Decel_RAD     = eval(str(observatoryConf["TelAz_Decel"]))*DEG2RAD
        self.TelRot_MaxSpeed_RAD = eval(str(observatoryConf["TelRot_MaxSpeed"]))*DEG2RAD
        self.TelRot_Accel_RAD    = eval(str(observatoryConf["TelRot_Accel"]))*DEG2RAD
        self.TelRot_Decel_RAD    = eval(str(observatoryConf["TelRot_Decel"]))*DEG2RAD
        self.DomAlt_MaxSpeed_RAD = eval(str(observatoryConf["DomAlt_MaxSpeed"]))*DEG2RAD
        self.DomAlt_Accel_RAD    = eval(str(observatoryConf["DomAlt_Accel"]))*DEG2RAD
        self.DomAlt_Decel_RAD    = eval(str(observatoryConf["DomAlt_Decel"]))*DEG2RAD
        self.DomAz_MaxSpeed_RAD  = eval(str(observatoryConf["DomAz_MaxSpeed"]))*DEG2RAD
        self.DomAz_Accel_RAD     = eval(str(observatoryConf["DomAz_Accel"]))*DEG2RAD
        self.DomAz_Decel_RAD     = eval(str(observatoryConf["DomAz_Decel"]))*DEG2RAD

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxSpeed_RAD=%.3f" % (self.TelAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Accel_RAD=%.3f"    % (self.TelAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Decel_RAD=%.3f"    % (self.TelAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxSpeed_RAD=%.3f"  % (self.TelAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Accel_RAD=%.3f"     % (self.TelAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Decel_RAD=%.3f"     % (self.TelAz_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MaxSpeed_RAD=%.3f" % (self.TelRot_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Accel_RAD=%.3f"    % (self.TelRot_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Decel_RAD=%.3f"    % (self.TelRot_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_MaxSpeed_RAD=%.3f" % (self.DomAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Accel_RAD=%.3f"    % (self.DomAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Decel_RAD=%.3f"    % (self.DomAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_MaxSpeed_RAD=%.3f"  % (self.DomAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Accel_RAD=%.3f"     % (self.DomAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Decel_RAD=%.3f"     % (self.DomAz_Decel_RAD))

        self.Filter_ChangeTime = eval(str(observatoryConf["Filter_ChangeTime"]))
        self.Mount_SettleTime  = eval(str(observatoryConf["Mount_SettleTime"]))
        self.DomAz_SettleTime  = eval(str(observatoryConf["DomAz_SettleTime"]))
        self.ReadoutTime       = eval(str(observatoryConf["ReadoutTime"]))
        self.ShutterTime       = eval(str(observatoryConf["ShutterTime"]))

        self.log.log(INFOX, "ObservatoryModel: configure Filter_ChangeTime=%.1f" % (self.Filter_ChangeTime))
        self.log.log(INFOX, "ObservatoryModel: configure Mount_SettleTime=%.1f"  % (self.Mount_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_SettleTime=%.1f"  % (self.DomAz_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure ReadoutTime=%.1f"       % (self.ReadoutTime))
        self.log.log(INFOX, "ObservatoryModel: configure ShutterTime=%.1f"       % (self.ShutterTime))

        self.OpticsOL_Slope    = eval(str(observatoryConf["OpticsOL_Slope"]))
        self.OpticsCL_Delay    = eval(str(observatoryConf["OpticsCL_Delay"]))
        self.OpticsCL_AltLimit = eval(str(observatoryConf["OpticsCL_AltLimit"]))

        self.log.log(INFOX, "ObservatoryModel: configure OpticsOL_Slope=%.3f"  % (self.OpticsOL_Slope))
        self.log.log(INFOX, "ObservatoryModel: configure OpticsCL_Delay=%s"    % (self.OpticsCL_Delay))
        self.log.log(INFOX, "ObservatoryModel: configure OpticsCL_AltLimit=%s" % (self.OpticsCL_AltLimit))

        self.activities = ["TelAlt",
                           "TelAz",
                           "TelRot",
                           "DomAlt",
                           "DomAz",
                           "Filter",
                           "MountSettle",
                           "DomAzSettle",
                           "Readout",
                           "OpticsOL",
                           "OpticsCL",
                           "Exposures"]

        self.prerequisites = {}
        for activity in self.activities:
            key = "prereq_" + activity
            self.prerequisites[activity] = eval(observatoryConf[key])
            self.log.log(INFOX, "ObservatoryModel: configure prerequisites[%s]=%s"  % (activity, self.prerequisites[activity]))

        self.park_TelAlt_RAD = eval(str(observatoryConf["park_TelAlt"]))*DEG2RAD
        self.park_TelAz_RAD  = eval(str(observatoryConf["park_TelAz"]))*DEG2RAD
        self.park_TelRot_RAD = eval(str(observatoryConf["park_TelRot"]))*DEG2RAD
        self.park_DomAlt_RAD = eval(str(observatoryConf["park_DomAlt"]))*DEG2RAD
        self.park_DomAz_RAD  = eval(str(observatoryConf["park_DomAz"]))*DEG2RAD
        self.park_Filter     = str(observatoryConf["park_Filter"])

        self.log.log(INFOX, "ObservatoryModel: configure park_TelAlt_RAD=%.3f" % (self.park_TelAlt_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_TelAz_RAD=%.3f"  % (self.park_TelAz_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_TelRot_RAD=%.3f" % (self.park_TelRot_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_DomAlt_RAD=%.3f" % (self.park_DomAlt_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_DomAz_RAD=%.3f"  % (self.park_DomAz_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure park_Filter=%s"       % (self.park_Filter))

        return

    def reset(self):

        self.setState(self.parkState)

        return

    def setState(self, newState):

        self.currentState.set(newState)

        return

    def slewAltAzRot(self, time, alt, az, rot):
        return

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
                                                                                            
        UT_day   = 57388 + time/86400.0

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
        pa_RAD            = pal.pa(HA_RAD, dec_RAD, self.location.latitude_RAD)
        ra_RAD            = LST_RAD - HA_RAD

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
        HA_RAD  = LST_RAD - ra_RAD

        (az_RAD, alt_RAD) = pal.de2h(HA_RAD, dec_RAD, self.location.latitude_RAD)
        pa_RAD            = pal.pa(HA_RAD, dec_RAD, self.location.latitude_RAD)

        return (alt_RAD, az_RAD, pa_RAD)

    def startTracking(self, time):
        if not self.currentState.tracking:
            self.updateState(time)
            self.currentState.tracking = True
        return

    def stopTracking(self, time):
        if self.currentState.tracking:
            self.updateState(time)
            self.currentState.tracking = False
        return

    def updateState(self, time):

        if self.currentState.tracking:
            (alt_RAD, az_RAD, pa_RAD) = self.RaDec2AltAzPa(time,
                                                            self.currentState.ra_RAD,
                                                            self.currentState.dec_RAD)
            az_RAD = divmod(az_RAD, TWOPI)[1]
            pa_RAD = divmod(pa_RAD, TWOPI)[1]
            rot_RAD = pa_RAD + self.currentState.ang_RAD
                                                                                                    
            self.currentState.time    = time
            self.currentState.alt_RAD = alt_RAD
            self.currentState.az_RAD  = az_RAD
            self.currentState.pa_RAD  = pa_RAD
            self.currentState.rot_RAD = rot_RAD

            self.currentState.telAlt_RAD = alt_RAD
            self.currentState.telAz_RAD  = az_RAD
            self.currentState.telRot_RAD = rot_RAD
            self.currentState.domAlt_RAD = alt_RAD
            self.currentState.domAz_RAD  = az_RAD
        else:
            (ra_RAD, dec_RAD, pa_RAD) = self.AltAz2RaDecPa(time,
                                                            self.currentState.alt_RAD,
                                                            self.currentState.az_RAD)
            pa_RAD = divmod(pa_RAD, TWOPI)[1]
            self.currentState.time    = time
            self.currentState.ra_RAD  = ra_RAD
            self.currentState.dec_RAD = dec_RAD
            self.currentState.ang_RAD = self.currentState.rot_RAD - pa_RAD
        return

