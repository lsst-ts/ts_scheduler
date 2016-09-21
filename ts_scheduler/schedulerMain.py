import logging
import logging.handlers
import sys
import time
import math

from SALPY_scheduler import SAL_scheduler
from SALPY_scheduler import scheduler_timeHandlerC
from SALPY_scheduler import scheduler_observatoryStateC
from SALPY_scheduler import scheduler_observationC
from SALPY_scheduler import scheduler_targetC
from SALPY_scheduler import scheduler_fieldC
from SALPY_scheduler import scheduler_schedulerConfigC
from SALPY_scheduler import scheduler_driverConfigC
from SALPY_scheduler import scheduler_obsSiteConfigC
from SALPY_scheduler import scheduler_telescopeConfigC
from SALPY_scheduler import scheduler_domeConfigC
from SALPY_scheduler import scheduler_rotatorConfigC
from SALPY_scheduler import scheduler_cameraConfigC
from SALPY_scheduler import scheduler_slewConfigC
from SALPY_scheduler import scheduler_opticsLoopCorrConfigC
from SALPY_scheduler import scheduler_parkConfigC
from SALPY_scheduler import scheduler_areaDistPropConfigC

#from SALPY_scheduler import flushSamples_schedulerConfig

from ts_scheduler.setup import TRACE
from ts_scheduler.schedulerDefinitions import RAD2DEG, DEG2RAD, read_conf_file, conf_file_path
from ts_scheduler.schedulerDriver import Driver
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryState

