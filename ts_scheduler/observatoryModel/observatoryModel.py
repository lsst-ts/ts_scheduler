import math
import logging

import palpy as pal

from ts_scheduler.setup import WORDY
from ts_scheduler.schedulerDefinitions import TWOPI
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.observatoryModel import ObservatoryPosition
from ts_scheduler.observatoryModel import ObservatoryState

class ObservatoryModelParameters(object):

    def __init__(self):

        self.TelAlt_MinPos_rad = 0.0
        self.TelAlt_MaxPos_rad = 0.0
        self.TelAz_MinPos_rad = 0.0
        self.TelAz_MaxPos_rad = 0.0
        self.TelAlt_MaxSpeed_rad = 0.0
        self.TelAlt_Accel_rad = 0.0
        self.TelAlt_Decel_rad = 0.0
        self.TelAz_MaxSpeed_rad = 0.0
        self.TelAz_Accel_rad = 0.0
        self.TelAz_Decel_rad = 0.0
        self.Mount_SettleTime = 0.0

        self.TelRot_MinPos_rad = 0.0
        self.TelRot_MaxPos_rad = 0.0
        self.TelRot_MaxSpeed_rad = 0.0
        self.TelRot_Accel_rad = 0.0
        self.TelRot_Decel_rad = 0.0
        self.TelRot_FilterChangePos_rad = 0.0
        self.Rotator_FollowSky = False
        self.Rotator_ResumeAngle = False

        self.DomAlt_MaxSpeed_rad = 0.0
        self.DomAlt_Accel_rad = 0.0
        self.DomAlt_Decel_rad = 0.0
        self.DomAz_MaxSpeed_rad = 0.0
        self.DomAz_Accel_rad = 0.0
        self.DomAz_Decel_rad = 0.0
        self.DomAz_SettleTime = 0.0

        self.OpticsOL_Slope = 0.0
        self.OpticsCL_Delay = []
        self.OpticsCL_AltLimit = []

        self.ReadoutTime = 0.0
        self.ShutterTime = 0.0
        self.Filter_ChangeTime = 0.0
        self.filter_darktime = "u"
        self.filter_removable_list = []
        self.filter_max_changes_burst_num = 0
        self.filter_max_changes_burst_time = 0.0
        self.filter_max_changes_avg_num = 0
        self.filter_max_changes_avg_time = 0.0
        self.filter_init_mounted_list = []
        self.filter_init_unmounted_list = []

        self.prerequisites = {}

    def configure_telescope(self, confdict):

        self.TelAlt_MinPos_rad = math.radians(confdict["telescope"]["altitude_minpos"])
        self.TelAlt_MaxPos_rad = math.radians(confdict["telescope"]["altitude_maxpos"])
        self.TelAz_MinPos_rad = math.radians(confdict["telescope"]["azimuth_minpos"])
        self.TelAz_MaxPos_rad = math.radians(confdict["telescope"]["azimuth_maxpos"])
        self.TelAlt_MaxSpeed_rad = math.radians(confdict["telescope"]["altitude_maxspeed"])
        self.TelAlt_Accel_rad = math.radians(confdict["telescope"]["altitude_accel"])
        self.TelAlt_Decel_rad = math.radians(confdict["telescope"]["altitude_decel"])
        self.TelAz_MaxSpeed_rad = math.radians(confdict["telescope"]["azimuth_maxspeed"])
        self.TelAz_Accel_rad = math.radians(confdict["telescope"]["azimuth_accel"])
        self.TelAz_Decel_rad = math.radians(confdict["telescope"]["azimuth_decel"])
        self.Mount_SettleTime = confdict["telescope"]["settle_time"]

    def configure_rotator(self, confdict):

        self.TelRot_MinPos_rad = math.radians(confdict["rotator"]["minpos"])
        self.TelRot_MaxPos_rad = math.radians(confdict["rotator"]["maxpos"])
        self.TelRot_MaxSpeed_rad = math.radians(confdict["rotator"]["maxspeed"])
        self.TelRot_Accel_rad = math.radians(confdict["rotator"]["accel"])
        self.TelRot_Decel_rad = math.radians(confdict["rotator"]["decel"])
        self.TelRot_FilterChangePos_rad = math.radians(confdict["rotator"]["filter_change_pos"])
        self.Rotator_FollowSky = confdict["rotator"]["follow_sky"]
        self.Rotator_ResumeAngle = confdict["rotator"]["resume_angle"]

    def configure_dome(self, confdict):

        self.DomAlt_MaxSpeed_rad = math.radians(confdict["dome"]["altitude_maxspeed"])
        self.DomAlt_Accel_rad = math.radians(confdict["dome"]["altitude_accel"])
        self.DomAlt_Decel_rad = math.radians(confdict["dome"]["altitude_decel"])
        self.DomAz_MaxSpeed_rad = math.radians(confdict["dome"]["azimuth_maxspeed"])
        self.DomAz_Accel_rad = math.radians(confdict["dome"]["azimuth_accel"])
        self.DomAz_Decel_rad = math.radians(confdict["dome"]["azimuth_decel"])
        self.DomAz_SettleTime = confdict["dome"]["settle_time"]

    def configure_optics(self, confdict):

        self.OpticsOL_Slope = confdict["optics_loop_corr"]["tel_optics_ol_slope"] / math.radians(1)
        self.OpticsCL_Delay = confdict["optics_loop_corr"]["tel_optics_cl_delay"]
        self.OpticsCL_AltLimit = confdict["optics_loop_corr"]["tel_optics_cl_alt_limit"]
        for index, alt in enumerate(self.OpticsCL_AltLimit):
            self.OpticsCL_AltLimit[index] = math.radians(self.OpticsCL_AltLimit[index])

    def configure_camera(self, confdict):

        self.ReadoutTime = confdict["camera"]["readout_time"]
        self.ShutterTime = confdict["camera"]["shutter_time"]
        self.Filter_ChangeTime = confdict["camera"]["filter_change_time"]
        self.filter_removable_list = confdict["camera"]["filter_removable"]
        self.filter_max_changes_burst_num = confdict["camera"]["filter_max_changes_burst_num"]
        self.filter_max_changes_burst_time = confdict["camera"]["filter_max_changes_burst_time"]
        self.filter_max_changes_avg_num = confdict["camera"]["filter_max_changes_avg_num"]
        self.filter_max_changes_avg_time = confdict["camera"]["filter_max_changes_avg_time"]

        self.filter_init_mounted_list = confdict["camera"]["filter_mounted"]
        self.filter_init_unmounted_list = confdict["camera"]["filter_unmounted"]

    def configure_slew(self, confdict, activities):

        for activity in activities:
            key = "prereq_" + activity
            self.prerequisites[activity] = confdict["slew"][key]

