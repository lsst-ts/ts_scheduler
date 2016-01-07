import math
import re

import palpy as pal

from schedulerDefinitions import TWOPI, RAD2DEG, DEG2RAD, INFOX

#####################################################################
class ObservatoryLocation(object):

    def __init__(self,
                 latitude_rad=0.0,
                 longitude_rad=0.0,
                 height=0.0):
        # meters
        self.Height = height

        # radians
        self.latitude_rad = latitude_rad
        self.longitude_rad = longitude_rad

#####################################################################
class ObservatoryPosition(object):

    def __init__(self,
                 time=0.0,
                 ra_rad=0.0,
                 dec_rad=0.0,
                 ang_rad=0.0,
                 filter='r',
                 tracking=False,
                 alt_rad=1.5,
                 az_rad=0.0,
                 pa_rad=0.0,
                 rot_rad=0.0):

        self.time = time
        self.ra_rad = ra_rad
        self.dec_rad = dec_rad
        self.ang_rad = ang_rad
        self.filter = filter
        self.tracking = tracking
        self.alt_rad = alt_rad
        self.az_rad = az_rad
        self.pa_rad = pa_rad
        self.rot_rad = rot_rad

    def __str__(self):
        return ("t=%.1f ra=%.3f dec=%.3f ang=%.3f filter=%s track=%s alt=%.3f az=%.3f rot=%.3f" %
                (self.time, self.ra_rad * RAD2DEG, self.dec_rad * RAD2DEG, self.ang_rad * RAD2DEG,
                 self.filter, self.tracking, self.alt_rad * RAD2DEG, self.az_rad * RAD2DEG,
                 self.rot_rad * RAD2DEG))

#####################################################################
class ObservatoryState(ObservatoryPosition):

    def __init__(self,
                 time=0.0,
                 ra_rad=0.0,
                 dec_rad=0.0,
                 ang_rad=0.0,
                 filter='r',
                 tracking=False,
                 alt_rad=1.5,
                 az_rad=0.0,
                 pa_rad=0.0,
                 rot_rad=0.0,
                 telalt_rad=1.5,
                 telaz_rad=0.0,
                 telrot_rad=0.0,
                 domalt_rad=1.5,
                 domaz_rad=0.0,
                 mountedfilters=['g', 'r', 'i', 'z', 'y'],
                 unmountedfilters=['u']):

        super(ObservatoryState, self).__init__(time,
                                               ra_rad,
                                               dec_rad,
                                               ang_rad,
                                               filter,
                                               tracking,
                                               alt_rad,
                                               az_rad,
                                               pa_rad,
                                               rot_rad)

        self.telalt_rad = telalt_rad
        self.telaz_rad = telaz_rad
        self.telrot_rad = telrot_rad
        self.domalt_rad = domalt_rad
        self.domaz_rad = domaz_rad
        self.mountedfilters = list(mountedfilters)
        self.unmountedfilters = list(unmountedfilters)

    def set(self, newstate):

        self.time = newstate.time
        self.ra_rad = newstate.ra_rad
        self.dec_rad = newstate.dec_rad
        self.ang_rad = newstate.ang_rad
        self.filter = newstate.filter
        self.tracking = newstate.tracking
        self.alt_rad = newstate.alt_rad
        self.az_rad = newstate.az_rad
        self.pa_rad = newstate.pa_rad
        self.rot_rad = newstate.rot_rad

        self.telalt_rad = newstate.telalt_rad
        self.telaz_rad = newstate.telaz_rad
        self.telrot_rad = newstate.telrot_rad
        self.domalt_rad = newstate.domalt_rad
        self.domaz_rad = newstate.domaz_rad
        self.mountedfilters = list(newstate.mountedfilters)
        self.unmountedfilters = list(newstate.unmountedfilters)

    def set_position(self, newposition):

        self.time = newposition.time
        self.ra_rad = newposition.ra_rad
        self.dec_rad = newposition.dec_rad
        self.ang_rad = newposition.ang_rad
        self.filter = newposition.filter
        self.tracking = newposition.tracking
        self.alt_rad = newposition.alt_rad
        self.az_rad = newposition.az_rad
        self.pa_rad = newposition.pa_rad
        self.rot_rad = newposition.rot_rad

        self.telalt_rad = newposition.alt_rad
        self.telaz_rad = newposition.az_rad
        self.telrot_rad = newposition.rot_rad
        self.domalt_rad = newposition.alt_rad
        self.domaz_rad = newposition.az_rad