class Main(object):

    def __init__(self, options):
        self.log = logging.getLogger("schedulerMain")

        main_confdict = read_conf_file(conf_file_path(__name__, "conf", "scheduler", "main.conf"))
        self.measinterval = main_confdict['log']['rate_meas_interval']

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)

        self.topic_schedulerConfig = scheduler_schedulerConfigC()
        self.topic_driverConfig = scheduler_driverConfigC()
        self.topic_obsSiteConfig = scheduler_obsSiteConfigC()
        self.topic_telescopeConfig = scheduler_telescopeConfigC()
        self.topic_domeConfig = scheduler_domeConfigC()
        self.topic_rotatorConfig = scheduler_rotatorConfigC()
        self.topic_cameraConfig = scheduler_cameraConfigC()
        self.topic_slewConfig = scheduler_slewConfigC()
        self.topic_opticsConfig = scheduler_opticsLoopCorrConfigC()
        self.topic_parkConfig = scheduler_parkConfigC()
        self.topic_areaDistPropConfig = scheduler_areaDistPropConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservatoryState = scheduler_observatoryStateC()
        self.topicObservation = scheduler_observationC()
        self.topicField = scheduler_fieldC()
        self.topicTarget = scheduler_targetC()

        self.schedulerDriver = Driver()

    def run(self):

        self.log.info("run")

        self.sal.salTelemetrySub("scheduler_schedulerConfig")
        self.sal.salTelemetrySub("scheduler_driverConfig")
        self.sal.salTelemetrySub("scheduler_obsSiteConfig")
        self.sal.salTelemetrySub("scheduler_telescopeConfig")
        self.sal.salTelemetrySub("scheduler_domeConfig")
        self.sal.salTelemetrySub("scheduler_rotatorConfig")
        self.sal.salTelemetrySub("scheduler_cameraConfig")
        self.sal.salTelemetrySub("scheduler_slewConfig")
        self.sal.salTelemetrySub("scheduler_opticsLoopCorrConfig")
        self.sal.salTelemetrySub("scheduler_parkConfig")
        self.sal.salTelemetrySub("scheduler_areaDistPropConfig")
        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observatoryState")
        self.sal.salTelemetrySub("scheduler_observation")
        self.sal.salTelemetryPub("scheduler_field")
        self.sal.salTelemetryPub("scheduler_target")

        #self.sal.flushSamples_schedulerConfig(self.topic_schedulerConfig)

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
                if (scode == 0 and self.topic_schedulerConfig.survey_duration > 0.0):
                    lastconfigtime = time.time()
                    survey_duration = self.topic_schedulerConfig.survey_duration
                    self.log.info("run: rx scheduler config survey_duration=%.1f" % (survey_duration))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: scheduler config timeout")
                        config_file = conf_file_path(__name__, "conf", "survey", "survey.conf")
                        config_dict = read_conf_file(config_file)
                        survey_duration = config_dict["survey"]["survey_duration"]
                        waitconfig = False
            self.schedulerDriver.configure_duration(survey_duration)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_driverConfig(self.topic_driverConfig)
                if (scode == 0 and self.topic_driverConfig.timebonus_tmax > 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_driver_config(self.topic_driverConfig)
                    self.log.info("run: rx driver config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: driver config timeout")
                        config_file = conf_file_path(__name__, "conf", "scheduler", "driver.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_obsSiteConfig(self.topic_obsSiteConfig)
                if (scode == 0 and self.topic_obsSiteConfig.name != ""):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_location_config(self.topic_obsSiteConfig)
                    self.log.info("run: rx site config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: site config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "site.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_location(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_telescopeConfig(self.topic_telescopeConfig)
                if (scode == 0 and self.topic_telescopeConfig.altitude_minpos >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_telescope_config(self.topic_telescopeConfig)
                    self.log.info("run: rx telescope config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: telescope config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_telescope(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_domeConfig(self.topic_domeConfig)
                if (scode == 0 and self.topic_domeConfig.altitude_maxspeed >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_dome_config(self.topic_domeConfig)
                    self.log.info("run: rx dome config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: dome config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_dome(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_rotatorConfig(self.topic_rotatorConfig)
                if (scode == 0 and self.topic_rotatorConfig.maxspeed >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_rotator_config(self.topic_rotatorConfig)
                    self.log.info("run: rx rotator config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: rotator config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_rotator(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_cameraConfig(self.topic_cameraConfig)
                if (scode == 0 and self.topic_cameraConfig.readout_time > 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_camera_config(self.topic_cameraConfig)
                    self.log.info("run: rx camera config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: camera config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_camera(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_slewConfig(self.topic_slewConfig)
                if (scode == 0 and self.topic_slewConfig.prereq_exposures != ""):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_slew_config(self.topic_slewConfig)
                    self.log.info("run: rx slew config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: slew config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_slew(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_opticsLoopCorrConfig(self.topic_opticsConfig)
                if (scode == 0 and self.topic_opticsConfig.tel_optics_ol_slope > 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_optics_config(self.topic_opticsConfig)
                    self.log.info("run: rx optics config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: optics config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_optics(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_parkConfig(self.topic_parkConfig)
                if (scode == 0 and self.topic_parkConfig.telescope_altitude > 0):
                    lastconfigtime = time.time()
                    config_dict = self.read_topic_park_config(self.topic_parkConfig)
                    self.log.info("run: rx park config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: optics config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
            self.schedulerDriver.configure_park(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            config_dict = None
            while waitconfig:
                scode = self.sal.getNextSample_areaDistPropConfig(self.topic_areaDistPropConfig)
                if (scode == 0 and self.topic_areaDistPropConfig.name != ""):
                    lastconfigtime = time.time()
                    name = self.topic_areaDistPropConfig.name
                    config_dict = self.read_topic_area_prop_config(self.topic_areaDistPropConfig)
                    self.log.info("run: rx area prop config=%s" % (config_dict))
                    self.schedulerDriver.create_area_proposal(name, config_dict)
                    waitconfig = True
                else:
                    tf = time.time()
                    if self.topic_areaDistPropConfig.name == "":
                        self.log.info("run: area prop config end")
                        waitconfig = False
                    if tf - lastconfigtime > 10.0:
                        self.log.info("run: area prop config timeout")
                        waitconfig = False

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
                    self.log.debug("run: tx field %s" % (field_dict[fieldid]))
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
                        nightstamp = self.topicTime.night
                        self.log.debug("run: rx time=%.1f night=%i" % (timestamp, nightstamp))

                        self.schedulerDriver.update_time(self.topicTime.timestamp)

                        waitstate = True
                        laststatetime = time.time()
                        while waitstate:
                            scode = self.sal.getNextSample_observatoryState(self.topicObservatoryState)
                            if scode == 0 and self.topicObservatoryState.timestamp != 0:
                                laststatetime = time.time()
                                waitstate = False
                                observatory_state = self.create_observatory_state(self.topicObservatoryState)

                                self.log.debug("run: rx state %s" % str(observatory_state))

                                self.schedulerDriver.update_internal_conditions(observatory_state)
                                target = self.schedulerDriver.select_next_target()

                                self.topicTarget.targetId = target.targetid
                                self.topicTarget.fieldId = target.fieldid
                                self.topicTarget.filter = target.filter
                                self.topicTarget.request_time = target.time
                                self.topicTarget.ra = target.ra
                                self.topicTarget.dec = target.dec
                                self.topicTarget.angle = target.ang
                                self.topicTarget.num_exposures = target.num_exp
                                for i, exptime in enumerate(target.exp_times):
                                    self.topicTarget.exposure_times[i] = int(exptime)
                                self.topicTarget.airmass = target.airmass
                                self.topicTarget.sky_brightness = target.sky_brightness
                                self.topicTarget.slew_time = target.slewtime
                                self.topicTarget.cost_bonus = target.cost_bonus
                                self.topicTarget.rank = target.rank
                                self.topicTarget.num_proposals = target.num_props
                                for i, prop_id in enumerate(target.propid_list):
                                    self.topicTarget.proposal_Ids[i] = prop_id
                                for i, prop_value in enumerate(target.value_list):
                                    self.topicTarget.proposal_values[i] = prop_value
                                for i, prop_need in enumerate(target.need_list):
                                    self.topicTarget.proposal_needs[i] = prop_need
                                for i, prop_bonus in enumerate(target.bonus_list):
                                    self.topicTarget.proposal_bonuses[i] = prop_bonus

                                prop = self.schedulerDriver.science_proposal_list[0]
                                moon_sun = prop.sky.get_moon_sun_info(target.ra_rad, target.dec_rad)
                                if moon_sun["moonRA"] is not None:
                                    self.topicTarget.moon_ra = math.degrees(moon_sun["moonRA"])
                                    self.topicTarget.moon_dec = math.degrees(moon_sun["moonDec"])
                                    self.topicTarget.moon_alt = math.degrees(moon_sun["moonAlt"])
                                    self.topicTarget.moon_az = math.degrees(moon_sun["moonAz"])
                                    self.topicTarget.moon_phase = moon_sun["moonPhase"]
                                    self.topicTarget.moon_distance = math.degrees(moon_sun["moonDist"])
                                    self.topicTarget.sun_alt = math.degrees(moon_sun["sunAlt"])
                                    self.topicTarget.sun_az = math.degrees(moon_sun["sunAz"])
                                    self.topicTarget.sun_ra = math.degrees(moon_sun["sunRA"])
                                    self.topicTarget.sun_dec = math.degrees(moon_sun["sunDec"])
                                    self.topicTarget.sun_elong = math.degrees(moon_sun["sunEclipLon"])

                                self.sal.putSample_target(self.topicTarget)
                                self.log.debug("run: tx target %s", str(target))

                                waitobservation = True
                                lastobstime = time.time()
                                while waitobservation:
                                    scode = self.sal.getNextSample_observation(self.topicObservation)
                                    if scode == 0 and self.topicObservation.targetId != 0:
                                        lastobstime = time.time()
                                        meascount += 1
                                        visitcount += 1
                                        if self.topicTarget.targetId == self.topicObservation.targetId:
                                            synccount += 1

                                            observation = self.create_observation(self.topicObservation)
                                            self.log.debug("run: rx observation %s", str(observation))
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
                                        self.log.log(TRACE, "run: t=%f lastobstime=%f" % (to, lastobstime))

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
                                    self.log.log(TRACE, "run: t=%f laststatetime=%f" % (ts, laststatetime))

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

    def read_topic_driver_config(self, topic_driver_config):

        confdict = {}
        confdict["ranking"] = {}
        confdict["ranking"]["coadd_values"] = topic_driver_config.coadd_values
        confdict["ranking"]["time_balancing"] = topic_driver_config.time_balancing
        confdict["ranking"]["timebonus_tmax"] = topic_driver_config.timebonus_tmax
        confdict["ranking"]["timebonus_bmax"] = topic_driver_config.timebonus_bmax
        confdict["ranking"]["timebonus_slope"] = topic_driver_config.timebonus_slope
        confdict["constraints"] = {}
        confdict["constraints"]["night_boundary"] = topic_driver_config.night_boundary
        confdict["constraints"]["ignore_sky_brightness"] = topic_driver_config.ignore_sky_brightness
        confdict["constraints"]["ignore_airmass"] = topic_driver_config.ignore_airmass
        confdict["constraints"]["ignore_clouds"] = topic_driver_config.ignore_clouds
        confdict["constraints"]["ignore_seeing"] = topic_driver_config.ignore_seeing

        return confdict

    def read_topic_location_config(self, topic_location_config):

        confdict = {}
        confdict["obs_site"] = {}
        confdict["obs_site"]["name"] = topic_location_config.name
        confdict["obs_site"]["latitude"] = topic_location_config.latitude
        confdict["obs_site"]["longitude"] = topic_location_config.longitude
        confdict["obs_site"]["height"] = topic_location_config.height

        return confdict

    def read_topic_telescope_config(self, topic_telescope_config):

        confdict = {}
        confdict["telescope"] = {}
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitude_minpos
        confdict["telescope"]["altitude_maxpos"] = topic_telescope_config.altitude_maxpos
        confdict["telescope"]["azimuth_minpos"] = topic_telescope_config.azimuth_minpos
        confdict["telescope"]["azimuth_maxpos"] = topic_telescope_config.azimuth_maxpos
        confdict["telescope"]["altitude_maxspeed"] = topic_telescope_config.altitude_maxspeed
        confdict["telescope"]["altitude_accel"] = topic_telescope_config.altitude_accel
        confdict["telescope"]["altitude_decel"] = topic_telescope_config.altitude_decel
        confdict["telescope"]["azimuth_maxspeed"] = topic_telescope_config.azimuth_maxspeed
        confdict["telescope"]["azimuth_accel"] = topic_telescope_config.azimuth_accel
        confdict["telescope"]["azimuth_decel"] = topic_telescope_config.azimuth_decel
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitude_minpos
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitude_minpos
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitude_minpos
        confdict["telescope"]["settle_time"] = topic_telescope_config.settle_time

        return confdict

    def read_topic_dome_config(self, topic_dome_config):

        confdict = {}
        confdict["dome"] = {}
        confdict["dome"]["altitude_maxspeed"] = topic_dome_config.altitude_maxspeed
        confdict["dome"]["altitude_accel"] = topic_dome_config.altitude_accel
        confdict["dome"]["altitude_decel"] = topic_dome_config.altitude_decel
        confdict["dome"]["azimuth_maxspeed"] = topic_dome_config.azimuth_maxspeed
        confdict["dome"]["azimuth_accel"] = topic_dome_config.azimuth_accel
        confdict["dome"]["azimuth_decel"] = topic_dome_config.azimuth_decel
        confdict["dome"]["settle_time"] = topic_dome_config.settle_time

        return confdict

    def read_topic_rotator_config(self, topic_rotator_config):

        confdict = {}
        confdict["rotator"] = {}
        confdict["rotator"]["minpos"] = topic_rotator_config.minpos
        confdict["rotator"]["maxpos"] = topic_rotator_config.maxpos
        confdict["rotator"]["maxspeed"] = topic_rotator_config.maxspeed
        confdict["rotator"]["accel"] = topic_rotator_config.accel
        confdict["rotator"]["decel"] = topic_rotator_config.decel
        confdict["rotator"]["filter_change_pos"] = topic_rotator_config.filter_change_pos
        confdict["rotator"]["follow_sky"] = topic_rotator_config.followsky
        confdict["rotator"]["resume_angle"] = topic_rotator_config.resume_angle

        return confdict

    def read_topic_optics_config(self, topic_optics_config):

        tel_optics_cl_alt_limit = []
        for k in range(3):
            tel_optics_cl_alt_limit.append(topic_optics_config.tel_optics_cl_alt_limit[k])
        tel_optics_cl_delay = []
        for k in range(2):
            tel_optics_cl_delay.append(topic_optics_config.tel_optics_cl_delay[k])

        confdict = {}
        confdict["optics_loop_corr"] = {}
        confdict["optics_loop_corr"]["tel_optics_ol_slope"] = topic_optics_config.tel_optics_ol_slope
        confdict["optics_loop_corr"]["tel_optics_cl_alt_limit"] = tel_optics_cl_alt_limit
        confdict["optics_loop_corr"]["tel_optics_cl_delay"] = tel_optics_cl_delay

        return confdict

    def read_topic_camera_config(self, topic_camera_config):

        confdict = {}
        confdict["camera"] = {}
        confdict["camera"]["readout_time"] = topic_camera_config.readout_time
        confdict["camera"]["shutter_time"] = topic_camera_config.shutter_time
        confdict["camera"]["filter_change_time"] = topic_camera_config.filter_change_time
        confdict["camera"]["filter_max_changes_burst_num"] = topic_camera_config.filter_max_changes_burst_num
        confdict["camera"]["filter_max_changes_burst_time"] = topic_camera_config.filter_max_changes_burst_time
        confdict["camera"]["filter_max_changes_avg_num"] = topic_camera_config.filter_max_changes_avg_num
        confdict["camera"]["filter_max_changes_avg_time"] = topic_camera_config.filter_max_changes_avg_time
        confdict["camera"]["filter_removable"] = topic_camera_config.filter_removable

        return confdict

    def read_topic_slew_config(self, topic_slew_config):

        confdict = {}
        confdict["slew"] = {}

        prereq_str = topic_slew_config.prereq_domalt
        if prereq_str != "":
            confdict["slew"]["prereq_domalt"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domalt"] = []

        prereq_str = topic_slew_config.prereq_domaz
        if prereq_str != "":
            confdict["slew"]["prereq_domaz"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domaz"] = []

        prereq_str = topic_slew_config.prereq_domazsettle
        if prereq_str != "":
            confdict["slew"]["prereq_domazsettle"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domazsettle"] = []

        prereq_str = topic_slew_config.prereq_telalt
        if prereq_str != "":
            confdict["slew"]["prereq_telalt"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telalt"] = []

        prereq_str = topic_slew_config.prereq_telaz
        if prereq_str != "":
            confdict["slew"]["prereq_telaz"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telaz"] = []

        prereq_str = topic_slew_config.prereq_telopticsopenloop
        if prereq_str != "":
            confdict["slew"]["prereq_telopticsopenloop"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telopticsopenloop"] = []

        prereq_str = topic_slew_config.prereq_telopticsclosedloop
        if prereq_str != "":
            confdict["slew"]["prereq_telopticsclosedloop"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telopticsclosedloop"] = []

        prereq_str = topic_slew_config.prereq_telsettle
        if prereq_str != "":
            confdict["slew"]["prereq_telsettle"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telsettle"] = []

        prereq_str = topic_slew_config.prereq_telrot
        if prereq_str != "":
            confdict["slew"]["prereq_telrot"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telrot"] = []

        prereq_str = topic_slew_config.prereq_filter
        if prereq_str != "":
            confdict["slew"]["prereq_filter"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_filter"] = []

        prereq_str = topic_slew_config.prereq_exposures
        if prereq_str != "":
            confdict["slew"]["prereq_exposures"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_exposures"] = []

        prereq_str = topic_slew_config.prereq_readout
        if prereq_str != "":
            confdict["slew"]["prereq_readout"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_readout"] = []

        return confdict

    def read_topic_park_config(self, topic_park_config):

        confdict = {}
        confdict["park"] = {}
        confdict["park"]["telescope_altitude"] = topic_park_config.telescope_altitude
        confdict["park"]["telescope_azimuth"] = topic_park_config.telescope_azimuth
        confdict["park"]["telescope_rotator"] = topic_park_config.telescope_rotator
        confdict["park"]["dome_altitude"] = topic_park_config.dome_altitude
        confdict["park"]["dome_azimuth"] = topic_park_config.dome_azimuth
        confdict["park"]["filter_position"] = topic_park_config.filter_position

        return confdict

    def read_topic_area_prop_config(self, topic_areapropconf):

        confdict = {}

        name = topic_areapropconf.name
        prop_id = topic_areapropconf.prop_id

        confdict["sky_nightly_bounds"] = {}
        confdict["sky_nightly_bounds"]["twilight_boundary"] = topic_areapropconf.twilight_boundary
        confdict["sky_nightly_bounds"]["delta_lst"] = topic_areapropconf.delta_lst

        confdict["constraints"] = {}
        confdict["constraints"]["max_airmass"] = topic_areapropconf.max_airmass

        confdict["sky_region"] = {}
        num_region_selections = topic_areapropconf.num_region_selections
        region_types = topic_areapropconf.region_types
        if region_types == "":
            region_types_list = []
        else:
            region_types_list = region_types.split(",")

        region_list = []
        for k in range(num_region_selections):
            region_minimum = topic_areapropconf.region_minimums[k]
            region_maximum = topic_areapropconf.region_maximums[k]
            region_bound = topic_areapropconf.region_bounds[k]

            region = (region_types_list[k], region_minimum, region_maximum, region_bound)
            region_list.append(region)
        region_combiners = topic_areapropconf.region_combiners
        if region_combiners == "":
            region_combiners_list = []
        else:
            region_combiners_list = region_combiners.split(",")
        confdict["sky_region"]["cuts"] = region_list
        confdict["sky_region"]["combiners"] = region_combiners_list

        confdict["sky_exclusions"] = {}
        num_exclusion_selections = topic_areapropconf.num_exclusion_selections
        exclusion_types = topic_areapropconf.exclusion_types
        if exclusion_types == "":
            exclusion_types_list = []
        else:
            exclusion_types_list = exclusion_types.split(",")
        exclusion_list = []
        for k in range(num_exclusion_selections):
            exclusion_minimum = topic_areapropconf.exclusion_minimums[k]
            exclusion_maximum = topic_areapropconf.exclusion_maximums[k]
            exclusion_bound = topic_areapropconf.exclusion_bounds[k]

            exclusion = (exclusion_types_list[k], exclusion_minimum,
                         exclusion_maximum, exclusion_bound)
            exclusion_list.append(exclusion)

        confdict["sky_exclusions"]["cuts"] = exclusion_list
        dec_window = topic_areapropconf.dec_window
        confdict["sky_exclusions"]["dec_window"] = dec_window

        num_filters = topic_areapropconf.num_filters
        filter_names = topic_areapropconf.filter_names
        filter_list = filter_names.split(",")
        exp_index = 0
        for k in range(num_filters):
            filter = filter_list[k]
            filter_section = "filter_%s" % filter
            confdict[filter_section] = {}
            confdict[filter_section]["visits"] = topic_areapropconf.num_visits[k]
            confdict[filter_section]["min_brig"] = \
                topic_areapropconf.bright_limit[k]
            confdict[filter_section]["max_brig"] = topic_areapropconf.dark_limit[k]
            confdict[filter_section]["max_seeing"] = topic_areapropconf.max_seeing[k]
            num_exp = topic_areapropconf.num_filter_exposures[k]
            exp_times_list = []
            for n in range(num_exp):
                exp_times_list.append(topic_areapropconf.exposures[exp_index])
                exp_index += 1
            confdict[filter_section]["exp_times"] = exp_times_list

        confdict["scheduling"] = {}
        max_num_targets = topic_areapropconf.max_num_targets
        accept_serendipity = topic_areapropconf.accept_serendipity
        accept_consecutive_visits = topic_areapropconf.accept_consecutive_visits
        confdict["scheduling"]["max_num_targets"] = max_num_targets
        confdict["scheduling"]["accept_serendipity"] = accept_serendipity
        confdict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits

        return confdict

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
