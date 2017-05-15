import logging
import logging.handlers
import sys
import time
import math
import numpy

from SALPY_scheduler import SAL_scheduler
from SALPY_scheduler import scheduler_timeHandlerC
from SALPY_scheduler import scheduler_observatoryStateC
from SALPY_scheduler import scheduler_cloudC
from SALPY_scheduler import scheduler_seeingC
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
from SALPY_scheduler import scheduler_generalPropConfigC
from SALPY_scheduler import scheduler_sequencePropConfigC
from SALPY_scheduler import scheduler_filterSwapC
from SALPY_scheduler import scheduler_interestedProposalC

from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.setup import TRACE, EXTENSIVE
from lsst.ts.scheduler.kernel import read_conf_file, conf_file_path
from lsst.ts.scheduler import Driver

__all__ = ["Main"]

class Main(object):

    def __init__(self, options):
        self.log = logging.getLogger("schedulerMain")

        main_confdict = read_conf_file(conf_file_path(__name__, "conf", "scheduler", "main.conf"))
        self.measinterval = main_confdict['log']['rate_meas_interval']

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)
        self.sal_sleeper = 0.1
        self.main_loop_timeouts = options.timeout

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
        self.topic_areaDistPropConfig = scheduler_generalPropConfigC()
        self.topic_sequencePropConfig = scheduler_sequencePropConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservatoryState = scheduler_observatoryStateC()
        self.topic_cloud = scheduler_cloudC()
        self.topic_seeing = scheduler_seeingC()
        self.topicObservation = scheduler_observationC()
        self.topicField = scheduler_fieldC()
        self.topicTarget = scheduler_targetC()
        self.topicFilterSwap = scheduler_filterSwapC()
        self.tInterestedProposal = scheduler_interestedProposalC()

        self.schedulerDriver = Driver()

    def sal_init(self):
        self.log.info("Starting pub/sub initialization")
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
        self.sal.salTelemetrySub("scheduler_generalPropConfig")
        self.sal.salTelemetrySub("scheduler_sequencePropConfig")
        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observatoryState")
        self.sal.salTelemetrySub("scheduler_cloud")
        self.sal.salTelemetrySub("scheduler_seeing")
        self.sal.salTelemetrySub("scheduler_observation")
        self.sal.salTelemetryPub("scheduler_field")
        self.sal.salTelemetryPub("scheduler_target")
        self.sal.salTelemetryPub("scheduler_filterSwap")
        self.sal.salTelemetryPub("scheduler_interestedProposal")
        self.log.info("Finished pub/sub initialization")

    def run(self):

        self.log.info("run")

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
                    if (tf - lastconfigtime > 20.0):
                        self.log.info("run: scheduler config timeout")
                        config_file = conf_file_path(__name__, "conf", "survey", "survey.conf")
                        config_dict = read_conf_file(config_file)
                        survey_duration = config_dict["survey"]["survey_duration"]
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_duration(survey_duration)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_driverConfig(self.topic_driverConfig)
                if (scode == 0 and self.topic_driverConfig.timecost_time_max > 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_driver_config(self.topic_driverConfig)
                    self.log.info("run: rx driver config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: driver config timeout")
                        config_file = conf_file_path(__name__, "conf", "scheduler", "driver.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_obsSiteConfig(self.topic_obsSiteConfig)
                if (scode == 0 and self.topic_obsSiteConfig.name != ""):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_location_config(self.topic_obsSiteConfig)
                    self.log.info("run: rx site config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: site config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "site.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_location(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_telescopeConfig(self.topic_telescopeConfig)
                if (scode == 0 and self.topic_telescopeConfig.altitude_minpos >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_telescope_config(self.topic_telescopeConfig)
                    self.log.info("run: rx telescope config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: telescope config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_telescope(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_domeConfig(self.topic_domeConfig)
                if (scode == 0 and self.topic_domeConfig.altitude_maxspeed >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_dome_config(self.topic_domeConfig)
                    self.log.info("run: rx dome config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: dome config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_dome(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_rotatorConfig(self.topic_rotatorConfig)
                if (scode == 0 and self.topic_rotatorConfig.maxspeed >= 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_rotator_config(self.topic_rotatorConfig)
                    self.log.info("run: rx rotator config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: rotator config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_rotator(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_cameraConfig(self.topic_cameraConfig)
                if (scode == 0 and self.topic_cameraConfig.readout_time > 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_camera_config(self.topic_cameraConfig)
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
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_camera(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_slewConfig(self.topic_slewConfig)
                if (scode == 0 and self.topic_slewConfig.prereq_exposures != ""):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_slew_config(self.topic_slewConfig)
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
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_slew(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_opticsLoopCorrConfig(self.topic_opticsConfig)
                if (scode == 0 and self.topic_opticsConfig.tel_optics_ol_slope > 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_optics_config(self.topic_opticsConfig)
                    self.log.info("run: rx optics config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: optics config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_optics(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_parkConfig(self.topic_parkConfig)
                if (scode == 0 and self.topic_parkConfig.telescope_altitude > 0):
                    lastconfigtime = time.time()
                    config_dict = self.rtopic_park_config(self.topic_parkConfig)
                    self.log.info("run: rx park config=%s" % (config_dict))
                    waitconfig = False
                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        self.log.info("run: optics config timeout")
                        config_file = conf_file_path(__name__, "conf", "system", "observatory_model.conf")
                        config_dict = read_conf_file(config_file)
                        waitconfig = False
                    time.sleep(self.sal_sleeper)
            self.schedulerDriver.configure_park(config_dict)

            waitconfig = True
            lastconfigtime = time.time()
            config_dict = None
            good_config = False
            while waitconfig:
                scode = self.sal.getNextSample_generalPropConfig(self.topic_areaDistPropConfig)
                if (scode == 0 and self.topic_areaDistPropConfig.name != ""):
                    lastconfigtime = time.time()
                    name = self.topic_areaDistPropConfig.name
                    prop_id = self.topic_areaDistPropConfig.prop_id
                    if (prop_id == -1 and name == "NULL"):
                        self.log.info("run: area prop config null")
                        waitconfig = False
                    else:
                        config_dict = self.rtopic_area_prop_config(self.topic_areaDistPropConfig)
                        self.log.info("run: rx area prop id=%i name=%s config=%s" % (prop_id, name,
                                                                                     config_dict))
                        self.schedulerDriver.create_area_proposal(prop_id, name, config_dict)
                        waitconfig = True
                    good_config = True
                else:
                    tf = time.time()
                    if tf - lastconfigtime > 10.0:
                        self.log.info("run: area prop config timeout")
                        """
                        if not good_config:
                            area_proposals = ["north_ecliptic_spur.conf", "south_celestial_pole.conf",
                                              "wide_fast_deep.conf", "galactic_plane.conf"]
                            for prop_id, prop_config in enumerate(area_proposals):
                                config_file = conf_file_path(__name__, "conf", "survey", prop_config)
                                config_dict = read_conf_file(config_file)
                                name = "".join([x.capitalize() for x in prop_config.split('.')[0].split('_')])
                                self.schedulerDriver.create_area_proposal(prop_id, name, config_dict)
                        """
                        waitconfig = False
                    time.sleep(self.sal_sleeper)

            waitconfig = True
            lastconfigtime = time.time()
            config_dict = None
            good_config = False
            while waitconfig:
                scode = self.sal.getNextSample_sequencePropConfig(self.topic_sequencePropConfig)
                if (scode == 0 and self.topic_sequencePropConfig.name != ""):
                    lastconfigtime = time.time()
                    name = self.topic_sequencePropConfig.name
                    prop_id = self.topic_sequencePropConfig.prop_id
                    if (prop_id == -1 and name == "NULL"):
                        self.log.info("run: seq prop config null")
                        waitconfig = False
                    else:
                        config_dict = self.rtopic_seq_prop_config(self.topic_sequencePropConfig)
                        self.log.info("run: rx seq prop id=%i name=%s config=%s" % (prop_id, name,
                                                                                    config_dict))
                        self.schedulerDriver.create_sequence_proposal(prop_id, name, config_dict)
                        waitconfig = True
                    good_config = True
                else:
                    tf = time.time()
                    if tf - lastconfigtime > 10.0:
                        self.log.info("run: seq prop config timeout")
                        """
                        if not good_config:
                            seq_proposals = ["deep_drilling_cosmology1.conf"]
                            for prop_id, prop_config in enumerate(seq_proposals):
                                config_file = conf_file_path(__name__, "conf", "survey", prop_config)
                                config_dict = read_conf_file(config_file)
                                name = "".join([x.capitalize() for x in prop_config.split('.')[0].split('_')])
                                self.schedulerDriver.create_sequence_proposal(prop_id, name, config_dict)
                        """
                        waitconfig = False
                    time.sleep(self.sal_sleeper)

            field_dict = self.schedulerDriver.get_fields_dict()
            if len(field_dict) > 0:
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)
                for fieldid in field_dict:
                    self.topicField.ID = field_dict[fieldid].fieldid
                    self.topicField.ra = math.degrees(field_dict[fieldid].ra_rad)
                    self.topicField.dec = math.degrees(field_dict[fieldid].dec_rad)
                    self.topicField.gl = math.degrees(field_dict[fieldid].gl_rad)
                    self.topicField.gb = math.degrees(field_dict[fieldid].gb_rad)
                    self.topicField.el = math.degrees(field_dict[fieldid].el_rad)
                    self.topicField.eb = math.degrees(field_dict[fieldid].eb_rad)
                    self.topicField.fov = math.degrees(field_dict[fieldid].fov_rad)
                    self.sal.putSample_field(self.topicField)
                    self.log.log(EXTENSIVE, "run: tx field %s" % (field_dict[fieldid]))
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)

            waittime = True
            lasttimetime = time.time()
            while waittime:
                scode = self.sal.getNextSample_timeHandler(self.topicTime)
                if scode == 0 and self.topicTime.timestamp != 0:
                    lasttimetime = time.time()
                    nightstamp = self.topicTime.night
                    is_down = self.topicTime.is_down
                    down_duration = self.topicTime.down_duration
                    self.log.log(EXTENSIVE, "run: rx time=%.6f night=%i is_down=%s down_duration=%.1f" %
                                 (self.topicTime.timestamp, nightstamp, is_down, down_duration))
                    if self.topicTime.timestamp > timestamp:
                        timestamp = self.topicTime.timestamp
                        isnight = self.schedulerDriver.update_time(timestamp, nightstamp)
                        if isnight:
                            if is_down:
                                self.log.info("run: downtime duration=%.1f" % (down_duration))
                                waitstate = True
                            else:
                                waitstate = True
                        else:
                            (needswap, filter2unmount, filter2mount) = \
                                self.schedulerDriver.get_need_filter_swap()

                            self.topicFilterSwap.need_swap = needswap
                            self.topicFilterSwap.filter_to_unmount = filter2unmount
                            self.sal.putSample_filterSwap(self.topicFilterSwap)
                            self.log.info("run: tx filter swap %s %s" % (needswap, filter2unmount))
                            waitstate = False

                        laststatetime = time.time()
                        while waitstate:
                            scode = self.sal.getNextSample_observatoryState(self.topicObservatoryState)
                            if scode == 0 and self.topicObservatoryState.timestamp != 0:
                                laststatetime = time.time()
                                waitstate = False
                                observatory_state = self.rtopic_observatory_state(self.topicObservatoryState)

                                self.log.log(EXTENSIVE, "run: rx state %s" % str(observatory_state))

                                self.schedulerDriver.update_internal_conditions(observatory_state, nightstamp)

                                if is_down:
                                    waitobservation = False
                                else:
                                    waitcloud = True
                                    lastcloudtime = time.time()
                                    while waitcloud:
                                        scode = self.sal.getNextSample_cloud(self.topic_cloud)
                                        if scode == 0 and self.topic_cloud.timestamp != 0:
                                            lastcloudtime = time.time()
                                            waitcloud = False
                                            cloud = self.topic_cloud.cloud
                                        else:
                                            tf = time.time()
                                            if (tf - lastcloudtime > 10.0):
                                                self.log.info("run: cloud timeout")
                                                waitcloud = False
                                                cloud = 0.0

                                    waitseeing = True
                                    lastseeingtime = time.time()
                                    while waitseeing:
                                        scode = self.sal.getNextSample_seeing(self.topic_seeing)
                                        if scode == 0 and self.topic_seeing.timestamp != 0:
                                            lastseeingtime = time.time()
                                            waitseeing = False
                                            seeing = self.topic_seeing.seeing
                                        else:
                                            tf = time.time()
                                            if (tf - lastseeingtime > 10.0):
                                                self.log.info("run: seeing timeout")
                                                waitseeing = False
                                                seeing = 0.0

                                    self.log.log(EXTENSIVE, "run: rx conditions cloud=%.2f seeing=%.2f" %
                                                 (cloud, seeing))
                                    self.schedulerDriver.update_external_conditions(cloud, seeing)

                                    target = self.schedulerDriver.select_next_target()

                                    self.wtopic_target(self.topicTarget, target)

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

                                            obs = self.rtopic_observation(self.topicObservation)
                                            self.log.log(EXTENSIVE, "run: rx observation %s", str(obs))
                                            target_list = self.schedulerDriver.register_observation(obs)
                                            s = self.wtopic_interestedProposal(self.tInterestedProposal,
                                                                               self.topicObservation.targetId,
                                                                               target_list)
                                            self.sal.putSample_interestedProposal(self.tInterestedProposal)
                                            self.log.log(EXTENSIVE, "run: tx interested %s", s)
                                            waitobservation = False
                                        else:
                                            self.log.warning("run: rx unsync observation Id=%i "
                                                             "for target Id=%i" %
                                                             (self.topicObservation.targetId,
                                                              self.topicTarget.targetId))
                                    else:
                                        to = time.time()
                                        if (to - lastobstime > self.main_loop_timeouts):
                                            waitobservation = False
                                            self.log.debug("run: observation timeout")
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
                                if (ts - laststatetime > self.main_loop_timeouts):
                                    waitstate = False
                                    self.log.debug("run: state timeout")
                                    self.log.log(TRACE, "run: t=%f laststatetime=%f" % (ts, laststatetime))

                    else:
                        self.log.error("run: rx non progressive time previous=%f new=%f" %
                                       (timestamp, self.topicTime.timestamp))
                        waittime = False

                else:
                    tc = time.time()
                    if (tc - lasttimetime) > self.main_loop_timeouts:
                        self.log.debug("run: time timeout")
                        waittime = False

                newtime = time.time()
                deltatime = newtime - meastime
                if deltatime >= self.measinterval:
                    rate = float(meascount) / deltatime
                    self.log.info("run: rxe %.0f visits/sec total=%i visits sync=%i" % (rate, visitcount,
                                                                                        synccount))
                    meastime = newtime
                    meascount = 0

        except:
            self.log.exception("An exception was thrown in the Scheduler!")

        self.schedulerDriver.end_survey()

        self.log.info("exit")
        self.sal.salShutdown()
        sys.exit(0)

    def rtopic_driver_config(self, topic_driver_config):

        confdict = {}
        confdict["ranking"] = {}
        confdict["ranking"]["coadd_values"] = topic_driver_config.coadd_values
        confdict["ranking"]["time_balancing"] = topic_driver_config.time_balancing
        confdict["ranking"]["timecost_time_max"] = topic_driver_config.timecost_time_max
        confdict["ranking"]["timecost_time_ref"] = topic_driver_config.timecost_time_ref
        confdict["ranking"]["timecost_cost_ref"] = topic_driver_config.timecost_cost_ref
        confdict["ranking"]["timecost_weight"] = topic_driver_config.timecost_weight
        confdict["ranking"]["filtercost_weight"] = topic_driver_config.filtercost_weight
        confdict["constraints"] = {}
        confdict["constraints"]["night_boundary"] = topic_driver_config.night_boundary
        confdict["constraints"]["ignore_sky_brightness"] = topic_driver_config.ignore_sky_brightness
        confdict["constraints"]["ignore_airmass"] = topic_driver_config.ignore_airmass
        confdict["constraints"]["ignore_clouds"] = topic_driver_config.ignore_clouds
        confdict["constraints"]["ignore_seeing"] = topic_driver_config.ignore_seeing
        confdict["darktime"] = {}
        confdict["darktime"]["new_moon_phase_threshold"] = topic_driver_config.new_moon_phase_threshold

        return confdict

    def rtopic_location_config(self, topic_location_config):

        confdict = {}
        confdict["obs_site"] = {}
        confdict["obs_site"]["name"] = topic_location_config.name
        confdict["obs_site"]["latitude"] = topic_location_config.latitude
        confdict["obs_site"]["longitude"] = topic_location_config.longitude
        confdict["obs_site"]["height"] = topic_location_config.height

        return confdict

    def rtopic_telescope_config(self, topic_telescope_config):

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

    def rtopic_dome_config(self, topic_dome_config):

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

    def rtopic_rotator_config(self, topic_rotator_config):

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

    def rtopic_optics_config(self, topic_optics_config):

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

    def rtopic_camera_config(self, topic_camera_config):

        confdict = {}
        confdict["camera"] = {}
        confdict["camera"]["readout_time"] = topic_camera_config.readout_time
        confdict["camera"]["shutter_time"] = topic_camera_config.shutter_time
        confdict["camera"]["filter_change_time"] = topic_camera_config.filter_change_time
        confdict["camera"]["filter_max_changes_burst_num"] = \
            topic_camera_config.filter_max_changes_burst_num
        confdict["camera"]["filter_max_changes_burst_time"] = \
            topic_camera_config.filter_max_changes_burst_time
        confdict["camera"]["filter_max_changes_avg_num"] = \
            topic_camera_config.filter_max_changes_avg_num
        confdict["camera"]["filter_max_changes_avg_time"] = \
            topic_camera_config.filter_max_changes_avg_time
        if topic_camera_config.filter_removable != "":
            confdict["camera"]["filter_removable"] = topic_camera_config.filter_removable.split(",")
        else:
            confdict["camera"]["filter_removable"] = []

        if topic_camera_config.filter_mounted != "":
            confdict["camera"]["filter_mounted"] = topic_camera_config.filter_mounted.split(",")
        else:
            confdict["camera"]["filter_mounted"] = []

        if topic_camera_config.filter_unmounted != "":
            confdict["camera"]["filter_unmounted"] = topic_camera_config.filter_unmounted.split(",")
        else:
            confdict["camera"]["filter_unmounted"] = []

        return confdict

    def rtopic_slew_config(self, topic_slew_config):

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

    def rtopic_park_config(self, topic_park_config):

        confdict = {}
        confdict["park"] = {}
        confdict["park"]["telescope_altitude"] = topic_park_config.telescope_altitude
        confdict["park"]["telescope_azimuth"] = topic_park_config.telescope_azimuth
        confdict["park"]["telescope_rotator"] = topic_park_config.telescope_rotator
        confdict["park"]["dome_altitude"] = topic_park_config.dome_altitude
        confdict["park"]["dome_azimuth"] = topic_park_config.dome_azimuth
        confdict["park"]["filter_position"] = topic_park_config.filter_position

        return confdict

    def rtopic_area_prop_config(self, topic_areapropconf):

        confdict = {}

        confdict["sky_nightly_bounds"] = {}
        confdict["sky_nightly_bounds"]["twilight_boundary"] = topic_areapropconf.twilight_boundary
        confdict["sky_nightly_bounds"]["delta_lst"] = topic_areapropconf.delta_lst

        confdict["constraints"] = {}
        confdict["constraints"]["max_airmass"] = topic_areapropconf.max_airmass
        confdict["constraints"]["max_cloud"] = topic_areapropconf.max_cloud
        confdict["constraints"]["min_distance_moon"] = topic_areapropconf.min_distance_moon
        confdict["constraints"]["exclude_planets"] = topic_areapropconf.exclude_planets

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

        num_time_ranges = topic_areapropconf.num_time_ranges
        if num_time_ranges:
            time_range_list = []
            selection_mappings = []
            selection_index = 0
            for k in range(num_time_ranges):
                time_range_list.append((topic_areapropconf.time_range_starts[k],
                                        topic_areapropconf.time_range_ends[k]))
                num_selection_mappings = topic_areapropconf.num_selection_mappings[k]
                selection_map = []
                for m in range(num_selection_mappings):
                    selection_map.append(topic_areapropconf.selection_mappings[selection_index])
                    selection_index += 1
                selection_mappings.append(selection_map)

            confdict["sky_region"]["time_ranges"] = time_range_list
            confdict["sky_region"]["selection_mappings"] = selection_mappings

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
            confdict[filter_section]["num_grouped_visits"] = topic_areapropconf.num_grouped_visits[k]

        confdict["scheduling"] = {}
        max_num_targets = topic_areapropconf.max_num_targets
        accept_serendipity = topic_areapropconf.accept_serendipity
        accept_consecutive_visits = topic_areapropconf.accept_consecutive_visits
        confdict["scheduling"]["max_num_targets"] = max_num_targets
        confdict["scheduling"]["accept_serendipity"] = accept_serendipity
        confdict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits
        confdict["scheduling"]["airmass_bonus"] = topic_areapropconf.airmass_bonus
        confdict["scheduling"]["hour_angle_bonus"] = topic_areapropconf.hour_angle_bonus
        confdict["scheduling"]["hour_angle_max"] = topic_areapropconf.hour_angle_max

        confdict["scheduling"]["restrict_grouped_visits"] = topic_areapropconf.restrict_grouped_visits
        confdict["scheduling"]["time_interval"] = topic_areapropconf.time_interval
        confdict["scheduling"]["time_window_start"] = topic_areapropconf.time_window_start
        confdict["scheduling"]["time_window_max"] = topic_areapropconf.time_window_max
        confdict["scheduling"]["time_window_end"] = topic_areapropconf.time_window_end
        confdict["scheduling"]["time_weight"] = topic_areapropconf.time_weight

        return confdict

    def rtopic_seq_prop_config(self, topic_seqpropconf):

        confdict = {}

        confdict["sky_nightly_bounds"] = {}
        confdict["sky_nightly_bounds"]["twilight_boundary"] = topic_seqpropconf.twilight_boundary
        confdict["sky_nightly_bounds"]["delta_lst"] = topic_seqpropconf.delta_lst

        confdict["constraints"] = {}
        confdict["constraints"]["max_airmass"] = topic_seqpropconf.max_airmass
        confdict["constraints"]["max_cloud"] = topic_seqpropconf.max_cloud
        confdict["constraints"]["min_distance_moon"] = topic_seqpropconf.min_distance_moon
        confdict["constraints"]["exclude_planets"] = topic_seqpropconf.exclude_planets

        confdict["sky_region"] = {}
        num_user_regions = topic_seqpropconf.num_user_regions
        region_list = []
        for k in range(num_user_regions):
            region_list.append(topic_seqpropconf.user_region_ids[k])

        confdict["sky_region"]["user_regions"] = region_list

        confdict["sky_exclusions"] = {}
        confdict["sky_exclusions"]["dec_window"] = topic_seqpropconf.dec_window

        num_sub_sequences = topic_seqpropconf.num_sub_sequences
        if num_sub_sequences:
            confdict["subsequences"] = {}
            sub_sequence_names = topic_seqpropconf.sub_sequence_names.split(',')
            confdict["subsequences"]["names"] = sub_sequence_names
            sub_sequence_filters = topic_seqpropconf.sub_sequence_filters.split(',')
            sub_sequence_visits_per_filter = topic_seqpropconf.num_sub_sequence_filter_visits
            index = 0
            for k, sname in enumerate(sub_sequence_names):
                sub_seq_section = "subseq_{}".format(sname)
                confdict[sub_seq_section] = {}
                num_sub_sequence_filters = topic_seqpropconf.num_sub_sequence_filters[k]
                confdict[sub_seq_section]["filters"] = \
                    sub_sequence_filters[index:index + num_sub_sequence_filters]
                confdict[sub_seq_section]["visits_per_filter"] = \
                    sub_sequence_visits_per_filter[index:index + num_sub_sequence_filters]
                index += num_sub_sequence_filters
                confdict[sub_seq_section]["num_events"] = topic_seqpropconf.num_sub_sequence_events[k]
                confdict[sub_seq_section]["num_max_missed"] = topic_seqpropconf.num_sub_sequence_max_missed[k]
                confdict[sub_seq_section]["time_interval"] = topic_seqpropconf.sub_sequence_time_intervals[k]
                confdict[sub_seq_section]["time_window_start"] = \
                    topic_seqpropconf.sub_sequence_time_window_starts[k]
                confdict[sub_seq_section]["time_window_max"] = \
                    topic_seqpropconf.sub_sequence_time_window_maximums[k]
                confdict[sub_seq_section]["time_window_end"] = \
                    topic_seqpropconf.sub_sequence_time_window_ends[k]
                confdict[sub_seq_section]["time_weight"] = topic_seqpropconf.sub_sequence_time_weights[k]

        num_master_sub_sequences = topic_seqpropconf.num_master_sub_sequences
        if num_master_sub_sequences:
            confdict["master_subsequences"] = {}
            master_sub_sequence_names = topic_seqpropconf.master_sub_sequence_names.split(',')

            confdict["master_subsequences"]["names"] = master_sub_sequence_names
            confdict["master_subsequences"]["num_nested"] = \
                topic_seqpropconf.num_nested_sub_sequences[:num_master_sub_sequences]
            nested_sub_sequence_names = topic_seqpropconf.nested_sub_sequence_names.split(',')
            nested_sub_sequence_filters = topic_seqpropconf.nested_sub_sequence_filters.split(',')
            index = 0
            findex = 0
            for k, mname in enumerate(master_sub_sequence_names):
                msub_seq_section = "msubseq_{}".format(mname)
                confdict[msub_seq_section] = {}
                num_nested_sub_sequences = topic_seqpropconf.num_nested_sub_sequences[k]
                confdict[msub_seq_section]["nested_names"] = \
                    nested_sub_sequence_names[index:index + num_nested_sub_sequences]
                confdict[msub_seq_section]["num_events"] = topic_seqpropconf.num_master_sub_sequence_events[k]
                confdict[msub_seq_section]["num_max_missed"] = \
                    topic_seqpropconf.num_master_sub_sequence_max_missed[k]
                confdict[msub_seq_section]["time_interval"] = \
                    topic_seqpropconf.master_sub_sequence_time_intervals[k]
                confdict[msub_seq_section]["time_window_start"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_starts[k]
                confdict[msub_seq_section]["time_window_max"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_maximums[k]
                confdict[msub_seq_section]["time_window_end"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_ends[k]
                confdict[msub_seq_section]["time_weight"] = \
                    topic_seqpropconf.master_sub_sequence_time_weights[k]

                for l, nname in enumerate(confdict[msub_seq_section]["nested_names"]):
                    nindex = index + l
                    nsub_seq_section = "nsubseq_{}".format(nname)
                    confdict[nsub_seq_section] = {}
                    num_nested_sub_sequence_filters = \
                        topic_seqpropconf.num_nested_sub_sequence_filters[nindex]
                    last_index = findex + num_nested_sub_sequence_filters
                    confdict[nsub_seq_section]["filters"] = nested_sub_sequence_filters[findex:last_index]
                    confdict[nsub_seq_section]["visits_per_filter"] = \
                        topic_seqpropconf.num_nested_sub_sequence_filter_visits[findex:last_index]
                    findex += num_nested_sub_sequence_filters
                    confdict[nsub_seq_section]["num_events"] = \
                        topic_seqpropconf.num_nested_sub_sequence_events[nindex]
                    confdict[nsub_seq_section]["num_max_missed"] = \
                        topic_seqpropconf.num_nested_sub_sequence_max_missed[nindex]
                    confdict[nsub_seq_section]["time_interval"] = \
                        topic_seqpropconf.nested_sub_sequence_time_intervals[nindex]
                    confdict[nsub_seq_section]["time_window_start"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_starts[nindex]
                    confdict[nsub_seq_section]["time_window_max"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_maximums[nindex]
                    confdict[nsub_seq_section]["time_window_end"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_ends[nindex]
                    confdict[nsub_seq_section]["time_weight"] = \
                        topic_seqpropconf.nested_sub_sequence_time_weights[nindex]

                index += num_nested_sub_sequences

        num_filters = topic_seqpropconf.num_filters
        filter_names = topic_seqpropconf.filter_names
        filter_list = filter_names.split(",")
        exp_index = 0
        for k in range(num_filters):
            filter_section = "filter_%s" % filter_list[k]
            confdict[filter_section] = {}
            confdict[filter_section]["min_brig"] = \
                topic_seqpropconf.bright_limit[k]
            confdict[filter_section]["max_brig"] = topic_seqpropconf.dark_limit[k]
            confdict[filter_section]["max_seeing"] = topic_seqpropconf.max_seeing[k]
            num_exp = topic_seqpropconf.num_filter_exposures[k]
            exp_times_list = []
            for n in range(num_exp):
                exp_times_list.append(topic_seqpropconf.exposures[exp_index])
                exp_index += 1
            confdict[filter_section]["exp_times"] = exp_times_list

        confdict["scheduling"] = {}
        max_num_targets = topic_seqpropconf.max_num_targets
        accept_serendipity = topic_seqpropconf.accept_serendipity
        accept_consecutive_visits = topic_seqpropconf.accept_consecutive_visits
        confdict["scheduling"]["max_num_targets"] = max_num_targets
        confdict["scheduling"]["accept_serendipity"] = accept_serendipity
        confdict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits
        confdict["scheduling"]["restart_lost_sequences"] = topic_seqpropconf.restart_lost_sequences
        confdict["scheduling"]["restart_complete_sequences"] = topic_seqpropconf.restart_complete_sequences
        confdict["scheduling"]["airmass_bonus"] = topic_seqpropconf.airmass_bonus
        confdict["scheduling"]["hour_angle_bonus"] = topic_seqpropconf.hour_angle_bonus
        confdict["scheduling"]["hour_angle_max"] = topic_seqpropconf.hour_angle_max

        return confdict

    def wtopic_target(self, topicTarget, target):

        topicTarget.targetId = target.targetid
        topicTarget.groupId = target.groupid
        topicTarget.fieldId = target.fieldid
        topicTarget.filter = target.filter
        topicTarget.request_time = target.time
        topicTarget.ra = target.ra
        topicTarget.dec = target.dec
        topicTarget.angle = target.ang
        topicTarget.num_exposures = target.num_exp
        for i, exptime in enumerate(target.exp_times):
            topicTarget.exposure_times[i] = int(exptime)
        topicTarget.airmass = target.airmass
        topicTarget.sky_brightness = target.sky_brightness
        topicTarget.cloud = target.cloud
        topicTarget.seeing = target.seeing
        topicTarget.slew_time = target.slewtime
        topicTarget.cost = target.cost
        topicTarget.rank = target.rank
        topicTarget.num_proposals = target.num_props
        for i, prop_id in enumerate(target.propid_list):
            topicTarget.proposal_Ids[i] = prop_id
        for i, prop_value in enumerate(target.value_list):
            topicTarget.proposal_values[i] = prop_value
        for i, prop_need in enumerate(target.need_list):
            topicTarget.proposal_needs[i] = prop_need
        for i, prop_bonus in enumerate(target.bonus_list):
            topicTarget.proposal_bonuses[i] = prop_bonus

        prop = self.schedulerDriver.science_proposal_list[0]
        moon_sun = prop.sky.get_moon_sun_info(numpy.array([target.ra_rad]), numpy.array([target.dec_rad]))
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
            self.topicTarget.solar_elong = math.degrees(moon_sun["solarElong"])

    def rtopic_observation(self, topic_observation):

        observation = Target()
        observation.time = topic_observation.observation_start_time
        observation.targetid = topic_observation.targetId
        observation.fieldid = topic_observation.fieldId
        observation.filter = topic_observation.filter
        observation.num_props = topic_observation.num_proposals
        observation.propid_list = []
        for k in range(observation.num_props):
            observation.propid_list.append(topic_observation.proposal_Ids[k])
        observation.ra_rad = math.radians(topic_observation.ra)
        observation.dec_rad = math.radians(topic_observation.dec)
        observation.ang_rad = math.radians(topic_observation.angle)
        observation.num_exp = topic_observation.num_exposures
        observation.exp_times = []
        for k in range(topic_observation.num_exposures):
            observation.exp_times.append(topic_observation.exposure_times[k])

        return observation

    def rtopic_observatory_state(self, topic_state):

        state = ObservatoryState()

        state.time = topic_state.timestamp
        state.ra_rad = math.radians(topic_state.pointing_ra)
        state.dec_rad = math.radians(topic_state.pointing_dec)
        state.ang_rad = math.radians(topic_state.pointing_angle)
        state.filter = topic_state.filter_position
        state.tracking = topic_state.tracking
        state.alt_rad = math.radians(topic_state.pointing_altitude)
        state.az_rad = math.radians(topic_state.pointing_azimuth)
        state.pa_rad = math.radians(topic_state.pointing_pa)
        state.rot_rad = math.radians(topic_state.pointing_rot)
        state.telalt_rad = math.radians(topic_state.telescope_altitude)
        state.telaz_rad = math.radians(topic_state.telescope_azimuth)
        state.telrot_rad = math.radians(topic_state.telescope_rotator)
        state.domalt_rad = math.radians(topic_state.dome_altitude)
        state.domaz_rad = math.radians(topic_state.dome_azimuth)
        state.mountedfilters = topic_state.filter_mounted.split(",")
        state.unmountedfilters = topic_state.filter_unmounted.split(",")

        return state

    def wtopic_interestedProposal(self, topic, targetId, target_list):

        topic.observationId = targetId
        topic.num_proposals = len(target_list)
        propid_list = []
        need_list = []
        bonus_list = []
        value_list = []
        propboost_list = []
        for k in range(topic.num_proposals):
            topic.proposal_Ids[k] = target_list[k].propid
            topic.proposal_needs[k] = target_list[k].need
            topic.proposal_bonuses[k] = target_list[k].bonus
            topic.proposal_values[k] = target_list[k].value
            topic.proposal_boosts[k] = target_list[k].propboost
            propid_list.append(target_list[k].propid)
            need_list.append(target_list[k].need)
            bonus_list.append(target_list[k].bonus)
            value_list.append(target_list[k].value)
            propboost_list.append(target_list[k].propboost)
        logstr = ("obsId=%i numprops=%i propid=%s need=%s bonus=%s value=%s propboost=%s" %
                  (targetId, topic.num_proposals,
                   propid_list, need_list, bonus_list, value_list, propboost_list))
        return logstr
