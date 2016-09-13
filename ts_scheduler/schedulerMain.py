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

        self.schedulerDriver = Driver()

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
                    self.schedulerDriver.configure_duration(survey_duration)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: scheduler config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_driverConfig(self.topic_driverConfig)
                if (scode == 0 and self.topic_driverConfig.timebonus_tmax > 0):
                    lastconfigtime = time.time()

                    coadd_values = self.topic_driverConfig.coadd_values
                    time_balancing = self.topic_driverConfig.time_balancing
                    timebonus_tmax = self.topic_driverConfig.timebonus_tmax
                    timebonus_bmax = self.topic_driverConfig.timebonus_bmax
                    timebonus_slope = self.topic_driverConfig.timebonus_slope
                    night_boundary = self.topic_driverConfig.night_boundary

                    config_dict = {}
                    config_dict["ranking"] = {}
                    config_dict["ranking"]["coadd_values"] = coadd_values
                    config_dict["ranking"]["time_balancing"] = time_balancing
                    config_dict["ranking"]["timebonus_tmax"] = timebonus_tmax
                    config_dict["ranking"]["timebonus_bmax"] = timebonus_bmax
                    config_dict["ranking"]["timebonus_slope"] = timebonus_slope
                    config_dict["survey"] = {}
                    config_dict["survey"]["night_boundary"] = night_boundary

                    self.log.info("run: rx driver config=%s" % (config_dict))
                    self.schedulerDriver.configure(config_dict)

                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: driver config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_obsSiteConfig(self.topic_obsSiteConfig)
                if (scode == 0 and self.topic_obsSiteConfig.name != ""):
                    lastconfigtime = time.time()
                    latitude = self.topic_obsSiteConfig.latitude
                    longitude = self.topic_obsSiteConfig.longitude
                    height = self.topic_obsSiteConfig.height
                    self.log.info("run: rx site config latitude=%.3f longitude=%.3f height=%.0f" %
                                  (latitude, longitude, height))
                    self.schedulerDriver.configure_location(math.radians(latitude),
                                                            math.radians(longitude),
                                                            height)
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
                if (scode == 0 and self.topic_rotatorConfig.maxspeed >= 0):
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
                                  (minpos, maxpos, follow_sky, resume_angle))
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
                        self.log.info("run: rotator config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_cameraConfig(self.topic_cameraConfig)
                if (scode == 0 and self.topic_cameraConfig.readout_time > 0):
                    lastconfigtime = time.time()

                    config_camera_dict = self.read_topic_cameraConfig(self.topic_cameraConfig)

                    self.log.info("run: rx camera config=%s" % (config_camera_dict))
                    self.schedulerDriver.configure_camera(config_camera_dict)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: camera config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_slewConfig(self.topic_slewConfig)
                if (scode == 0 and self.topic_slewConfig.prereq_exposures != ""):
                    lastconfigtime = time.time()

                    prereq_dict = {}

                    prereq_str = self.topic_slewConfig.prereq_domalt
                    if prereq_str != "":
                        prereq_dict["domalt"] = prereq_str.split(",")
                    else:
                        prereq_dict["domalt"] = []

                    prereq_str = self.topic_slewConfig.prereq_domaz
                    if prereq_str != "":
                        prereq_dict["domaz"] = prereq_str.split(",")
                    else:
                        prereq_dict["domaz"] = []

                    prereq_str = self.topic_slewConfig.prereq_domazsettle
                    if prereq_str != "":
                        prereq_dict["domazsettle"] = prereq_str.split(",")
                    else:
                        prereq_dict["domazsettle"] = []

                    prereq_str = self.topic_slewConfig.prereq_telalt
                    if prereq_str != "":
                        prereq_dict["telalt"] = prereq_str.split(",")
                    else:
                        prereq_dict["telalt"] = []

                    prereq_str = self.topic_slewConfig.prereq_telaz
                    if prereq_str != "":
                        prereq_dict["telaz"] = prereq_str.split(",")
                    else:
                        prereq_dict["telaz"] = []

                    prereq_str = self.topic_slewConfig.prereq_telopticsopenloop
                    if prereq_str != "":
                        prereq_dict["telopticsopenloop"] = prereq_str.split(",")
                    else:
                        prereq_dict["telopticsopenloop"] = []

                    prereq_str = self.topic_slewConfig.prereq_telopticsclosedloop
                    if prereq_str != "":
                        prereq_dict["telopticsclosedloop"] = prereq_str.split(",")
                    else:
                        prereq_dict["telopticsclosedloop"] = []

                    prereq_str = self.topic_slewConfig.prereq_telsettle
                    if prereq_str != "":
                        prereq_dict["telsettle"] = prereq_str.split(",")
                    else:
                        prereq_dict["telsettle"] = []

                    prereq_str = self.topic_slewConfig.prereq_telrot
                    if prereq_str != "":
                        prereq_dict["telrot"] = prereq_str.split(",")
                    else:
                        prereq_dict["telrot"] = []

                    prereq_str = self.topic_slewConfig.prereq_filter
                    if prereq_str != "":
                        prereq_dict["filter"] = prereq_str.split(",")
                    else:
                        prereq_dict["filter"] = []

                    prereq_str = self.topic_slewConfig.prereq_exposures
                    if prereq_str != "":
                        prereq_dict["exposures"] = prereq_str.split(",")
                    else:
                        prereq_dict["exposures"] = []

                    prereq_str = self.topic_slewConfig.prereq_readout
                    if prereq_str != "":
                        prereq_dict["readout"] = prereq_str.split(",")
                    else:
                        prereq_dict["readout"] = []

                    self.log.info("run: rx slew config prereq_dict=%s" %
                                  (prereq_dict))
                    self.schedulerDriver.configure_slew(prereq_dict)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: slew config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_opticsLoopCorrConfig(self.topic_opticsConfig)
                if (scode == 0 and self.topic_opticsConfig.tel_optics_ol_slope > 0):
                    lastconfigtime = time.time()

                    tel_optics_ol_slope = self.topic_opticsConfig.tel_optics_ol_slope
                    tel_optics_cl_alt_limit = []
                    for k in range(3):
                        tel_optics_cl_alt_limit.append(self.topic_opticsConfig.tel_optics_cl_alt_limit[k])

                    tel_optics_cl_delay = []
                    for k in range(2):
                        tel_optics_cl_delay.append(self.topic_opticsConfig.tel_optics_cl_delay[k])

                    self.log.info("run: rx optics config tel_optics_ol_slope=%.3f "
                                  "tel_optics_cl_alt_limit=%s "
                                  "tel_optics_cl_delay=%s" %
                                  (tel_optics_ol_slope, tel_optics_cl_alt_limit, tel_optics_cl_delay))
                    self.schedulerDriver.configure_optics(tel_optics_ol_slope,
                                                          tel_optics_cl_alt_limit,
                                                          tel_optics_cl_delay)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: optics config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_parkConfig(self.topic_parkConfig)
                if (scode == 0 and self.topic_parkConfig.telescope_altitude > 0):
                    lastconfigtime = time.time()

                    telescope_altitude = self.topic_parkConfig.telescope_altitude
                    telescope_azimuth = self.topic_parkConfig.telescope_azimuth
                    telescope_rotator = self.topic_parkConfig.telescope_rotator
                    dome_altitude = self.topic_parkConfig.dome_altitude
                    dome_azimuth = self.topic_parkConfig.dome_azimuth
                    filter_position = self.topic_parkConfig.filter_position

                    self.log.info("run: rx park config "
                                  "telescope_altitude=%.3f "
                                  "telescope_azimuth=%.3f "
                                  "telescope_rotator=%.3f"
                                  "dome_altitude=%.3f"
                                  "dome_azimuth=%.3f"
                                  "filter_position=%s" %
                                  (telescope_altitude,
                                   telescope_azimuth,
                                   telescope_rotator,
                                   dome_altitude,
                                   dome_azimuth,
                                   filter_position))
                    self.schedulerDriver.configure_park(telescope_altitude,
                                                        telescope_azimuth,
                                                        telescope_rotator,
                                                        dome_altitude,
                                                        dome_azimuth,
                                                        filter_position)
                    waitconfig = False

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.info("run: optics config timeout")

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_areaDistPropConfig(self.topic_areaDistPropConfig)
                if (scode == 0 and self.topic_areaDistPropConfig.name != ""):
                    lastconfigtime = time.time()

                    config_dict = {}

                    name = self.topic_areaDistPropConfig.name
                    prop_id = self.topic_areaDistPropConfig.prop_id

                    config_dict["sky_nightly_bounds"] = {}
                    twilight_boundary = self.topic_areaDistPropConfig.twilight_boundary
                    delta_lst = self.topic_areaDistPropConfig.delta_lst
                    config_dict["sky_nightly_bounds"]["twilight_boundary"] = twilight_boundary
                    config_dict["sky_nightly_bounds"]["delta_lst"] = delta_lst

                    config_dict["constraints"] = {}
                    max_airmass = self.topic_areaDistPropConfig.max_airmass
                    config_dict["constraints"]["max_airmass"] = max_airmass

                    config_dict["sky_region"] = {}
                    num_region_selections = self.topic_areaDistPropConfig.num_region_selections
                    region_types = self.topic_areaDistPropConfig.region_types
                    if region_types == "":
                        region_types_list = []
                    else:
                        region_types_list = region_types.split(",")
                    region_list = []
                    for k in range(num_region_selections):
                        region_minimum = self.topic_areaDistPropConfig.region_minimums[k]
                        region_maximum = self.topic_areaDistPropConfig.region_maximums[k]
                        region_bound = self.topic_areaDistPropConfig.region_bounds[k]

                        region = (region_types_list[k], region_minimum, region_maximum, region_bound)
                        region_list.append(region)
                    region_combiners = self.topic_areaDistPropConfig.region_combiners
                    if region_combiners == "":
                        region_combiners_list = []
                    else:
                        region_combiners_list = region_combiners.split(",")
                    config_dict["sky_region"]["cuts"] = region_list
                    config_dict["sky_region"]["combiners"] = region_combiners_list

                    config_dict["sky_exclusions"] = {}
                    num_exclusion_selections = self.topic_areaDistPropConfig.num_exclusion_selections
                    exclusion_types = self.topic_areaDistPropConfig.exclusion_types
                    if exclusion_types == "":
                        exclusion_types_list = []
                    else:
                        exclusion_types_list = exclusion_types.split(",")
                    exclusion_list = []
                    for k in range(num_exclusion_selections):
                        exclusion_minimum = self.topic_areaDistPropConfig.exclusion_minimums[k]
                        exclusion_maximum = self.topic_areaDistPropConfig.exclusion_maximums[k]
                        exclusion_bound = self.topic_areaDistPropConfig.exclusion_bounds[k]

                        exclusion = (exclusion_types_list[k], exclusion_minimum,
                                     exclusion_maximum, exclusion_bound)
                        exclusion_list.append(exclusion)
                    config_dict["sky_exclusions"]["cuts"] = exclusion_list
                    dec_window = self.topic_areaDistPropConfig.dec_window
                    config_dict["sky_exclusions"]["dec_window"] = dec_window

                    num_filters = self.topic_areaDistPropConfig.num_filters
                    filter_names = self.topic_areaDistPropConfig.filter_names
                    filter_list = filter_names.split(",")
                    exp_index = 0
                    for k in range(num_filters):
                        filter = filter_list[k]
                        filter_section = "filter_%s" % filter
                        config_dict[filter_section] = {}
                        config_dict[filter_section]["visits"] = self.topic_areaDistPropConfig.num_visits[k]
                        config_dict[filter_section]["min_brig"] = self.topic_areaDistPropConfig.bright_limit[k]
                        config_dict[filter_section]["max_brig"] = self.topic_areaDistPropConfig.dark_limit[k]
                        config_dict[filter_section]["max_seeing"] = self.topic_areaDistPropConfig.max_seeing[k]
                        num_exp = self.topic_areaDistPropConfig.num_filter_exposures[k]
                        exp_times_list = []
                        for n in range(num_exp):
                            exp_times_list.append(self.topic_areaDistPropConfig.exposures[exp_index])
                            exp_index += 1
                        config_dict[filter_section]["exp_times"] = exp_times_list

                    config_dict["scheduling"] = {}
                    max_num_targets = self.topic_areaDistPropConfig.max_num_targets
                    accept_serendipity = self.topic_areaDistPropConfig.accept_serendipity
                    accept_consecutive_visits = self.topic_areaDistPropConfig.accept_consecutive_visits
                    config_dict["scheduling"]["max_num_targets"] = max_num_targets
                    config_dict["scheduling"]["accept_serendipity"] = accept_serendipity
                    config_dict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits

                    self.log.info("run: rx areaprop config "
                                  "prop_id=%i "
                                  "name=%s "
                                  "config_dict=%s " %
                                  (prop_id, name, config_dict))

                    self.schedulerDriver.configure_area_proposal(prop_id,
                                                                 name,
                                                                 config_dict)

                    waitconfig = True
                else:
                    tf = time.time()
                    if self.topic_areaDistPropConfig.name == "":
                        waitconfig = False
                        self.log.info("run: area prop config end")

                    if tf - lastconfigtime > 10.0:
                        waitconfig = False
                        self.log.info("run: area prop config timeout")

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

    def read_topic_cameraConfig(self, topic_cameraConfig):

        config_camera_dict = {}

        config_camera_dict["readout_time"] = topic_cameraConfig.readout_time
        config_camera_dict["shutter_time"] = topic_cameraConfig.shutter_time
        config_camera_dict["filter_change_time"] = topic_cameraConfig.filter_change_time
        config_camera_dict["filter_max_changes_burst_num"] = topic_cameraConfig.filter_max_changes_burst_num
        config_camera_dict["filter_max_changes_burst_time"] = topic_cameraConfig.filter_max_changes_burst_time
        config_camera_dict["filter_max_changes_avg_num"] = topic_cameraConfig.filter_max_changes_avg_num
        config_camera_dict["filter_max_changes_avg_time"] = topic_cameraConfig.filter_max_changes_avg_time
        config_camera_dict["filter_removable"] = topic_cameraConfig.filter_removable

        return config_camera_dict

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
