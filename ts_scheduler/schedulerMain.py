import sys
import time
import logging

from SALPY_scheduler import SAL_scheduler
from SALPY_scheduler import scheduler_timeHandlerC
from SALPY_scheduler import scheduler_observationTestC
from SALPY_scheduler import scheduler_targetTestC
from SALPY_scheduler import scheduler_schedulerConfigC
from SALPY_scheduler import scheduler_fieldC

from schedulerDefinitions import INFOX, RAD2DEG, readConfFile
from schedulerDriver import Driver

class Main(object):

    def __init__(self):
        logging.INFOX = INFOX
        logging.addLevelName(logging.INFOX, 'INFOX')

        main_confdict, pairs = readConfFile("../conf/scheduler/main.conf")
        if ('logLevel' in main_confdict):
            loglevelstr = main_confdict['logLevel']
            if (loglevelstr == 'INFOX'):
                self.logLevel = logging.INFOX
            elif (loglevelstr == 'INFO'):
                self.logLevel = logging.INFO
            elif (loglevelstr == 'DEBUG'):
                self.logLevel = logging.DEBUG
            else:
                self.logLevel = logging.INFO
        else:
            self.logLevel = logging.INFO
        if ('rateMeasurementInterval' in main_confdict):
            self.measinterval = main_confdict['rateMeasurementInterval']
        else:
            self.measinterval = 1.0

        self.logFormatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        self.log = logging.getLogger("scheduler")
        self.log.setLevel(logging.INFO)

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(self.logFormatter)
        console.setLevel(logging.INFOX)
        self.log.addHandler(console)

        timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
        self.defaultLogFileName = "../log/scheduler.%s.log" % (timestr)
        self.logFile = None
        self.config_logfile(self.defaultLogFileName)

        self.schedulerDriver = Driver(self.log)

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)

        self.topicConfig = scheduler_schedulerConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservation = scheduler_observationTestC()
        self.topicField = scheduler_fieldC()
        self.topicTarget = scheduler_targetTestC()

    def config_logfile(self, logfilename):
        if (self.logFile is not None):
            self.log.removeHandler(self.logFile)
        self.logFile = logging.FileHandler(logfilename)
        self.logFile.setFormatter(self.logFormatter)
        self.logFile.setLevel(self.logLevel)
        self.log.addHandler(self.logFile)
        self.log.log(INFOX, "Main: configure logFile=%s" % logfilename)

    def run(self):

        self.log.info("Main: scheduler started")

        self.sal.salTelemetrySub("scheduler_schedulerConfig")
        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observationTest")
        self.sal.salTelemetryPub("scheduler_field")
        self.sal.salTelemetryPub("scheduler_targetTest")

        self.schedulerDriver.start_survey()

        meascount = 0
        visitcount = 0
        synccount = 0

        meastime = time.time()

        timestamp = 0.0

        try:
            waitconfig = True
            lastconfigtime = time.time()
            while waitconfig:
                scode = self.sal.getNextSample_schedulerConfig(self.topicConfig)
                if (scode == 0 and self.topicConfig.log_file != ""):
                    lastconfigtime = time.time()
                    logfilename = self.topicConfig.log_file
                    self.log.log(INFOX, "schedulerMain.run: config logfile=%s" % (logfilename))
                    waitconfig = False
                    self.configLogFile(logfilename)

                else:
                    tf = time.time()
                    if (tf - lastconfigtime > 10.0):
                        waitconfig = False
                        self.log.log(INFOX, "Main: config timeout")

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
                    self.log.log(INFOX, "schedulerMain.run: tx field %s" % (field_dict[fieldid]))
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)

            waitconditions = True
            lastcondtime = time.time()
            while waitconditions:
                scode = self.sal.getNextSample_timeHandler(self.topicTime)
                if (scode == 0 and self.topicTime.timestamp != 0):
                    if (self.topicTime.timestamp > timestamp):
                        lastcondtime = time.time()
                        timestamp = self.topicTime.timestamp

                        self.log.info("Main: rx time=%f" % (timestamp))

                        self.schedulerDriver.update_internal_conditions(self.topicTime)
                        self.schedulerDriver.update_external_conditions(self.topicTime)

                        target = self.schedulerDriver.select_next_target()
                        self.topicTarget.targetId = target.targetid
                        self.topicTarget.fieldId = target.fieldid
                        self.topicTarget.filter = target.filter
                        self.topicTarget.ra = target.ra_rad * RAD2DEG
                        self.topicTarget.dec = target.dec_rad * RAD2DEG
                        self.topicTarget.angle = target.ang_rad * RAD2DEG
                        self.topicTarget.num_exposures = target.numexp

                        self.sal.putSample_targetTest(self.topicTarget)
                        self.log.info("Main: tx target Id=%i, field=%i, filter=%s" %
                                      (target.targetid, target.fieldid, target.filter))

                        waitobservation = True
                        lastobstime = time.time()
                        while waitobservation:
                            scode = self.sal.getNextSample_observationTest(self.topicObservation)
                            if (scode == 0 and self.topicObservation.targetId != 0):
                                meascount += 1
                                visitcount += 1
                                if (self.topicTarget.targetId == self.topicObservation.targetId):
                                    lastobstime = time.time()
                                    synccount += 1

                                    self.log.info("Main: rx observation target Id=%i" %
                                                  (self.topicObservation.targetId))
                                    self.schedulerDriver.register_observation(self.topicObservation)

                                    break
                                else:
                                    self.log.warning("Main: rx unsync observation Id=%i for target Id=%i" %
                                                     (self.topicObservation.targetId,
                                                      self.topicTarget.targetId))
                            else:
                                to = time.time()
                                if (to - lastobstime > 10.0):
                                    waitobservation = False
                                self.log.debug("Main: t=%f lastobstime=%f" % (to, lastobstime))

                            newtime = time.time()
                            deltatime = newtime - meastime
                            if (deltatime >= self.measinterval):
                                rate = float(meascount) / deltatime
                                self.log.log(INFOX, "Main: rix %.0f visits/sec total=%i visits sync=%i" %
                                             (rate, visitcount, synccount))
                                meastime = newtime
                                meascount = 0
                    else:
                        self.log.warning("Main: rx backward time previous=%f new=%f" %
                                         (timestamp, self.topicTime.timestamp))

                else:
                    tc = time.time()
                    if (tc - lastcondtime > 30.0):
                        waitconditions = False

                newtime = time.time()
                deltatime = newtime - meastime
                if (deltatime >= self.measinterval):
                    rate = float(meascount) / deltatime
                    self.log.log(INFOX, "Main: rx %.0f visits/sec total=%i visits sync=%i" %
                                 (rate, visitcount, synccount))
                    meastime = newtime
                    meascount = 0

        except KeyboardInterrupt:
            self.log.info("Main: scheduler interrupted")

        self.schedulerDriver.end_survey()

        self.log.info("Main: scheduler stopped")
        self.sal.salShutdown()
        sys.exit(0)
