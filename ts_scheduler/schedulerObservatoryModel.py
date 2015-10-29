from schedulerDefinitions import *

class ObservatoryState(object):

    def __init__(self,
                    time       = 0.0,
                    telAlt_RAD = 1.553343,
                    telAz_RAD  = 0.0,
                    telRot_RAD = 0.0,
                    domAlt_RAD = 1.553343,
                    domAz_RAD  = 0.0,
                    filter     = 'r',
                    tracking   = False,
                    ra_RAD     = 0.0,
                    dec_RAD    = 0.0,
                    ang_RAD    = 0.0,
                    alt_RAD    = 1.553343,
                    az_RAD     = 0.0,
                    pa_RAD     = 0.0,
                    mountedFilters   = ['g','r','i','z','y'],
                    unmountedFilters = ['u']):

        self.time       = time
        self.telAlt_RAD = telAlt_RAD
        self.telAz_RAD  = telAz_RAD
        self.telRot_RAD = telRot_RAD
        self.domAlt_RAD = domAlt_RAD
        self.domAz_RAD  = domAz_RAD
        self.filter     = filter
        self.tracking   = tracking
        self.ra_RAD     = ra_RAD
        self.dec_RAD    = dec_RAD
        self.ang_RAD    = ang_RAD
        self.alt_RAD    = alt_RAD
        self.pa_RAD     = pa_RAD
        self.mountedFilters   = mountedFilters
        self.unmountedFilters = unmountedFilters

        return

    def update(self, newState):

        self.time       = newState.time
        self.telAlt_RAD = newState.telAlt_RAD
        self.telAz_RAD  = newState.telAz_RAD
        self.telRot_RAD = newState.telRot_RAD
        self.domAlt_RAD = newState.domAlt_RAD
        self.domAz_RAD  = newState.domAz_RAD
        self.filter     = newState.filter
        self.tracking   = newState.tracking
        self.ra_RAD     = newState.ra_RAD
        self.dec_RAD    = newState.dec_RAD
        self.ang_RAD    = newState.ang_RAD
        self.alt_RAD    = newState.alt_RAD
        self.pa_RAD     = newState.pa_RAD
        self.mountedFilters   = list(newState.mountedFilters)
        self.unmountedFilters = list(newState.unmountedFilters)

        return

