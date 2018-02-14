from builtins import object
from builtins import str
import logging
import logging.handlers
import sys
import time
import copy

from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel, ObservatoryState
from lsst.ts.scheduler.setup import TRACE, EXTENSIVE
from lsst.ts.scheduler.kernel import read_conf_file, conf_file_path
from lsst.ts.scheduler.sal_utils import SALUtils
from lsst.ts.scheduler import Driver

__all__ = ["Main"]

class Main(object):

    def __init__(self, options, driver=Driver()):
        self.log = logging.getLogger("schedulerMain")

        main_confdict = read_conf_file(conf_file_path(__name__, "conf", "scheduler", "main.conf"))
        self.measinterval = main_confdict['log']['rate_meas_interval']

        self.sal = SALUtils(options.timeout)
        self.schedulerDriver = driver

        self.meascount = 0
        self.visitcount = 0
        self.synccount = 0

        self.meastime = time.time()

    def sal_init(self):
        self.sal.start()

    def run(self):

        self.log.info("run")

        timestamp = 0.0

        try:

            self.configure_driver()

            self.configure_location()

            self.configure_telescope()

            self.configure_dome()

            self.configure_rotator()

            self.configure_camera()

            self.configure_slew()

            self.configure_optics()

            self.configure_park()

            self.configure_proposals()

            waittime = True
            lasttimetime = time.time()

            while waittime:

                waittime, timestamp, lasttimetime = self.main_loop(timestamp, lasttimetime)

                newtime = time.time()
                deltatime = newtime - self.meastime
                if deltatime >= self.measinterval:
                    rate = float(self.meascount) / deltatime
                    self.log.info("run: rxe %.0f visits/sec total=%i visits sync=%i" % (rate, self.visitcount,
                                                                                        self.synccount))
                    self.meastime = newtime
                    self.meascount = 0

        except:
            self.log.exception("An exception was thrown in the Scheduler!")

        self.schedulerDriver.end_survey()

        self.log.info("exit")
        self.sal.salShutdown()
        sys.exit(0)

    def configure_driver(self):

        # Configure survey duration

        survey_duration = 0.
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_schedulerConfig(self.sal.topic_schedulerConfig)
            if (scode == 0 and self.sal.topic_schedulerConfig.survey_duration > 0.0):
                lastconfigtime = time.time()
                survey_duration = self.sal.topic_schedulerConfig.survey_duration
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
                time.sleep(self.sal.sal_sleeper)

        self.schedulerDriver.configure_duration(survey_duration)

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()
        while waitconfig:
            scode = self.sal.getNextSample_driverConfig(self.sal.topic_driverConfig)
            if (scode == 0 and self.sal.topic_driverConfig.timecost_time_max > 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_driver_config(self.sal.topic_driverConfig)
                self.log.info("run: rx driver config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: driver config timeout")
                    config_file = conf_file_path(__name__, "conf", "scheduler", "driver.conf")
                    config_dict = read_conf_file(config_file)
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure(config_dict)

    def configure_location(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_obsSiteConfig(self.sal.topic_obsSiteConfig)
            if (scode == 0 and self.sal.topic_obsSiteConfig.name != ""):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_location_config(self.sal.topic_obsSiteConfig)
                self.log.info("run: rx site config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: site config timeout")
                    config_dict = ObservatoryLocation.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_location(config_dict)

    def configure_telescope(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_telescopeConfig(self.sal.topic_telescopeConfig)
            if (scode == 0 and self.sal.topic_telescopeConfig.altitude_minpos >= 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_telescope_config(self.sal.topic_telescopeConfig)
                self.log.info("run: rx telescope config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: telescope config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_telescope(config_dict)

    def configure_dome(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_domeConfig(self.sal.topic_domeConfig)
            if (scode == 0 and self.sal.topic_domeConfig.altitude_maxspeed >= 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_dome_config(self.sal.topic_domeConfig)
                self.log.info("run: rx dome config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: dome config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_dome(config_dict)

    def configure_rotator(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_rotatorConfig(self.sal.topic_rotatorConfig)
            if (scode == 0 and self.sal.topic_rotatorConfig.maxspeed >= 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_rotator_config(self.sal.topic_rotatorConfig)
                self.log.info("run: rx rotator config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: rotator config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_rotator(config_dict)

    def configure_camera(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_cameraConfig(self.sal.topic_cameraConfig)
            if (scode == 0 and self.sal.topic_cameraConfig.readout_time > 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_camera_config(self.sal.topic_cameraConfig)
                self.log.info("run: rx camera config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    waitconfig = False
                    self.log.info("run: camera config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_camera(config_dict)

    def configure_slew(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_slewConfig(self.sal.topic_slewConfig)
            if (scode == 0 and self.sal.topic_slewConfig.prereq_exposures != ""):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_slew_config(self.sal.topic_slewConfig)
                self.log.info("run: rx slew config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    waitconfig = False
                    self.log.info("run: slew config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_slew(config_dict)

    def configure_optics(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_opticsLoopCorrConfig(self.sal.topic_opticsConfig)
            if (scode == 0 and self.sal.topic_opticsConfig.tel_optics_ol_slope > 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_optics_config(self.sal.topic_opticsConfig)
                self.log.info("run: rx optics config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: optics config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_optics(config_dict)

    def configure_park(self):

        config_dict = {}
        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_parkConfig(self.sal.topic_parkConfig)
            if (scode == 0 and self.sal.topic_parkConfig.telescope_altitude > 0):
                lastconfigtime = time.time()
                config_dict = self.sal.rtopic_park_config(self.sal.topic_parkConfig)
                self.log.info("run: rx park config=%s" % (config_dict))
                waitconfig = False
            else:
                tf = time.time()
                if (tf - lastconfigtime > 10.0):
                    self.log.info("run: park config timeout")
                    config_dict = ObservatoryModel.get_configure_dict()
                    waitconfig = False
                time.sleep(self.sal.sal_sleeper)
        self.schedulerDriver.configure_park(config_dict)

    def configure_proposals(self):
        self.configure_area_distribution_proposals()

        self.configure_sequence_proposals()

    def configure_area_distribution_proposals(self):

        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_generalPropConfig(self.sal.topic_areaDistPropConfig)
            if (scode == 0 and self.sal.topic_areaDistPropConfig.name != ""):
                lastconfigtime = time.time()
                name = self.sal.topic_areaDistPropConfig.name
                prop_id = self.sal.topic_areaDistPropConfig.prop_id
                if (prop_id == -1 and name == "NULL"):
                    self.log.info("run: area prop config null")
                    waitconfig = False
                else:
                    config_dict = self.sal.rtopic_area_prop_config(self.sal.topic_areaDistPropConfig)
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
                time.sleep(self.sal.sal_sleeper)

    def configure_sequence_proposals(self):

        waitconfig = True
        lastconfigtime = time.time()

        while waitconfig:
            scode = self.sal.getNextSample_sequencePropConfig(self.sal.topic_sequencePropConfig)
            if (scode == 0 and self.sal.topic_sequencePropConfig.name != ""):
                lastconfigtime = time.time()
                name = self.sal.topic_sequencePropConfig.name
                prop_id = self.sal.topic_sequencePropConfig.prop_id
                if (prop_id == -1 and name == "NULL"):
                    self.log.info("run: seq prop config null")
                    waitconfig = False
                else:
                    config_dict = self.sal.rtopic_seq_prop_config(self.sal.topic_sequencePropConfig)
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
                time.sleep(self.sal.sal_sleeper)

    def main_loop(self, i_timestamp, i_lasttimetime):

        scode = self.sal.getNextSample_timeHandler(self.sal.topicTime)
        timestamp = copy.copy(i_timestamp)  # make sure local timestamp is a copy
        lasttimetime = copy.copy(i_lasttimetime)  # make sure local lasttimetime is a copy
        waittime = True

        if scode == 0 and self.sal.topicTime.timestamp != 0:
            lasttimetime = time.time()
            nightstamp = self.sal.topicTime.night
            is_down = self.sal.topicTime.is_down
            down_duration = self.sal.topicTime.down_duration
            self.log.log(EXTENSIVE, "run: rx time=%.6f night=%i is_down=%s down_duration=%.1f" %
                         (self.sal.topicTime.timestamp, nightstamp, is_down, down_duration))
            if self.sal.topicTime.timestamp > timestamp:
                timestamp = self.sal.topicTime.timestamp
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

                    self.sal.topicFilterSwap.need_swap = needswap
                    self.sal.topicFilterSwap.filter_to_unmount = filter2unmount
                    self.sal.putSample_filterSwap(self.sal.topicFilterSwap)
                    self.log.info("run: tx filter swap %s %s" % (needswap, filter2unmount))
                    waitstate = False

                laststatetime = time.time()
                while waitstate:
                    scode = self.sal.getNextSample_observatoryState(self.sal.topicObservatoryState)
                    if scode == 0 and self.sal.topicObservatoryState.timestamp != 0:
                        laststatetime = time.time()
                        waitstate = False
                        observatory_state = self.sal.rtopic_observatory_state(self.sal.topicObservatoryState)

                        self.log.log(EXTENSIVE, "run: rx state %s" % str(observatory_state))

                        self.schedulerDriver.update_internal_conditions(observatory_state, nightstamp)

                        if is_down:
                            waitobservation = False
                        else:
                            self.get_external_conditions()

                            target = self.schedulerDriver.select_next_target()

                            self.sal.wtopic_target(self.sal.topicTarget, target, self.schedulerDriver.sky)

                            self.sal.putSample_target(self.sal.topicTarget)
                            self.log.debug("run: tx target %s", str(target))

                            waitobservation = True

                        lastobstime = time.time()
                        if waitobservation:
                            self.wait_observation()
                    else:
                        ts = time.time()
                        if ts - laststatetime > self.sal.main_loop_timeouts:
                            waitstate = False
                            self.log.debug("run: state timeout")
                            self.log.log(TRACE, "run: t=%f laststatetime=%f" % (ts, laststatetime))

            else:
                self.log.error("run: rx non progressive time previous=%f new=%f" %
                               (timestamp, self.sal.topicTime.timestamp))
                waittime = False

        else:
            tc = time.time()
            if (tc - lasttimetime) > self.sal.main_loop_timeouts:
                self.log.debug("run: time timeout")
                waittime = False

        return waittime, timestamp, lasttimetime

    def get_external_conditions(self):

        waitcloud = True
        lastcloudtime = time.time()
        cloud = 0.0

        while waitcloud:
            scode = self.sal.getNextSample_cloud(self.sal.topic_cloud)
            if scode == 0 and self.sal.topic_cloud.timestamp != 0:
                lastcloudtime = time.time()
                waitcloud = False
                cloud = self.sal.topic_cloud.cloud
            else:
                tf = time.time()
                if (tf - lastcloudtime > 10.0):
                    self.log.info("run: cloud timeout")
                    waitcloud = False
                    cloud = 0.0

        waitseeing = True
        lastseeingtime = time.time()
        seeing = 0.0

        while waitseeing:
            scode = self.sal.getNextSample_seeing(self.sal.topic_seeing)
            if scode == 0 and self.sal.topic_seeing.timestamp != 0:
                lastseeingtime = time.time()
                waitseeing = False
                seeing = self.sal.topic_seeing.seeing
            else:
                tf = time.time()
                if (tf - lastseeingtime > 10.0):
                    self.log.info("run: seeing timeout")
                    waitseeing = False
                    seeing = 0.0

        self.log.log(EXTENSIVE, "run: rx conditions cloud=%.2f seeing=%.2f" %
                     (cloud, seeing))
        self.schedulerDriver.update_external_conditions(cloud, seeing)

    def wait_observation(self):

        waitobservation = True
        lastobstime = time.time()

        while waitobservation:
            scode = self.sal.getNextSample_observation(self.sal.topicObservation)
            if scode == 0 and self.sal.topicObservation.targetId != 0:
                lastobstime = time.time()
                self.meascount += 1
                self.visitcount += 1
                if self.sal.topicTarget.targetId == self.sal.topicObservation.targetId:
                    self.synccount += 1

                    obs = self.sal.rtopic_observation(self.sal.topicObservation)
                    self.log.log(EXTENSIVE, "run: rx observation %s", str(obs))
                    target_list = self.schedulerDriver.register_observation(obs)
                    s = self.sal.wtopic_interestedProposal(self.sal.tInterestedProposal,
                                                       self.sal.topicObservation.targetId,
                                                       target_list)
                    self.sal.putSample_interestedProposal(self.sal.tInterestedProposal)
                    self.log.log(EXTENSIVE, "run: tx interested %s", s)
                    waitobservation = False
                else:
                    self.log.warning("run: rx unsync observation Id=%i "
                                     "for target Id=%i" %
                                     (self.sal.topicObservation.targetId,
                                      self.sal.topicTarget.targetId))
            else:
                to = time.time()
                if to - lastobstime > self.sal.main_loop_timeouts:
                    waitobservation = False
                    self.log.debug("run: observation timeout")
                self.log.log(TRACE, "run: t=%f lastobstime=%f" % (to, lastobstime))

            newtime = time.time()
            deltatime = newtime - self.meastime
            if deltatime >= self.measinterval:
                rate = float(self.meascount) / deltatime
                self.log.info("run: rxi %.0f visits/sec total=%i visits sync=%i" %
                              (rate, self.visitcount, self.synccount))
                self.meastime = newtime
                self.meascount = 0
