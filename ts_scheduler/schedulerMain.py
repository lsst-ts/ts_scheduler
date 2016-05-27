import logging
import logging.handlers
import sys
import time
import math

from SALPY_scheduler import SAL_scheduler
from SALPY_scheduler import scheduler_timeHandlerC
from SALPY_scheduler import scheduler_observatoryStateC
from SALPY_scheduler import scheduler_observationTestC
from SALPY_scheduler import scheduler_targetTestC
from SALPY_scheduler import scheduler_fieldC
from SALPY_scheduler import scheduler_schedulerConfigC
from SALPY_scheduler import scheduler_obsSiteConfigC
from SALPY_scheduler import scheduler_telescopeConfigC
from SALPY_scheduler import scheduler_domeConfigC
from SALPY_scheduler import scheduler_rotatorConfigC
from SALPY_scheduler import scheduler_cameraConfigC
from SALPY_scheduler import scheduler_slewConfigC
from SALPY_scheduler import scheduler_parkConfigC

from ts_scheduler.schedulerDefinitions import INFOX, RAD2DEG, DEG2RAD, read_conf_file, conf_file_path
from ts_scheduler.schedulerDriver import Driver
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryState

class Main(object):

    def __init__(self, options):
        self.log = logging.getLogger("schedulerMain")

        main_confdict = read_conf_file(conf_file_path(__name__, "../conf", "scheduler", "main.conf"))
        self.measinterval = main_confdict['log']['rate_meas_interval']

        self.schedulerDriver = Driver()

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)

        self.topic_schedulerConfig = scheduler_schedulerConfigC()
        self.topic_obsSiteConfig = scheduler_obsSiteConfigC()
        self.topic_telescopeConfig = scheduler_telescopeConfigC()
        self.topic_domeConfig = scheduler_domeConfigC()
        self.topic_rotatorConfig = scheduler_rotatorConfigC()
        self.topic_cameraConfig = scheduler_cameraConfigC()
        self.topic_slewConfig = scheduler_slewConfigC()
        self.topic_parkConfig = scheduler_parkConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservatoryState = scheduler_observatoryStateC()
        self.topicObservation = scheduler_observationTestC()
        self.topicField = scheduler_fieldC()
        self.topicTarget = scheduler_targetTestC()

    def run(self):

        self.log.info("run")

        self.sal.salTelemetrySub("scheduler_schedulerConfig")
        self.sal.salTelemetrySub("scheduler_obsSiteConfig")
        self.sal.salTelemetrySub("scheduler_telescopeConfig")
        self.sal.salTelemetrySub("scheduler_domeConfig")
        self.sal.salTelemetrySub("scheduler_rotatorConfig")
        self.sal.salTelemetrySub("scheduler_cameraConfig")
        self.sal.salTelemetrySub("scheduler_slewConfig")
        self.sal.salTelemetrySub("scheduler_parkConfig")
        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observatoryState")
        self.sal.salTelemetrySub("scheduler_observationTest")
        self.sal.salTelemetryPub("scheduler_field")
        self.sal.salTelemetryPub("scheduler_targetTest")

        meascount = 0
        visitcount = 0
        synccount = 0

        meastime = time.time()

        timestamp = 0.0

        try:
            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_schedulerConfig(self.topic_schedulerConfig)
                if (scode == 0 and self.topic_schedulerConfig.log_file != ""):
                    lastconfigtime = time.time()
                    logfilename = self.topic_schedulerConfig.log_file
                    self.log.info("run: rx scheduler config logfile=%s" % (logfilename))
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: scheduler config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_obsSiteConfig(self.topic_obsSiteConfig)
                if (scode == 0 and self.topic_obsSiteConfig.name != ""):
                    lastconfigtime = time.time()
                    latitude = self.topic_obsSiteConfig.latitude
                    longitude = self.topic_obsSiteConfig.longitude
                    height = self.topic_obsSiteConfig.height
                    self.log.info("run: rx site config latitude=%.3f longitude=%.3f height=%.0f" % (latitude, longitude, height))
                    self.schedulerDriver.configure_location(math.radians(latitude), math.radians(longitude), height)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: site config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_telescopeConfig(self.topic_telescopeConfig)
                if (scode == 0 and self.topic_telescopeConfig.altitude_minpos >= 0):
                    lastconfigtime = time.time()

                    altitude_minpos = self.topic_telescopeConfig.altitude_minpos
                    altitude_maxpos = self.topic_telescopeConfig.altitude_maxpos
                    azimuth_minpos = self.topic_telescopeConfig.azimuth_minpos
                    azimuth_maxpos = self.topic_telescopeConfig.azimuth_maxpos
                    altitude_maxspeed = self.topic_telescopeConfig.altitude_maxspeed
                    altitude_accel = self.topic_telescopeConfig.altitude_accel
                    altitude_decel = self.topic_telescopeConfig.altitude_decel
                    azimuth_maxspeed = self.topic_telescopeConfig.azimuth_maxspeed
                    azimuth_accel = self.topic_telescopeConfig.azimuth_accel
                    azimuth_decel = self.topic_telescopeConfig.azimuth_decel
                    settle_time = self.topic_telescopeConfig.settle_time

                    self.log.info("run: rx telescope config altitude_minpos=%.3f altitude_maxpos=%.3f "
                                  "azimuth_minpos=%.3f azimuth_maxpos=%.3f" %
                                  (altitude_minpos, altitude_maxpos, azimuth_minpos, azimuth_maxpos))
                    self.schedulerDriver.configure_telescope(math.radians(altitude_minpos),
                                                             math.radians(altitude_maxpos),
                                                             math.radians(azimuth_minpos),
                                                             math.radians(azimuth_maxpos),
                                                             math.radians(altitude_maxspeed),
                                                             math.radians(altitude_accel),
                                                             math.radians(altitude_decel),
                                                             math.radians(azimuth_maxspeed),
                                                             math.radians(azimuth_accel),
                                                             math.radians(azimuth_decel),
                                                             settle_time)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: telescope config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_domeConfig(self.topic_domeConfig)
                if (scode == 0 and self.topic_domeConfig.altitude_maxspeed >= 0):
                    lastconfigtime = time.time()

                    altitude_maxspeed = self.topic_domeConfig.altitude_maxspeed
                    altitude_accel = self.topic_domeConfig.altitude_accel
                    altitude_decel = self.topic_domeConfig.altitude_decel
                    azimuth_maxspeed = self.topic_domeConfig.azimuth_maxspeed
                    azimuth_accel = self.topic_domeConfig.azimuth_accel
                    azimuth_decel = self.topic_domeConfig.azimuth_decel
                    settle_time = self.topic_domeConfig.settle_time

                    self.log.info("run: rx dome config altitude_maxspeed=%.3f azimuth_maxspeed=%.3f" %
                                  (altitude_maxspeed, azimuth_maxspeed))
                    self.schedulerDriver.configure_dome(math.radians(altitude_maxspeed),
                                                        math.radians(altitude_accel),
                                                        math.radians(altitude_decel),
                                                        math.radians(azimuth_maxspeed),
                                                        math.radians(azimuth_accel),
                                                        math.radians(azimuth_decel),
                                                        settle_time)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: dome config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_rotatorConfig(self.topic_rotatorConfig)
                if (scode == 0 and self.topic_rotatorConfig.minpos >= 0):
                    lastconfigtime = time.time()

                    minpos = self.topic_rotatorConfig.minpos
                    maxpos = self.topic_rotatorConfig.maxpos
                    maxspeed = self.topic_rotatorConfig.maxspeed
                    accel = self.topic_rotatorConfig.accel
                    decel = self.topic_rotatorConfig.decel
                    filterchangepos = self.topic_rotatorConfig.filter_change_pos
                    follow_sky = self.topic_rotatorConfig.followsky
                    resume_angle = self.topic_rotatorConfig.resume_angle

                    self.log.info("run: rx rotator config minpos=%.3f maxpos=%.3f "
                                  "followsky=%s resume_angle=%s" %
                                  (minpos, maxpos, followsky, resume_angle))
                    self.schedulerDriver.configure_rotator(math.radians(minpos),
                                                           math.radians(maxpos),
                                                           math.radians(maxspeed),
                                                           math.radians(accel),
                                                           math.radians(decel),
                                                           math.radians(filterchangepos),
                                                           follow_sky,
                                                           resume_angle)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: telescope config timeout")

            field_dict = self.schedulerDriver.get_fields_dict()
            if len(field_dict) > 0:
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)
                for fieldid in field_dict:
                    self.topicField.ID = field_dict[fieldid].fieldid
                    self.topicField.ra = field_dict[fieldid].ra_rad * RAD2DEG
                    self.topicField.dec = field_dict[fieldid].dec_rad * RAD2DEG
                    self.topicField.gl = field_dict[fieldid].gl_rad * RAD2DEG
                    self.topicField.gb = field_dict[fieldid].gb_rad * RAD2DEG
                    self.topicField.el = field_dict[fieldid].el_rad * RAD2DEG
                    self.topicField.eb = field_dict[fieldid].eb_rad * RAD2DEG
                    self.topicField.fov = field_dict[fieldid].fov_rad * RAD2DEG
                    self.sal.putSample_field(self.topicField)
                    self.log.log(INFOX, "run: tx field %s" % (field_dict[fieldid]))
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)

            waittime = True
            lasttimetime = time.time()
            while waittime:
                scode = self.sal.getNextSample_timeHandler(self.topicTime)
                if scode == 0 and self.topicTime.timestamp != 0:
                    if self.topicTime.timestamp > timestamp:
                        lasttimetime = time.time()
                        timestamp = self.topicTime.timestamp

                        self.log.log(INFOX, "run: rx time=%.1f" % (timestamp))

                        self.schedulerDriver.update_time(self.topicTime.timestamp)

                        waitstate = True
                        laststatetime = time.time()
                        while waitstate:
                            scode = self.sal.getNextSample_observatoryState(self.topicObservatoryState)
                            if scode == 0 and self.topicObservatoryState.timestamp != 0:
                                laststatetime = time.time()
                                waitstate = False
                                observatory_state = self.create_observatory_state(self.topicObservatoryState)

                                self.log.log(INFOX, "run: rx state %s" % str(observatory_state))

                                self.schedulerDriver.update_internal_conditions(observatory_state)
                                target = self.schedulerDriver.select_next_target()

                                self.topicTarget.targetId = target.targetid
                                self.topicTarget.fieldId = target.fieldid
                                self.topicTarget.filter = target.filter
                                self.topicTarget.ra = target.ra_rad * RAD2DEG
                                self.topicTarget.dec = target.dec_rad * RAD2DEG
                                self.topicTarget.angle = target.ang_rad * RAD2DEG
                                self.topicTarget.num_exposures = target.num_exp
                                for i, exptime in enumerate(target.exp_times):
                                    self.topicTarget.exposure_times[i] = int(exptime)
                                self.sal.putSample_targetTest(self.topicTarget)

                                self.log.log(INFOX, "run: tx target %s", str(target))

                                waitobservation = True
                                lastobstime = time.time()
                                while waitobservation:
                                    scode = self.sal.getNextSample_observationTest(self.topicObservation)
                                    if scode == 0 and self.topicObservation.targetId != 0:
                                        lastobstime = time.time()
                                        meascount += 1
                                        visitcount += 1
                                        if self.topicTarget.targetId == self.topicObservation.targetId:
                                            synccount += 1

                                            observation = self.create_observation(self.topicObservation)
                                            self.log.log(INFOX, "run: rx observation %s", str(observation))
                                            self.schedulerDriver.register_observation(observation)

                                            waitobservation = False
                                        else:
                                            self.log.warning("run: rx unsync observation Id=%i "
                                                             "for target Id=%i" %
                                                             (self.topicObservation.targetId,
                                                              self.topicTarget.targetId))
                                    else:
                                        to = time.time()
                                        if (to - lastobstime > 10.0):
                                            waitobservation = False
                                        self.log.debug("run: t=%f lastobstime=%f" % (to, lastobstime))

                                    newtime = time.time()
                                    deltatime = newtime - meastime
                                    if deltatime >= self.measinterval:
                                        rate = float(meascount) / deltatime
                                        self.log.info("run: rxi %.0f visits/sec total=%i visits sync=%i" %
                                                      (rate, visitcount, synccount))
                                        meastime = newtime
                                        meascount = 0
                            else:
                                ts = time.time()
                                if (ts - laststatetime > 10.0):
                                    waitstate = False
                                    self.log.debug("run: t=%f laststatetime=%f" % (ts, laststatetime))

                    else:
                        self.log.warning("run: rx backward time previous=%f new=%f" %
                                         (timestamp, self.topicTime.timestamp))

                else:
                    tc = time.time()
                    if (tc - lasttimetime) > 10.0:
                        waittime = False

                newtime = time.time()
                deltatime = newtime - meastime
                if deltatime >= self.measinterval:
                    rate = float(meascount) / deltatime
                    self.log.info("run: rxe %.0f visits/sec total=%i visits sync=%i" % (rate, visitcount,
                                                                                        synccount))
                    meastime = newtime
                    meascount = 0

        except KeyboardInterrupt:
            self.log.info("Scheduler interrupted")

        self.schedulerDriver.end_survey()

        self.log.info("exit")
        self.sal.salShutdown()
        sys.exit(0)

    def create_observation(self, topic_observation):

        observation = Target()
        observation.time = topic_observation.observation_start_time
        observation.targetid = topic_observation.targetId
        observation.fieldid = topic_observation.fieldId
        observation.filter = topic_observation.filter
        observation.ra_rad = topic_observation.ra * DEG2RAD
        observation.dec_rad = topic_observation.dec * DEG2RAD
        observation.ang_rad = topic_observation.angle * DEG2RAD
        observation.num_exp = topic_observation.num_exposures
        observation.exp_times = []
        for i in range(topic_observation.num_exposures):
            observation.exp_times.append(topic_observation.exposure_times[i])

        return observation

    def create_observatory_state(self, topic_state):

        state = ObservatoryState()

        state.time = topic_state.timestamp
        state.ra_rad = topic_state.pointing_ra * DEG2RAD
        state.dec_rad = topic_state.pointing_dec * DEG2RAD
        state.ang_rad = topic_state.pointing_angle * DEG2RAD
        state.filter = topic_state.filter_position
        state.tracking = topic_state.tracking
        state.alt_rad = topic_state.pointing_altitude * DEG2RAD
        state.az_rad = topic_state.pointing_azimuth * DEG2RAD
        state.pa_rad = topic_state.pointing_pa * DEG2RAD
        state.rot_rad = topic_state.pointing_rot * DEG2RAD
        state.telalt_rad = topic_state.telescope_altitude * DEG2RAD
        state.telaz_rad = topic_state.telescope_azimuth * DEG2RAD
        state.telrot_rad = topic_state.telescope_rotator * DEG2RAD
        state.domalt_rad = topic_state.dome_altitude * DEG2RAD
        state.domaz_rad = topic_state.dome_azimuth * DEG2RAD
        state.mountedfilters = topic_state.filter_mounted.split(",")
        state.unmountedfilters = topic_state.filter_unmounted.split(",")

        return state