#####################################################################
class ObservatoryModel(object):

    def __init__(self, log):

        self.log = log

        self.location = ObservatoryLocation()
        self.parkState = ObservatoryState()
        self.currentState = ObservatoryState()

    def __str__(self):
        return self.currentState.__str__()

    def configure(self, observatory_confdict):

        self.location.latitude_rad = math.radians(observatory_confdict["obs_site"]["latitude"])
        self.location.longitude_rad = math.radians(observatory_confdict["obs_site"]["longitude"])
        self.location.height = observatory_confdict["obs_site"]["height"]

        self.TelAlt_MinPos_rad = math.radians(observatory_confdict["telescope"]["altitude_minpos"])
        self.TelAlt_MaxPos_rad = math.radians(observatory_confdict["telescope"]["altitude_maxpos"])
        self.TelAz_MinPos_rad = math.radians(observatory_confdict["telescope"]["azimuth_minpos"])
        self.TelAz_MaxPos_rad = math.radians(observatory_confdict["telescope"]["azimuth_maxpos"])
        self.TelRot_MinPos_rad = math.radians(observatory_confdict["rotator"]["minpos"])
        self.TelRot_MaxPos_rad = math.radians(observatory_confdict["rotator"]["maxpos"])
        self.TelRot_FilterPos_rad = math.radians(observatory_confdict["rotator"]["filter_pos"])

        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MinPos_rad=%.3f" % (self.TelAlt_MinPos_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_MaxPos_rad=%.3f" % (self.TelAlt_MaxPos_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MinPos_rad=%.3f" % (self.TelAz_MinPos_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxPos_rad=%.3f" % (self.TelAz_MaxPos_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MinPos_rad=%.3f" % (self.TelRot_MinPos_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_MaxPos_rad=%.3f" % (self.TelRot_MaxPos_rad))
        self.log.log(INFOX,
                     "ObservatoryModel: configure TelRot_FilterPos_rad=%.3f" % (self.TelRot_FilterPos_rad))

        self.Rotator_FollowSky = observatory_confdict["rotator"]["follow_sky"]
        self.Rotator_ResumeAngle = observatory_confdict["rotator"]["resume_angle"]

        self.log.log(INFOX, "ObservatoryModel: configure Rotator_FollowSky=%s" % (self.Rotator_FollowSky))
        self.log.log(INFOX, "ObservatoryModel: configure Rotator_ResumeAngle=%s" % (self.Rotator_ResumeAngle))

        self.Filter_MountedList = observatory_confdict["camera"]["filter_mounted"]
        self.Filter_RemovableList = observatory_confdict["camera"]["filter_removable"]
        self.Filter_UnmountedList = observatory_confdict["camera"]["filter_unmounted"]

        self.log.log(INFOX, "ObservatoryModel: configure Filter_MountedList=%s" % (self.Filter_MountedList))
        self.log.log(INFOX,
                     "ObservatoryModel: configure Filter_RemovableList=%s" % (self.Filter_RemovableList))
        self.log.log(INFOX,
                     "ObservatoryModel: configure Filter_UnmountedList=%s" % (self.Filter_UnmountedList))

        self.TelAlt_MaxSpeed_rad = math.radians(observatory_confdict["telescope"]["altitude_maxspeed"])
        self.TelAlt_Accel_rad = math.radians(observatory_confdict["telescope"]["altitude_accel"])
        self.TelAlt_Decel_rad = math.radians(observatory_confdict["telescope"]["altitude_decel"])
        self.TelAz_MaxSpeed_rad = math.radians(observatory_confdict["telescope"]["azimuth_maxspeed"])
        self.TelAz_Accel_rad = math.radians(observatory_confdict["telescope"]["azimuth_accel"])
        self.TelAz_Decel_rad = math.radians(observatory_confdict["telescope"]["azimuth_decel"])
        self.TelRot_MaxSpeed_rad = math.radians(observatory_confdict["rotator"]["maxspeed"])
        self.TelRot_Accel_rad = math.radians(observatory_confdict["rotator"]["accel"])
        self.TelRot_Decel_rad = math.radians(observatory_confdict["rotator"]["decel"])
        self.DomAlt_MaxSpeed_rad = math.radians(observatory_confdict["dome"]["altitude_maxspeed"])
        self.DomAlt_Accel_rad = math.radians(observatory_confdict["dome"]["altitude_accel"])
        self.DomAlt_Decel_rad = math.radians(observatory_confdict["dome"]["altitude_decel"])
        self.DomAz_MaxSpeed_rad = math.radians(observatory_confdict["dome"]["azimuth_maxspeed"])
        self.DomAz_Accel_rad = math.radians(observatory_confdict["dome"]["azimuth_accel"])
        self.DomAz_Decel_rad = math.radians(observatory_confdict["dome"]["azimuth_decel"])

        self.log.log(INFOX,
                     "ObservatoryModel: configure TelAlt_MaxSpeed_rad=%.3f" % (self.TelAlt_MaxSpeed_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Accel_rad=%.3f" % (self.TelAlt_Accel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAlt_Decel_rad=%.3f" % (self.TelAlt_Decel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_MaxSpeed_rad=%.3f" % (self.TelAz_MaxSpeed_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Accel_rad=%.3f" % (self.TelAz_Accel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelAz_Decel_rad=%.3f" % (self.TelAz_Decel_rad))
        self.log.log(INFOX,
                     "ObservatoryModel: configure TelRot_MaxSpeed_rad=%.3f" % (self.TelRot_MaxSpeed_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Accel_rad=%.3f" % (self.TelRot_Accel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure TelRot_Decel_rad=%.3f" % (self.TelRot_Decel_rad))
        self.log.log(INFOX,
                     "ObservatoryModel: configure DomAlt_MaxSpeed_rad=%.3f" % (self.DomAlt_MaxSpeed_rad))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Accel_rad=%.3f" % (self.DomAlt_Accel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure DomAlt_Decel_rad=%.3f" % (self.DomAlt_Decel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_MaxSpeed_rad=%.3f" % (self.DomAz_MaxSpeed_rad))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Accel_rad=%.3f" % (self.DomAz_Accel_rad))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_Decel_rad=%.3f" % (self.DomAz_Decel_rad))

        self.Filter_ChangeTime = observatory_confdict["camera"]["filter_change_time"]
        self.Mount_SettleTime = observatory_confdict["telescope"]["settle_time"]
        self.DomAz_SettleTime = observatory_confdict["dome"]["settle_time"]
        self.ReadoutTime = observatory_confdict["camera"]["readout_time"]
        self.ShutterTime = observatory_confdict["camera"]["shutter_time"]

        self.log.log(INFOX, "ObservatoryModel: configure Filter_ChangeTime=%.1f" % (self.Filter_ChangeTime))
        self.log.log(INFOX, "ObservatoryModel: configure Mount_SettleTime=%.1f" % (self.Mount_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure DomAz_SettleTime=%.1f" % (self.DomAz_SettleTime))
        self.log.log(INFOX, "ObservatoryModel: configure ReadoutTime=%.1f" % (self.ReadoutTime))
        self.log.log(INFOX, "ObservatoryModel: configure ShutterTime=%.1f" % (self.ShutterTime))

        # Shouldn't these be converted to radians?
        self.OpticsOL_Slope = observatory_confdict["slew"]["tel_optics_ol_slope"]
        self.OpticsCL_Delay = observatory_confdict["slew"]["tel_optics_cl_delay"]
        self.OpticsCL_AltLimit = observatory_confdict["slew"]["tel_optics_cl_alt_limit"]

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
            self.prerequisites[activity] = observatory_confdict["slew"][key]
            self.log.log(INFOX,
                         "ObservatoryModel: configure prerequisites[%s]=%s" %
                         (activity, self.prerequisites[activity]))

        self.parkState.alt_rad = math.radians(observatory_confdict["park"]["telescope_altitude"])
        self.parkState.az_rad = math.radians(observatory_confdict["park"]["telescope_azimuth"])
        self.parkState.rot_rad = math.radians(observatory_confdict["park"]["telescope_rotator"])
        self.parkState.telalt_rad = math.radians(observatory_confdict["park"]["telescope_altitude"])
        self.parkState.telaz_rad = math.radians(observatory_confdict["park"]["telescope_azimuth"])
        self.parkState.telrot_rad = math.radians(observatory_confdict["park"]["telescope_rotator"])
        self.parkState.domalt_rad = math.radians(observatory_confdict["park"]["dome_altitude"])
        self.parkState.domaz_rad = math.radians(observatory_confdict["park"]["dome_azimuth"])
        self.parkState.filter = observatory_confdict["park"]["filter_position"]
        self.parkState.mountedfilters = self.Filter_MountedList
        self.parkState.unmountedfilters = self.Filter_UnmountedList
        self.parkState.tracking = False

        self.log.log(INFOX, "ObservatoryModel: configure park_Telalt_rad=%.3f" % (self.parkState.telalt_rad))
        self.log.log(INFOX, "ObservatoryModel: configure park_Telaz_rad=%.3f" % (self.parkState.telaz_rad))
        self.log.log(INFOX, "ObservatoryModel: configure park_Telrot_rad=%.3f" % (self.parkState.telrot_rad))
        self.log.log(INFOX, "ObservatoryModel: configure park_Domalt_rad=%.3f" % (self.parkState.domalt_rad))
        self.log.log(INFOX, "ObservatoryModel: configure park_Domaz_rad=%.3f" % (self.parkState.domaz_rad))
        self.log.log(INFOX, "ObservatoryModel: configure park_Filter=%s" % (self.parkState.filter))

        self.reset()

    def reset(self):

        self.set_state(self.parkState)

    def set_state(self, newstate):

        self.currentState.set(newstate)

    def observe(self, topic_observation):
        return

    def slew_altazrot(self, time, alt, az, rot):

        targetposition = ObservatoryPosition()
        targetposition.time = time
        targetposition.tracking = False
        targetposition.alt_rad = alt * DEG2RAD
        targetposition.az_rad = az * DEG2RAD
        targetposition.rot_rad = rot * DEG2RAD

        self.currentState.set_position(targetposition)

    def estimate_slewtime(self):
        return

    def park(self):
        return

    def slew(self, target):
        return

    def date2lst(self, time):
        """
        Computes the Local Sidereal Time for the given TIME.
        inputs:
               TIME: Time in seconds since simulation reference (SIMEPOCH)
        output:
               LST:  Local Sidereal Time in radians.
        """

        ut_day = 57388 + time / 86400.0

        # LSST convention of West=negative, East=positive
        lst_rad = pal.gmst(ut_day) + self.location.longitude_rad

        return lst_rad

    def altaz2radecpa(self, time, alt_rad, az_rad):
        """
        Converts ALT, AZ coordinates into RA DEC for the given TIME.

        inputs:
               alt_rad: Altitude in radians [-90.0deg  90.0deg] 90deg=>zenith
               az_rad:  Azimuth in radians [  0.0deg 360.0deg] 0deg=>N 90deg=>E
               time:    Time in seconds since simulation reference (SIMEPOCH)
        output:
               (ra_rad, dec_rad)
               ra_rad:  Right Ascension in radians
               dec_rad: Declination in radians
        """
        lst_rad = self.date2lst(time)

        (ha_rad, dec_rad) = pal.dh2e(az_rad, alt_rad, self.location.latitude_rad)
        pa_rad = pal.pa(ha_rad, dec_rad, self.location.latitude_rad)
        ra_rad = lst_rad - ha_rad

        return (ra_rad, dec_rad, pa_rad)

    def radec2altazpa(self, time, ra_rad, dec_rad):
        """
        Converts ra_rad, dec_rad coordinates into alt_rad az_rad for given DATE.
        inputs:
               ra_rad:  Right Ascension in radians
               dec_rad: Declination in radians
               DATE: Time in seconds since simulation reference (SIMEPOCH)
        output:
               (alt_rad, az_rad, pa_rad, HA_HOU)
               alt_rad: Altitude in radians [-90.0  90.0] 90=>zenith
               az_rad:  Azimuth in radians [  0.0 360.0] 0=>N 90=>E
               pa_rad:  Parallactic Angle in radians
               HA_HOU:  Hour Angle in hours
        """
        lst_rad = self.date2lst(time)
        ha_rad = lst_rad - ra_rad

        (az_rad, alt_rad) = pal.de2h(ha_rad, dec_rad, self.location.latitude_rad)
        pa_rad = pal.pa(ha_rad, dec_rad, self.location.latitude_rad)

        return (alt_rad, az_rad, pa_rad)

    def start_tracking(self, time):
        if not self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = True

    def stop_tracking(self, time):
        if self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = False

    def update_state(self, time):

        if self.currentState.tracking:
            (alt_rad, az_rad, pa_rad) = self.radec2altazpa(time,
                                                           self.currentState.ra_rad,
                                                           self.currentState.dec_rad)
            az_rad = divmod(az_rad, TWOPI)[1]
            pa_rad = divmod(pa_rad, TWOPI)[1]
            rot_rad = pa_rad + self.currentState.ang_rad

            self.currentState.time = time
            self.currentState.alt_rad = alt_rad
            self.currentState.az_rad = az_rad
            self.currentState.pa_rad = pa_rad
            self.currentState.rot_rad = rot_rad

            self.currentState.telalt_rad = alt_rad
            self.currentState.telaz_rad = az_rad
            self.currentState.telrot_rad = rot_rad
            self.currentState.domalt_rad = alt_rad
            self.currentState.domaz_rad = az_rad
        else:
            (ra_rad, dec_rad, pa_rad) = self.altaz2radecpa(time,
                                                           self.currentState.alt_rad,
                                                           self.currentState.az_rad)
            pa_rad = divmod(pa_rad, TWOPI)[1]
            self.currentState.time = time
            self.currentState.ra_rad = ra_rad
            self.currentState.dec_rad = dec_rad
            self.currentState.ang_rad = self.currentState.rot_rad - pa_rad