class ObservatoryModel(object):

    def __init__(self, location=None):

        self.log = logging.getLogger("observatoryModel")

        self.params = ObservatoryModelParameters()
        if location is None:
            self.location = ObservatoryLocation()
        else:
            self.location = location
        self.parkState = ObservatoryState()
        self.currentState = ObservatoryState()
        self.targetPosition = ObservatoryPosition()

        self.filters = ["u", "g", "r", "i", "z", "y"]

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
        self.function_get_delay_for = {}
        self.delay_for = {}
        self.longest_prereq_for = {}
        for activity in self.activities:
            function_name = "get_delay_for_" + activity
            self.function_get_delay_for[activity] = getattr(self, function_name)
            self.delay_for[activity] = 0.0
            self.longest_prereq_for[activity] = ""
        self.lastslew_delays_dict = {}
        self.lastslew_criticalpath = []
        self.filter_changes_list = []

    def __str__(self):
        return self.currentState.__str__()

    def configure(self, confdict):

        self.configure_telescope(confdict)
        self.configure_rotator(confdict)
        self.configure_dome(confdict)
        self.configure_optics(confdict)
        self.configure_camera(confdict)
        self.configure_slew(confdict)
        self.configure_park(confdict)

        self.currentState.mountedfilters = self.params.filter_init_mounted_list
        self.currentState.unmountedfilters = self.params.filter_init_unmounted_list
        self.parkState.mountedfilters = self.currentState.mountedfilters
        self.parkState.unmountedfilters = self.currentState.unmountedfilters

        self.reset()

    def configure_telescope(self, confdict):

        self.params.configure_telescope(confdict)

        self.log.log(WORDY,
                     "configure_telescope: TelAlt_MinPos=%.3f" %
                     (math.degrees(self.params.TelAlt_MinPos_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAlt_MaxPos=%.3f" %
                     (math.degrees(self.params.TelAlt_MaxPos_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAz_MinPos=%.3f" %
                     (math.degrees(self.params.TelAz_MinPos_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAz_MaxPos=%.3f" %
                     (math.degrees(self.params.TelAz_MaxPos_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAlt_MaxSpeed=%.3f" %
                     (math.degrees(self.params.TelAlt_MaxSpeed_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAlt_Accel=%.3f" %
                     (math.degrees(self.params.TelAlt_Accel_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAlt_Decel=%.3f" %
                     (math.degrees(self.params.TelAlt_Decel_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAz_MaxSpeed=%.3f" %
                     (math.degrees(self.params.TelAz_MaxSpeed_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAz_Accel=%.3f" %
                     (math.degrees(self.params.TelAz_Accel_rad)))
        self.log.log(WORDY,
                     "configure_telescope: TelAz_Decel=%.3f" %
                     (math.degrees(self.params.TelAz_Decel_rad)))
        self.log.log(WORDY,
                     "configure_telescope: Mount_SettleTime=%.3f" %
                     (self.params.Mount_SettleTime))

    def configure_rotator(self, confdict):

        self.params.configure_rotator(confdict)

        self.log.log(WORDY,
                     "configure_rotator: TelRot_MinPos=%.3f" %
                     (math.degrees(self.params.TelRot_MinPos_rad)))
        self.log.log(WORDY,
                     "configure_rotator: TelRot_MaxPos=%.3f" %
                     (math.degrees(self.params.TelRot_MaxPos_rad)))
        self.log.log(WORDY,
                     "configure_rotator: TelRot_MaxSpeed=%.3f" %
                     (math.degrees(self.params.TelRot_MaxSpeed_rad)))
        self.log.log(WORDY,
                     "configure_rotator: TelRot_Accel=%.3f" %
                     (math.degrees(self.params.TelRot_Accel_rad)))
        self.log.log(WORDY,
                     "configure_rotator: TelRot_Decel=%.3f" %
                     (math.degrees(self.params.TelRot_Decel_rad)))
        self.log.log(WORDY,
                     "configure_rotator: TelRot_FilterChangePos=%.3f" %
                     (math.degrees(self.params.TelRot_FilterChangePos_rad)))
        self.log.log(WORDY,
                     "configure_rotator: Rotator_FollowSky=%s" %
                     (self.params.Rotator_FollowSky))
        self.log.log(WORDY,
                     "configure_rotator: Rotator_ResumeAngle=%s" %
                     (self.params.Rotator_ResumeAngle))

    def configure_dome(self, confdict):

        self.params.configure_dome(confdict)

        self.log.log(WORDY,
                     "configure_dome: DomAlt_MaxSpeed=%.3f" % (math.degrees(self.params.DomAlt_MaxSpeed_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAlt_Accel=%.3f" % (math.degrees(self.params.DomAlt_Accel_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAlt_Decel=%.3f" % (math.degrees(self.params.DomAlt_Decel_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAz_MaxSpeed=%.3f" % (math.degrees(self.params.DomAz_MaxSpeed_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAz_Accel=%.3f" % (math.degrees(self.params.DomAz_Accel_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAz_Decel=%.3f" % (math.degrees(self.params.DomAz_Decel_rad)))
        self.log.log(WORDY,
                     "configure_dome: DomAz_SettleTime=%.3f" % (self.params.DomAz_SettleTime))

    def configure_optics(self, confdict):

        self.params.configure_optics(confdict)

        self.log.log(WORDY,
                     "configure_optics: OpticsOL_Slope=%.3f" % (self.params.OpticsOL_Slope))
        self.log.log(WORDY,
                     "configure_optics: OpticsCL_Delay=%s" % (self.params.OpticsCL_Delay))
        self.log.log(WORDY,
                     "configure_optics: OpticsCL_AltLimit=%s" % (self.params.OpticsCL_AltLimit))

    def configure_camera(self, confdict):

        self.params.configure_camera(confdict)

        self.log.log(WORDY,
                     "configure_camera: Filter_ChangeTime=%.1f" %
                     (self.params.Filter_ChangeTime))
        self.log.log(WORDY,
                     "configure_camera: ReadoutTime=%.1f" %
                     (self.params.ReadoutTime))
        self.log.log(WORDY,
                     "configure_camera: ShutterTime=%.1f" %
                     (self.params.ShutterTime))
        self.log.log(WORDY,
                     "configure_camera: filter_removable=%s" %
                     (self.params.filter_removable_list))
        self.log.log(WORDY,
                     "configure_camera: filter_max_changes_burst_num=%i" %
                     (self.params.filter_max_changes_burst_num))
        self.log.log(WORDY,
                     "configure_camera: filter_max_changes_burst_time=%.1f" %
                     (self.params.filter_max_changes_burst_time))
        self.log.log(WORDY,
                     "configure_camera: filter_max_changes_avg_num=%i" %
                     (self.params.filter_max_changes_avg_num))
        self.log.log(WORDY,
                     "configure_camera: filter_max_changes_avg_time=%.1f" %
                     (self.params.filter_max_changes_avg_time))
        self.log.log(WORDY,
                     "configure_camera: filter_init_mounted=%s" %
                     (self.params.filter_init_mounted_list))
        self.log.log(WORDY,
                     "configure_camera: filter_init_unmounted=%s" %
                     (self.params.filter_init_unmounted_list))

    def configure_slew(self, confdict):

        self.params.configure_slew(confdict, self.activities)

        for activity in self.activities:
            self.log.log(WORDY, "configure_slew: prerequisites[%s]=%s" %
                         (activity, self.params.prerequisites[activity]))

    def configure_park(self, confdict):

        self.parkState.alt_rad = math.radians(confdict["park"]["telescope_altitude"])
        self.parkState.az_rad = math.radians(confdict["park"]["telescope_azimuth"])
        self.parkState.rot_rad = math.radians(confdict["park"]["telescope_rotator"])
        self.parkState.telalt_rad = math.radians(confdict["park"]["telescope_altitude"])
        self.parkState.telaz_rad = math.radians(confdict["park"]["telescope_azimuth"])
        self.parkState.telrot_rad = math.radians(confdict["park"]["telescope_rotator"])
        self.parkState.domalt_rad = math.radians(confdict["park"]["dome_altitude"])
        self.parkState.domaz_rad = math.radians(confdict["park"]["dome_azimuth"])
        self.parkState.filter = confdict["park"]["filter_position"]
        self.parkState.mountedfilters = self.currentState.mountedfilters
        self.parkState.unmountedfilters = self.currentState.unmountedfilters
        self.parkState.tracking = False

        self.log.log(WORDY,
                     "configure_park: park_Telalt_rad=%.3f" % (self.parkState.telalt_rad))
        self.log.log(WORDY,
                     "configure_park: park_Telaz_rad=%.3f" % (self.parkState.telaz_rad))
        self.log.log(WORDY,
                     "configure_park: park_Telrot_rad=%.3f" % (self.parkState.telrot_rad))
        self.log.log(WORDY,
                     "configure_park: park_Domalt_rad=%.3f" % (self.parkState.domalt_rad))
        self.log.log(WORDY,
                     "configure_park: park_Domaz_rad=%.3f" % (self.parkState.domaz_rad))
        self.log.log(WORDY,
                     "configure_park: park_Filter=%s" % (self.parkState.filter))

    def set_state(self, new_state):

        self.currentState.set(new_state)

    def update_state(self, time):

        if time < self.currentState.time:
            time = self.currentState.time

        if self.currentState.tracking:

            targetposition = self.radecang2position(time,
                                                    self.currentState.ra_rad,
                                                    self.currentState.dec_rad,
                                                    self.currentState.ang_rad,
                                                    self.currentState.filter)

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

    def get_slew_delay(self, target):

        # check if filter is possible
        if target.filter not in self.currentState.mountedfilters:
            return -1.0

        targetposition = self.radecang2position(self.currentState.time,
                                                target.ra_rad,
                                                target.dec_rad,
                                                target.ang_rad,
                                                target.filter)
        if not self.params.Rotator_FollowSky:
            #override rotator position with current telrot
            targetposition.rot_rad = self.currentState.telrot_rad

        # check if altitude is possible
        if targetposition.alt_rad < self.params.TelAlt_MinPos_rad:
            return -1.0
        if targetposition.alt_rad > self.params.TelAlt_MaxPos_rad:
            return -1.0

        targetstate = self.get_closest_state(targetposition)
        target.ang_rad = targetstate.ang_rad
        target.alt_rad = targetstate.alt_rad
        target.az_rad = targetstate.az_rad
        target.rot_rad = targetstate.rot_rad
        target.telalt_rad = targetstate.telalt_rad
        target.telaz_rad = targetstate.telaz_rad
        target.telrot_rad = targetstate.telrot_rad

        return self.get_slew_delay_for_state(targetstate, self.currentState, False)

    def get_closest_state(self, targetposition):

        (telalt_rad, delta_telalt_rad) = self.get_closest_angle_distance(targetposition.alt_rad,
                                                                         self.currentState.telalt_rad,
                                                                         self.params.TelAlt_MinPos_rad,
                                                                         self.params.TelAlt_MaxPos_rad)
        (telaz_rad, delta_telaz_rad) = self.get_closest_angle_distance(targetposition.az_rad,
                                                                       self.currentState.telaz_rad,
                                                                       self.params.TelAz_MinPos_rad,
                                                                       self.params.TelAz_MaxPos_rad)

        # if the target rotator angle is unreachable
        # then sets an arbitrary value (oposite)
        norm_rot_rad = divmod(targetposition.rot_rad - self.params.TelRot_MinPos_rad, TWOPI)[1] \
            + self.params.TelRot_MinPos_rad
        if norm_rot_rad > self.params.TelRot_MaxPos_rad:
            targetposition.rot_rad = norm_rot_rad - math.pi
        (telrot_rad, delta_telrot_rad) = self.get_closest_angle_distance(targetposition.rot_rad,
                                                                         self.currentState.telrot_rad,
                                                                         self.params.TelRot_MinPos_rad,
                                                                         self.params.TelRot_MaxPos_rad)
        targetposition.ang_rad = targetposition.pa_rad - telrot_rad

        (domalt_rad, delta_domalt_rad) = self.get_closest_angle_distance(targetposition.alt_rad,
                                                                         self.currentState.domalt_rad,
                                                                         self.params.TelAlt_MinPos_rad,
                                                                         self.params.TelAlt_MaxPos_rad)
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
        if min_abs_rad is not None:
            norm_target_rad = divmod(target_rad - min_abs_rad, TWOPI)[1] + min_abs_rad
            if max_abs_rad is not None:
                # if the target angle is unreachable
                # then sets an arbitrary value
                if norm_target_rad > max_abs_rad:
                    norm_target_rad = max(min_abs_rad, norm_target_rad - math.pi)
        else:
            norm_target_rad = target_rad

        # computes the distance clockwise
        distance_rad = divmod(norm_target_rad - current_abs_rad, TWOPI)[1]

        # take the counter-clockwise distance if shorter
        if distance_rad > math.pi:
            distance_rad = distance_rad - TWOPI

        # if there are wrap limits
        if (min_abs_rad is not None) and (max_abs_rad is not None):
            # compute accumulated angle
            accum_abs_rad = current_abs_rad + distance_rad

            # if limits reached chose the other direction
            if accum_abs_rad > max_abs_rad:
                distance_rad = distance_rad - TWOPI
            if accum_abs_rad < min_abs_rad:
                distance_rad = distance_rad + TWOPI

        # compute final accumulated angle
        final_abs_rad = current_abs_rad + distance_rad

        return (final_abs_rad, distance_rad)

    def radecang2position(self, time, ra_rad, dec_rad, ang_rad, filter):

        (alt_rad, az_rad, pa_rad) = self.radec2altazpa(time, ra_rad, dec_rad)

        position = ObservatoryPosition()
        position.time = time
        position.tracking = True
        position.ra_rad = ra_rad
        position.dec_rad = dec_rad
        position.ang_rad = ang_rad
        position.filter = filter
        position.alt_rad = alt_rad
        position.az_rad = az_rad
        position.pa_rad = pa_rad
        position.rot_rad = divmod(pa_rad - ang_rad, TWOPI)[1]

        return position

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
        if time < self.currentState.time:
            time = self.currentState.time
        if not self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = True

    def stop_tracking(self, time):
        if time < self.currentState.time:
            time = self.currentState.time
        if self.currentState.tracking:
            self.update_state(time)
            self.currentState.tracking = False

    def slew_altaz(self, time, alt_rad, az_rad, rot_rad, filter):

        self.update_state(time)
        time = self.currentState.time

        targetposition = ObservatoryPosition()
        targetposition.time = time
        targetposition.tracking = False
        targetposition.alt_rad = alt_rad
        targetposition.az_rad = az_rad
        targetposition.rot_rad = rot_rad
        targetposition.filter = filter

        self.slew_to_position(targetposition)

    def slew_radec(self, time, ra_rad, dec_rad, ang_rad, filter):

        self.update_state(time)
        time = self.currentState.time

        targetposition = self.radecang2position(time, ra_rad, dec_rad, ang_rad, filter)
        if not self.params.Rotator_FollowSky:
            targetposition.rot_rad = self.currentState.telrot_rad

        self.slew_to_position(targetposition)

    def slew(self, target):

        self.slew_radec(self.currentState.time,
                        target.ra_rad, target.dec_rad, target.ang_rad, target.filter)

    def observe(self, target):
        return

    def park(self):
        return

    def swap_filter(self, filter_to_unmount):

        if filter_to_unmount in self.currentState.mountedfilters:
            self.currentState.mountedfilters.remove(filter_to_unmount)
            filter_to_mount = self.currentState.unmountedfilters.pop()
            self.currentState.mountedfilters.append(filter_to_mount)
            self.currentState.unmountedfilters.append(filter_to_unmount)

            self.parkState.mountedfilters = self.currentState.mountedfilters
            self.parkState.unmountedfilters = self.currentState.unmountedfilters
        else:
            self.log.info("swap_filter: REJECTED filter %s is not mounted" %
                          (filter_to_unmount))
        

    def slew_to_position(self, targetposition):

        targetstate = self.get_closest_state(targetposition)
        targetstate.mountedfilters = self.currentState.mountedfilters
        targetstate.unmountedfilters = self.currentState.unmountedfilters
        slew_delay = self.get_slew_delay_for_state(targetstate, self.currentState, True)
        if targetposition.filter != self.currentState.filter:
            self.filter_changes_list.append(targetstate.time)
        targetstate.time = targetstate.time + slew_delay
        self.currentState.set(targetstate)
        self.update_state(targetstate.time)

    def reset(self):

        self.set_state(self.parkState)

    def compute_kinematic_delay(self, distance, maxspeed, accel, decel):

        d = abs(distance)

        vpeak = (2 * d / (1 / accel + 1 / decel)) ** 0.5
        if vpeak <= maxspeed:
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

    def get_slew_delay_for_state(self, targetstate, initstate, include_slew_data=False):

        last_activity = "exposures"
        slew_delay = self.get_delay_after(last_activity, targetstate, initstate)

        self.lastslew_delays_dict = {}
        self.lastslew_criticalpath = []
        if include_slew_data:
            for act in self.activities:
                self.lastslew_delays_dict[act] = self.delay_for[act]

            activity = last_activity
            while activity != "":
                dt = self.delay_for[activity]
                if dt > 0:
                    self.lastslew_criticalpath.append(activity)
                activity = self.longest_prereq_for[activity]

        return slew_delay

    def get_delay_after(self, activity, targetstate, initstate):

        activity_delay = self.function_get_delay_for[activity](targetstate, initstate)

        prereq_list = self.params.prerequisites[activity]

        longest_previous_delay = 0.0
        longest_prereq = ""
        for prereq in prereq_list:
            previous_delay = self.get_delay_after(prereq, targetstate, initstate)
            if previous_delay > longest_previous_delay:
                longest_previous_delay = previous_delay
                longest_prereq = prereq
        self.longest_prereq_for[activity] = longest_prereq
        self.delay_for[activity] = activity_delay

        return activity_delay + longest_previous_delay

    def get_delay_for_telalt(self, targetstate, initstate):

        distance = targetstate.telalt_rad - initstate.telalt_rad
        maxspeed = self.params.TelAlt_MaxSpeed_rad
        accel = self.params.TelAlt_Accel_rad
        decel = self.params.TelAlt_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telalt_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telaz(self, targetstate, initstate):

        distance = targetstate.telaz_rad - initstate.telaz_rad
        maxspeed = self.params.TelAz_MaxSpeed_rad
        accel = self.params.TelAz_Accel_rad
        decel = self.params.TelAz_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telaz_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telrot(self, targetstate, initstate):

        distance = targetstate.telrot_rad - initstate.telrot_rad
        maxspeed = self.params.TelRot_MaxSpeed_rad
        accel = self.params.TelRot_Accel_rad
        decel = self.params.TelRot_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.telrot_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_telsettle(self, targetstate, initstate):

        distance = abs(targetstate.telalt_rad - initstate.telalt_rad) + \
            abs(targetstate.telaz_rad - initstate.telaz_rad)

        if distance > 1e-6:
            delay = self.params.Mount_SettleTime
        else:
            delay = 0

        return delay

    def get_delay_for_telopticsopenloop(self, targetstate, initstate):

        distance = abs(targetstate.telalt_rad - initstate.telalt_rad)

        if distance > 1e-6:
            delay = distance * self.params.OpticsOL_Slope
        else:
            delay = 0

        return delay

    def get_delay_for_telopticsclosedloop(self, targetstate, initstate):

        distance = abs(targetstate.telalt_rad - initstate.telalt_rad)

        delay = 0.0
        for k, cl_delay in enumerate(self.params.OpticsCL_Delay):
            if self.params.OpticsCL_AltLimit[k] <= distance < self.params.OpticsCL_AltLimit[k + 1]:
                delay = cl_delay
                break

        return delay

    def get_delay_for_domalt(self, targetstate, initstate):

        distance = targetstate.domalt_rad - initstate.domalt_rad
        maxspeed = self.params.DomAlt_MaxSpeed_rad
        accel = self.params.DomAlt_Accel_rad
        decel = self.params.DomAlt_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.domalt_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_domaz(self, targetstate, initstate):

        distance = targetstate.domaz_rad - initstate.domaz_rad
        maxspeed = self.params.DomAz_MaxSpeed_rad
        accel = self.params.DomAz_Accel_rad
        decel = self.params.DomAz_Decel_rad

        (delay, peakspeed) = self.compute_kinematic_delay(distance, maxspeed, accel, decel)
        targetstate.domaz_peakspeed_rad = peakspeed

        return delay

    def get_delay_for_domazsettle(self, targetstate, initstate):

        distance = abs(targetstate.domaz_rad - initstate.domaz_rad)

        if distance > 1e-6:
            delay = self.params.DomAz_SettleTime
        else:
            delay = 0

        return delay

    def get_delay_for_filter(self, targetstate, initstate):

        if targetstate.filter != initstate.filter:
            if targetstate.filter in initstate.mountedfilters:
                burst_num = self.params.filter_max_changes_burst_num
                if len(self.filter_changes_list) >= burst_num:
                    deltatime = initstate.time - self.filter_changes_list[-burst_num]
                    if deltatime >= self.params.filter_max_changes_burst_time:
                        avg_num = self.params.filter_max_changes_avg_num
                        if len(self.filter_changes_list) >= avg_num:
                            deltatime = initstate.time - self.filter_changes_list[-avg_num]
                            if deltatime >= self.params.filter_max_changes_avg_time:
                                delay = self.params.Filter_ChangeTime
                            else:
                                delay = -1.0
                        else:
                            delay = self.params.Filter_ChangeTime
                    else:
                        delay = -1.0
                else:
                    delay = self.params.Filter_ChangeTime
            else:
                delay = -1.0
        else:
            delay = 0.0

        return delay

    def get_delay_for_readout(self, targetstate, initstate):

        return self.params.ReadoutTime

    def get_delay_for_exposures(self, targetstate, initstate):

        return 0.0

    def estimate_slewtime(self):
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
