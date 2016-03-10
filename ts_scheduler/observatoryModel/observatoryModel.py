import math
import logging

import palpy as pal

from ts_scheduler.schedulerDefinitions import TWOPI, INFOX
from .observatoryLocation import ObservatoryLocation
from .observatoryPosition import ObservatoryPosition
from .observatoryState import ObservatoryState

class ObservatoryModel(object):

    def __init__(self):

        self.log = logging.getLogger("observatorModel.ObservatoryModel")

        self.location = ObservatoryLocation()
        self.parkState = ObservatoryState()
        self.currentState = ObservatoryState()
        self.targetPosition = ObservatoryPosition()

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

        self.activities = ["telalt",
                           "telaz",
                           "telrot",
                           "telsettle",
                           "telopticsopenloop",
                           "telopticsclosedloop",
                           "domalt",
                           "domaz",
                           "domazsettle",
                           "filter",
                           "readout",
                           "exposures"]

        self.prerequisites = {}
        for activity in self.activities:
            key = "prereq_" + activity
            self.prerequisites[activity] = observatory_confdict["slew"][key]
            self.log.log(INFOX,
                         "ObservatoryModel: configure prerequisites[%s]=%s" %
                         (activity, self.prerequisites[activity]))

        self.function_get_delay_for = {}
        self.delay_for = {}
        self.longest_prereq_for = {}
        for activity in self.activities:
            self.delay_for[activity] = 0.0
            self.longest_prereq_for[activity] = ""
            function_name = "get_delay_for_" + activity
            self.function_get_delay_for[activity] = getattr(self, function_name)

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

    def update_state(self, time):

        if (time < self.currentState.time):
            time = self.currentState.time

        if self.currentState.tracking:
            (alt_rad, az_rad, pa_rad) = self.radec2altazpa(time,
                                                           self.currentState.ra_rad,
                                                           self.currentState.dec_rad)
            az_rad = divmod(az_rad, TWOPI)[1]
            rot_rad = divmod(pa_rad - self.currentState.ang_rad, TWOPI)[1]

            targetposition = ObservatoryPosition()
            targetposition.time = time
            targetposition.tracking = True
            targetposition.alt_rad = alt_rad
            targetposition.az_rad = az_rad
            targetposition.pa_rad = pa_rad
            targetposition.rot_rad = rot_rad
            targetstate = self.get_closest_state(targetposition)

            self.currentState.time = targetstate.time
            self.currentState.alt_rad = targetstate.alt_rad
            self.currentState.az_rad = targetstate.az_rad
            self.currentState.pa_rad = targetstate.pa_rad
            self.currentState.rot_rad = targetstate.rot_rad

            self.currentState.telalt_rad = targetstate.telalt_rad
            self.currentState.telaz_rad = targetstate.telaz_rad
            self.currentState.telrot_rad = targetstate.telrot_rad
            self.currentState.domalt_rad = targetstate.domalt_rad
            self.currentState.domaz_rad = targetstate.domaz_rad
        else:
            (ra_rad, dec_rad, pa_rad) = self.altaz2radecpa(time,
                                                           self.currentState.alt_rad,
                                                           self.currentState.az_rad)
            self.currentState.time = time
            self.currentState.ra_rad = ra_rad
            self.currentState.dec_rad = dec_rad
            self.currentState.ang_rad = divmod(pa_rad - self.currentState.rot_rad, TWOPI)[1]
            self.currentState.pa_rad = pa_rad

    def slew_altazrot(self, time, alt_rad, az_rad, rot_rad):

        self.update_state(time)
        time = self.currentState.time

        targetposition = ObservatoryPosition()
        targetposition.time = time
        targetposition.tracking = False
        targetposition.alt_rad = alt_rad
        targetposition.az_rad = az_rad
        targetposition.rot_rad = rot_rad

        self.slew_to_position(targetposition)

    def slew_radecang(self, time, ra_rad, dec_rad, ang_rad):

        self.update_state(time)
        time = self.currentState.time

        (alt_rad, az_rad, pa_rad) = self.radec2altazpa(time, ra_rad, dec_rad)

        targetposition = ObservatoryPosition()
        targetposition.time = time
        targetposition.tracking = True
        targetposition.ra_rad = ra_rad
        targetposition.dec_rad = dec_rad
        targetposition.ang_rad = ang_rad
        targetposition.alt_rad = alt_rad
        targetposition.az_rad = az_rad
        targetposition.pa_rad = pa_rad
        targetposition.rot_rad = divmod(pa_rad - ang_rad, TWOPI)[1]

        self.slew_to_position(targetposition)

    def slew_to_position(self, targetposition):

        targetstate = self.get_closest_state(targetposition)
        slew_delay = self.get_slew_delay(targetstate, self.currentState)
        targetstate.time = targetstate.time + slew_delay
        self.currentState.set(targetstate)
        self.update_state(targetstate.time)

    def get_closest_state(self, targetposition):

        (telalt_rad, delta_telalt_rad) = self.get_closest_angle_distance(targetposition.alt_rad,
                                                                         self.currentState.telalt_rad,
                                                                         self.TelAlt_MinPos_rad,
                                                                         self.TelAlt_MaxPos_rad)
        (telaz_rad, delta_telaz_rad) = self.get_closest_angle_distance(targetposition.az_rad,
                                                                       self.currentState.telaz_rad,
                                                                       self.TelAz_MinPos_rad,
                                                                       self.TelAz_MaxPos_rad)

        # if the target rotator angle is unreachable
        # then sets an arbitrary value
        norm_rot_rad = divmod(targetposition.rot_rad - self.TelRot_MinPos_rad, TWOPI)[1] \
            + self.TelRot_MinPos_rad
        if (norm_rot_rad > self.TelRot_MaxPos_rad):
            targetposition.rot_rad = norm_rot_rad - math.pi
        (telrot_rad, delta_telrot_rad) = self.get_closest_angle_distance(targetposition.rot_rad,
                                                                         self.currentState.telrot_rad,
                                                                         self.TelRot_MinPos_rad,
                                                                         self.TelRot_MaxPos_rad)
        targetposition.ang_rad = targetposition.pa_rad - telrot_rad

        (domalt_rad, delta_domalt_rad) = self.get_closest_angle_distance(targetposition.alt_rad,
                                                                         self.currentState.domalt_rad,
                                                                         self.TelAlt_MinPos_rad,
                                                                         self.TelAlt_MaxPos_rad)
        (domaz_rad, delta_domaz_rad) = self.get_closest_angle_distance(targetposition.az_rad,
                                                                       self.currentState.domaz_rad)
        targetstate = ObservatoryState()
        targetstate.set_position(targetposition)
        targetstate.telalt_rad = telalt_rad
        targetstate.telaz_rad = telaz_rad
        targetstate.telrot_rad = telrot_rad
        targetstate.domalt_rad = domalt_rad
        targetstate.domaz_rad = domaz_rad

        return targetstate

    def get_closest_angle_distance(self, target_rad, current_abs_rad, min_abs_rad=None, max_abs_rad=None):

        # if there are wrap limits, normalizes the target angle
        if (min_abs_rad is not None):
            norm_target_rad = divmod(target_rad - min_abs_rad, TWOPI)[1] + min_abs_rad
            if (max_abs_rad is not None):
                # if the target angle is unreachable
                # then sets an arbitrary value
                if (norm_target_rad > max_abs_rad):
                    norm_target_rad = max(min_abs_rad, norm_target_rad - math.pi)
        else:
            norm_target_rad = target_rad

        # computes the distance clockwise
        distance_rad = divmod(norm_target_rad - current_abs_rad, TWOPI)[1]

        # take the counter-clockwise distance if shorter
        if (distance_rad > math.pi):
            distance_rad = distance_rad - TWOPI

        # if there are wrap limits
        if (min_abs_rad is not None and max_abs_rad is not None):
            # compute accumulated angle
            accum_abs_rad = current_abs_rad + distance_rad

            # if limits reached chose the other direction
            if (accum_abs_rad > max_abs_rad):
                distance_rad = distance_rad - TWOPI
            if (accum_abs_rad < min_abs_rad):
                distance_rad = distance_rad + TWOPI

        # compute final accumulated angle
        final_abs_rad = current_abs_rad + distance_rad

        return (final_abs_rad, distance_rad)

    def observe(self, topic_observation):
        return

    def compute_kinematic_delay(self, distance, maxspeed, accel, decel):

        d = abs(distance)

        vpeak = (2 * d / (1 / accel + 1 / decel)) ** 0.5
        if (vpeak <= maxspeed):
            delay = vpeak / accel + vpeak / decel
        else:
            d1 = 0.5 * (maxspeed * maxspeed) / accel
            d3 = 0.5 * (maxspeed * maxspeed) / decel
            d2 = d - d1 - d3

            t1 = maxspeed / accel
            t3 = maxspeed / decel
            t2 = d2 / maxspeed

            delay = t1 + t2 + t3
            vpeak = maxspeed

        return (delay, vpeak * cmp(distance, 0))

    def get_slew_delay(self, targetstate, initstate):

        slew_delay = self.get_delay_after("exposures", targetstate, initstate)

        return slew_delay

    def get_delay_after(self, activity, targetstate, initstate):

        activity_delay = self.function_get_delay_for[activity](targetstate, initstate)

        prereq_list = self.prerequisites[activity]

        longest_previous_delay = 0.0
        longest_prereq = ""
        for prereq in prereq_list:
            previous_delay = self.get_delay_after(prereq, targetstate, initstate)
            if (previous_delay > longest_previous_delay):
                longest_previous_delay = previous_delay
                longest_prereq = prereq
        self.longest_prereq_for[activity] = longest_prereq
        self.delay_for[activity] = activity_delay

        return activity_delay + longest_previous_delay

    def get_delay_for_telalt(self, targetstate, initstate):

        distance = targetstate.telalt_rad - initstate.telalt_rad
        maxspeed = self.TelAlt_MaxSpeed_rad
        accel = self.TelAlt_Accel_rad
        decel = self.TelAlt_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telalt_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telaz(self, targetstate, initstate):

        distance = targetstate.telaz_rad - initstate.telaz_rad
        maxspeed = self.TelAz_MaxSpeed_rad
        accel = self.TelAz_Accel_rad
        decel = self.TelAz_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telaz_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telrot(self, targetstate, initstate):

        distance = targetstate.telrot_rad - initstate.telrot_rad
        maxspeed = self.TelRot_MaxSpeed_rad
        accel = self.TelRot_Accel_rad
        decel = self.TelRot_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telrot_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telsettle(self, targetstate, initstate):

        distance = abs(targetstate.telalt_rad - initstate.telalt_rad) + \
            abs(targetstate.telaz_rad - initstate.telaz_rad)

        if (distance > 0):
            delay = self.Mount_SettleTime
        else:
            delay = 0

        return delay

    def get_delay_for_telopticsopenloop(self, targetstate, initstate):
        return 0.0

    def get_delay_for_telopticsclosedloop(self, targetstate, initstate):
        return 0.0

    def get_delay_for_domalt(self, targetstate, initstate):

        distance = targetstate.domalt_rad - initstate.domalt_rad
        maxspeed = self.DomAlt_MaxSpeed_rad
        accel = self.DomAlt_Accel_rad
        decel = self.DomAlt_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.domalt_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_domaz(self, targetstate, initstate):

        distance = targetstate.domaz_rad - initstate.domaz_rad
        maxspeed = self.DomAz_MaxSpeed_rad
        accel = self.DomAz_Accel_rad
        decel = self.DomAz_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.domaz_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_domazsettle(self, targetstate, initstate):

        distance = abs(targetstate.domaz_rad - initstate.domaz_rad)

        if (distance > 0):
            delay = self.DomAz_SettleTime
        else:
            delay = 0

        return delay

    def get_delay_for_filter(self, targetstate, initstate):
        return 0.0

    def get_delay_for_readout(self, targetstate, initstate):
        return 0.0

    def get_delay_for_exposures(self, targetstate, initstate):
        return 0.0

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
        ra_rad = divmod(lst_rad - ha_rad, TWOPI)[1]

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
        if (time < self.currentState.time):
            time = self.currentState.time
        if not self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = True

    def stop_tracking(self, time):
        if (time < self.currentState.time):
            time = self.currentState.time
        if self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = False
