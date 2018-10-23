from builtins import object
from builtins import str
import warnings
import logging
import logging.handlers
import sys
import time
import copy
_gitpython = True
try:
    from git import Repo
except ImportError:
    _gitpython = False
    warnings.warn('Warning: gitpython is not installed. '
                  'Setting the configuration branch via git within the scheduler is not available. '
                  'Please install gitpython via "pip install gitpython" if this is necessary.')

from lsst.ts.scheduler.setup import TRACE, EXTENSIVE
from lsst.ts.scheduler.kernel import read_conf_file, conf_file_path
from lsst.ts.scheduler.sal_utils import SALUtils
from lsst.ts.scheduler import Driver
from lsst.ts.schedulerConfig import SimulationConfig as SchedulerConfig

from scheduler_config.constants import CONFIG_DIRECTORY, CONFIG_DIRECTORY_PATH

__all__ = ["Main"]

class Main(object):

    def __init__(self, options, driver=None):
        warnings.warn('DeprecationWarning! Use of Main will be deprecated. Use Model instead')
        self.log = logging.getLogger("schedulerMain")

        main_confdict = read_conf_file(conf_file_path(__name__, "conf", "scheduler", "main.conf"))
        self.measinterval = main_confdict['log']['rate_meas_interval']

        if options.path is None:
            self.configuration_path = str(CONFIG_DIRECTORY)
        else:
            self.configuration_path = options.path

        if _gitpython:
            self.config_repo = Repo(str(CONFIG_DIRECTORY_PATH))
        else:
            self.config_repo = None

        self.current_setting = ''
        self.valid_settings = self.read_valid_settings()
        self.log.debug('List of valid configurations:')
        for setting in self.valid_settings:
            if self.current_setting == setting[setting.find('/')+1:]:
                self.log.debug('{} [current]'.format(setting))
            else:
                self.log.debug('{}'.format(setting))

        self.sal = SALUtils(options.timeout)
        if driver is None:
            self.schedulerDriver = Driver({}, {})
        else:
            self.schedulerDriver = driver
        self.config = SchedulerConfig()

        self.meascount = 0
        self.visitcount = 0
        self.synccount = 0

        self.summary_state_enum = {'DISABLE': 0,
                                   'ENABLE': 1,
                                   'FAULT': 2,
                                   'OFFLINE': 3,
                                   'STANDBY': 4}

        self.cmd_state_transition = {'enterControl': 'STANDBY',
                                     'start': 'DISABLE',
                                     'enable': 'ENABLE'
                                     }

        self.state = 'OFFLINE'

        self.meastime = time.time()

    def sal_init(self):
        self.sal.start()

    def run(self):

        self.log.info("run")

        timestamp = 0.0

        try:

            self.broadcast_state()

            if not self.wait_cmd("enterControl"):
                raise Exception("Did not received enterControl command.")

            self.broadcast_state()
            self.broadcast_valid_settings()

            if not self.wait_cmd("start"):
                raise Exception("Did not received enterControl command.")

            self.log.info("Received start command with configuration %s..." % self.topic.settingsToApply)

            self.load_configuration(self.topic.settingsToApply)
            # now run configuration, then publish state transition

            self.configure_driver()

            self.configure_location()

            self.configure_telescope()

            self.configure_dome()

            self.configure_rotator()

            self.configure_camera()

            self.configure_slew()

            self.configure_optics()

            self.configure_park()

            self.configure_scheduler()

            self.broadcast_state()

            if not self.wait_cmd("enable"):
                raise Exception("Did not received enterControl command.")

            self.log.info("Enabling...")
            self.broadcast_state()

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
            self.state = 'FAULT'
            self.broadcast_state()

        self.schedulerDriver.end_survey()

        self.log.info("exit")
        self.sal.salShutdown()
        sys.exit(0)

    def configure_driver(self):

        # Configure survey duration
        self.sal.topic_schedulerConfig.surveyDuration = self.config.survey.duration
        self.schedulerDriver.configure_duration(self.config.survey.full_duration)
        self.sal.putSample_schedulerConfig(self.sal.topic_schedulerConfig)

        # write configuration to topic
        self.sal.wtopic_driver_config(self.sal.topic_driverConfig, self.config)
        conf_dict = self.sal.rtopic_driver_config(self.sal.topic_driverConfig)
        # configure driver
        self.schedulerDriver.configure(conf_dict)
        # publish driver configuration
        self.sal.putSample_driverConfig(self.sal.topic_driverConfig)

    def configure_location(self):

        config_dict = {'obs_site': self.config.observing_site.toDict()}
        self.schedulerDriver.configure_location(config_dict)
        self.sal.wtopic_location_config(self.sal.topic_obsSiteConfig, self.config)
        self.sal.putSample_obsSiteConfig(self.sal.topic_obsSiteConfig)

    def configure_telescope(self):

        self.schedulerDriver.configure_telescope(self.config.toDict()['observatory'])
        self.sal.wtopic_telescope_config(self.sal.topic_telescopeConfig, self.config)
        self.sal.putSample_telescopeConfig(self.sal.topic_telescopeConfig)

    def configure_dome(self):

        self.schedulerDriver.configure_dome(self.config.toDict()['observatory'])
        self.sal.wtopic_dome_config(self.sal.topic_domeConfig, self.config)
        self.sal.putSample_domeConfig(self.sal.topic_domeConfig)

    def configure_rotator(self):

        self.schedulerDriver.configure_rotator(self.config.toDict()['observatory'])
        self.sal.wtopic_rotator_config(self.sal.topic_rotatorConfig, self.config)
        self.sal.putSample_rotatorConfig(self.sal.topic_rotatorConfig)

    def configure_camera(self):

        self.schedulerDriver.configure_camera(self.config.toDict()['observatory'])
        self.sal.wtopic_camera_config(self.sal.topic_cameraConfig, self.config)
        self.sal.putSample_cameraConfig(self.sal.topic_cameraConfig)

    def configure_slew(self):

        self.schedulerDriver.configure_slew(self.config.toDict()['observatory'])
        self.log.debug("Sending slew configuration:")
        self.log.debug(self.config)
        self.sal.wtopic_slew_config(self.sal.topic_slewConfig, self.config)
        self.sal.putSample_slewConfig(self.sal.topic_slewConfig)

    def configure_optics(self):

        self.schedulerDriver.configure_optics(self.config.toDict()['observatory'])
        self.sal.wtopic_optics_config(self.sal.topic_opticsConfig, self.config)
        self.sal.putSample_opticsLoopCorrConfig(self.sal.topic_opticsConfig)

    def configure_park(self):

        self.schedulerDriver.configure_park(self.config.toDict()['observatory'])
        self.sal.wtopic_park_config(self.sal.topic_parkConfig, self.config)
        self.sal.putSample_parkConfig(self.sal.topic_parkConfig)

    def configure_scheduler(self):

        # This method should be changed so it just pass some string to the driver.
        # Right now I'm passing the configuration so it can setup the proposal based scheduler.
        # Then, the scheduler should actually return a topology to be broadcast here
        survey_topology = self.schedulerDriver.configure_scheduler(config=self.config,
                                                                   config_path=self.configuration_path)
        # self.sal.wtopic_scheduler_topology_config(self.sal.topic_schedulerTopology, self.config)
        self.sal.topic_schedulerTopology = survey_topology.to_topic()
        self.sal.putSample_surveyTopology(self.sal.topic_schedulerTopology)


    def main_loop(self, i_timestamp, i_lasttimetime):

        scode = self.sal.getNextSample_timeHandler(self.sal.topicTime)
        timestamp = copy.copy(i_timestamp)  # make sure local timestamp is a copy
        lasttimetime = copy.copy(i_lasttimetime)  # make sure local lasttimetime is a copy
        waittime = True

        if scode == 0 and self.sal.topicTime.timestamp != 0:
            lasttimetime = time.time()
            nightstamp = self.sal.topicTime.night
            is_down = self.sal.topicTime.isDown
            down_duration = self.sal.topicTime.downDuration
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

                    self.sal.topicFilterSwap.needSwap = needswap
                    self.sal.topicFilterSwap.filterToUnmount = filter2unmount
                    self.sal.logEvent_needFilterSwap(self.sal.topicFilterSwap, 2)
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

                            self.sal.logEvent_target(self.sal.topicTarget, 1)
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
            scode = self.sal.getNextSample_bulkCloud(self.sal.topic_cloud)
            if scode == 0 and self.sal.topic_cloud.timestamp != 0:
                lastcloudtime = time.time()
                waitcloud = False
                cloud = self.sal.topic_cloud.bulkCloud
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

    def read_valid_settings(self):
        """
        Read valid settings from the configuration path.

        :return:
        """

        if self.configuration_path is None:
            self.current_setting = 'default'
            return ['default']

        # if gitpython is not available, we cannot search for branches.
        if not _gitpython or self.config_repo is None:
            self.current_setting = self.configuration_path
            return [self.current_setting]

        self.current_setting = str(self.config_repo.active_branch)
        remote_branches = []
        for ref in self.config_repo.git.branch('-r').split('\n'):
            if 'HEAD' not in ref:
                remote_branches.append(ref)

        return remote_branches

    def load_configuration(self, config_name):

        if self.configuration_path is None:
            self.log.debug("No configuration path. Using default values.")
            self.config.load(None)
        elif _gitpython is False:
            config_info = '%s ' % self.configuration_path
            config_file = self.configuration_path
            import subprocess
            try:
                label = subprocess.check_output(["git", "describe"]).strip().decode
                config_info += ' (%s)' % (label)
            except subprocess.CalledProcessError:
                pass
            self.log.debug('Gitpython is not available. Using config settings '
                           'on disk at %s' % (config_info))
            self.log.debug('reading configuration from %s' % config_file)
            self.config.load([config_file])
        else:
            valid_setting = False
            for config in self.valid_settings:
                if config_name == config[config.find('/') + 1:]:
                    self.log.debug('Loading settings: %s [%s]' % (config, config_name))
                    self.config_repo.git.checkout(config_name)
                    self.current_setting = str(self.config_repo.active_branch)
                    valid_setting = True
                    break
            if not valid_setting:
                self.log.warning('Setting %s not valid! Using %s' % (config_name, self.current_setting))

            config_file = self.configuration_path
            self.log.debug('reading configuration from %s' % config_file)
            self.config.load([config_file])
        self.config.load_proposals()
        self.log.info("{} proposals active.".format(self.config.num_proposals))
        self.config.validate()

    def broadcast_state(self):

        self.sal.topic_summaryState.summaryState = self.summary_state_enum[self.state]
        self.log.debug('Broadcasting state: %i ' % self.sal.topic_summaryState.summaryState)
        self.sal.logEvent_summaryState(self.sal.topic_summaryState, 1)

    def broadcast_valid_settings(self):

        # self.sal.topic_summaryState.summaryState = self.summary_state_enum[self.state]
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        self.sal.topicValidSettings.packageVersions = valid_settings
        self.sal.logEvent_validSettings(self.sal.topicValidSettings, 5)

    def wait_cmd(self, cmd):

        self.log.debug('Waiting for %s cmd' % cmd)
        accept_command = getattr(self.sal, 'acceptCommand_{}'.format(cmd))
        self.topic = getattr(self.sal, "topic_command_{}".format(cmd))
        wait_start = time.time()

        while True:
            cmdId = accept_command(self.topic)
            tc = time.time()
            if cmdId > 0:
                self.log.debug('Received %s cmd: State [%s -> %s]' % (cmd, self.state, self.cmd_state_transition[cmd]))
                self.log.debug('Acknowledging cmd')
                self.sal.salProcessor("scheduler_command_{}".format(cmd))

                ackCommand = getattr(self.sal, 'ackCommand_{}'.format(cmd))
                ackCommand(cmdId, 303, 0, "Done : OK")

                self.state = self.cmd_state_transition[cmd]
                return True
            if (tc - wait_start) > self.sal.main_loop_timeouts:
                self.log.debug("run: time timeout")
                return False
            time.sleep(self.sal.sal_sleeper)