class ObservatoryModel(object):

    def __init__(self, log):

        self.log = log

        observatoryConf, pairs = readConfFile("../conf/system/observatoryModel.conf")
    	self.configure(observatoryConf)

        self.currentState = ObservatoryState()

        return

    def configure(self, observatoryConf):

        self.TelAlt_MinPos_RAD     = eval(str(observatoryConf["TelAlt_MinPos"]))*DEG2RAD
        self.TelAlt_MaxPos_RAD     = eval(str(observatoryConf["TelAlt_MaxPos"]))*DEG2RAD
        self.TelAz_MinPos_RAD      = eval(str(observatoryConf["TelAz_MinPos"]))*DEG2RAD
        self.TelAz_MaxPos_RAD      = eval(str(observatoryConf["TelAz_MaxPos"]))*DEG2RAD
        self.Rotator_MinPos_RAD    = eval(str(observatoryConf["Rotator_MinPos"]))*DEG2RAD
        self.Rotator_MaxPos_RAD    = eval(str(observatoryConf["Rotator_MaxPos"]))*DEG2RAD
        self.Rotator_FilterPos_RAD = eval(str(observatoryConf["Rotator_FilterPos"]))*DEG2RAD

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MinPos_RAD=%.3f"      % (self.TelAlt_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxPos_RAD=%.3f"      % (self.TelAlt_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MinPos_RAD=%.3f"       % (self.TelAz_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxPos_RAD=%.3f"       % (self.TelAz_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_MinPos_RAD=%.3f"     % (self.Rotator_MinPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_MaxPos_RAD=%.3f"     % (self.Rotator_MaxPos_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_FilterPos_RAD=%.3f"  % (self.Rotator_FilterPos_RAD))

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

        self.TelAlt_MaxSpeed_RAD  = eval(str(observatoryConf["TelAlt_MaxSpeed"]))*DEG2RAD
        self.TelAlt_Accel_RAD     = eval(str(observatoryConf["TelAlt_Accel"]))*DEG2RAD
        self.TelAlt_Decel_RAD     = eval(str(observatoryConf["TelAlt_Decel"]))*DEG2RAD
        self.TelAz_MaxSpeed_RAD   = eval(str(observatoryConf["TelAz_MaxSpeed"]))*DEG2RAD
        self.TelAz_Accel_RAD      = eval(str(observatoryConf["TelAz_Accel"]))*DEG2RAD
        self.TelAz_Decel_RAD      = eval(str(observatoryConf["TelAz_Decel"]))*DEG2RAD
        self.Rotator_MaxSpeed_RAD = eval(str(observatoryConf["Rotator_MaxSpeed"]))*DEG2RAD
        self.Rotator_Accel_RAD    = eval(str(observatoryConf["Rotator_Accel"]))*DEG2RAD
        self.Rotator_Decel_RAD    = eval(str(observatoryConf["Rotator_Decel"]))*DEG2RAD
        self.DomAlt_MaxSpeed_RAD  = eval(str(observatoryConf["DomAlt_MaxSpeed"]))*DEG2RAD
        self.DomAlt_Accel_RAD     = eval(str(observatoryConf["DomAlt_Accel"]))*DEG2RAD
        self.DomAlt_Decel_RAD     = eval(str(observatoryConf["DomAlt_Decel"]))*DEG2RAD
        self.DomAz_MaxSpeed_RAD   = eval(str(observatoryConf["DomAz_MaxSpeed"]))*DEG2RAD
        self.DomAz_Accel_RAD      = eval(str(observatoryConf["DomAz_Accel"]))*DEG2RAD
        self.DomAz_Decel_RAD      = eval(str(observatoryConf["DomAz_Decel"]))*DEG2RAD

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxSpeed_RAD=%.3f"  % (self.TelAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Accel_RAD=%.3f"     % (self.TelAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Decel_RAD=%.3f"     % (self.TelAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxSpeed_RAD=%.3f"   % (self.TelAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Accel_RAD=%.3f"      % (self.TelAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Decel_RAD=%.3f"      % (self.TelAz_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_MaxSpeed_RAD=%.3f" % (self.Rotator_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_Accel_RAD=%.3f"    % (self.Rotator_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_Decel_RAD=%.3f"    % (self.Rotator_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_MaxSpeed_RAD=%.3f"  % (self.DomAlt_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Accel_RAD=%.3f"     % (self.DomAlt_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Decel_RAD=%.3f"     % (self.DomAlt_Decel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_MaxSpeed_RAD=%.3f"   % (self.DomAz_MaxSpeed_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Accel_RAD=%.3f"      % (self.DomAz_Accel_RAD))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Decel_RAD=%.3f"      % (self.DomAz_Decel_RAD))

        self.Filter_ChangeTime = eval(str(observatoryConf["Filter_ChangeTime"]))
        self.Mount_SettleTime  = eval(str(observatoryConf["Mount_SettleTime"]))
        self.DomAz_SettleTime  = eval(str(observatoryConf["DomAz_SettleTime"]))
        self.ReadoutTime       = eval(str(observatoryConf["ReadoutTime"]))

        self.log.log(INFOX, "ObservatoryModel: configure Filter_ChangeTime=%.1f" % (self.Filter_ChangeTime))
        self.log.log(INFOX, "ObservatoryModel: configure Mount_SettleTime=%.1f"  % (self.Mount_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_SettleTime=%.1f"  % (self.DomAz_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure ReadoutTime=%.1f"       % (self.ReadoutTime))

        self.TelOpticsOL_Slope    = eval(str(observatoryConf["TelOpticsOL_Slope"]))
        self.TelOpticsCL_Delay    = eval(str(observatoryConf["TelOpticsCL_Delay"]))
        self.TelOpticsCL_AltLimit = eval(str(observatoryConf["TelOpticsCL_AltLimit"]))

        self.log.log(INFOX, "ObservatoryModel: configure TelOpticsOL_Slope=%.3f"  % (self.TelOpticsOL_Slope))
        self.log.log(INFOX, "ObservatoryModel: configure TelOpticsCL_Delay=%s"    % (self.TelOpticsCL_Delay))
        self.log.log(INFOX, "ObservatoryModel: configure TelOpticsCL_AltLimit=%s" % (self.TelOpticsCL_AltLimit))

        self.activities = ["TelAlt",
                           "TelAz",
                           "Rotator",
                           "DomAlt",
                           "DomAz",
                           "Filter",
                           "MountSettle",
                           "DomAzSettle",
                           "Readout",
                           "TelOpticsOL",
                           "TelOpticsCL",
                           "Exposures"]

        self.prerequisites = {}
        for activity in self.activities:
            key = "prereq_" + activity
            self.prerequisites[activity] = eval(observatoryConf[key])
            self.log.log(INFOX, "ObservatoryModel: configure prerequisites[%s]=%s"  % (activity, self.prerequisites[activity]))

        return

    def updateState(self, newState):

        self.currentState.update(newState)

        return

    def estimateSlewTime(self):
        return

