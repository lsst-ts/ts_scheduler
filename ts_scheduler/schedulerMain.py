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
from schedulerDriver import schedulerDriver

class schedulerMain(object):

    def __init__(self):
        logging.INFOX = INFOX
        logging.addLevelName(logging.INFOX, 'INFOX')

        schedulerMainConfig, pairs = readConfFile("../conf/scheduler/main.conf")
        if ('logLevel' in schedulerMainConfig):
            logLevelStr = schedulerMainConfig['logLevel']
            if (logLevelStr == 'INFOX'):
                self.logLevel = logging.INFOX
            elif (logLevelStr == 'INFO'):
                self.logLevel = logging.INFO
            elif (logLevelStr == 'DEBUG'):
                self.logLevel = logging.DEBUG
            else:
                self.logLevel = logging.INFO
        else:
            self.logLevel = logging.INFO
        if ('rateMeasurementInterval' in schedulerMainConfig):
            self.measInterval = schedulerMainConfig['rateMeasurementInterval']
        else:
            self.measInterval = 1.0

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
        self.configLogFile(self.defaultLogFileName)

        self.schedulerDriver = schedulerDriver(self.log)

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)

        self.topicConfig = scheduler_schedulerConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservation = scheduler_observationTestC()
        self.topicField = scheduler_fieldC()
        self.topicTarget = scheduler_targetTestC()

        return

    def configLogFile(self, logFileName):
        if (self.logFile is not None):
            self.log.removeHandler(self.logFile)
        self.logFile = logging.FileHandler(logFileName)
        self.logFile.setFormatter(self.logFormatter)
        self.logFile.setLevel(self.logLevel)
        self.log.addHandler(self.logFile)
        self.log.log(INFOX, "Main: configure logFile=%s" % logFileName)

        return

    def run(self):

        self.log.info("Main: scheduler started")

        self.sal.salTelemetrySub("scheduler_schedulerConfig")
        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observationTest")
        self.sal.salTelemetryPub("scheduler_field")
        self.sal.salTelemetryPub("scheduler_targetTest")

        self.schedulerDriver.startSurvey()

        measCount = 0
        visitCount = 0
        syncCount = 0

        measTime = time.time()

        timestamp = 0.0

        try:
            waitConfig = True
            lastConfigTime = time.time()
            while waitConfig:
                scode = self.sal.getNextSample_schedulerConfig(self.topicConfig)
                if (scode == 0 and self.topicConfig.log_file != ""):
                    lastConfigTime = time.time()
                    logFileName = self.topicConfig.log_file
                    self.log.log(INFOX, "schedulerMain.run: config logfile=%s" % (logFileName))
                    waitConfig = False
                    self.configLogFile(logFileName)

                else:
                    tf = time.time()
                    if (tf - lastConfigTime > 10.0):
                        waitConfig = False
                        self.log.log(INFOX, "Main: config timeout")

            fieldsDict = self.schedulerDriver.getFieldsDict()
            if len(fieldsDict) > 0:
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)
                for fieldId in fieldsDict:
                    self.topicField.ID = fieldsDict[fieldId].fieldId
                    self.topicField.ra = fieldsDict[fieldId].ra_RAD * RAD2DEG
                    self.topicField.dec = fieldsDict[fieldId].dec_RAD * RAD2DEG
                    self.topicField.gl = fieldsDict[fieldId].gl_RAD * RAD2DEG
                    self.topicField.gb = fieldsDict[fieldId].gb_RAD * RAD2DEG
                    self.topicField.el = fieldsDict[fieldId].el_RAD * RAD2DEG
                    self.topicField.eb = fieldsDict[fieldId].eb_RAD * RAD2DEG
                    self.topicField.fov = fieldsDict[fieldId].fov_RAD * RAD2DEG
                    self.sal.putSample_field(self.topicField)
                    self.log.log(INFOX, "schedulerMain.run: tx field %s" % (fieldsDict[fieldId]))
                self.topicField.ID = -1
                self.sal.putSample_field(self.topicField)

            waitConditions = True
            lastCondTime = time.time()
            while waitConditions:
                scode = self.sal.getNextSample_timeHandler(self.topicTime)
                if (scode == 0 and self.topicTime.timestamp != 0):
                    if (self.topicTime.timestamp > timestamp):
                        lastCondTime = time.time()
                        timestamp = self.topicTime.timestamp

                        self.log.info("Main: rx time=%f" % (timestamp))

                        self.schedulerDriver.updateInternalConditions(self.topicTime)
                        self.schedulerDriver.updateExternalConditions(self.topicTime)

                        target = self.schedulerDriver.selectNextTarget()
                        self.topicTarget.targetId = target.targetId
                        self.topicTarget.fieldId = target.fieldId
                        self.topicTarget.filter = target.filter
                        self.topicTarget.ra = target.ra_RAD * RAD2DEG
                        self.topicTarget.dec = target.dec_RAD * RAD2DEG
                        self.topicTarget.angle = target.ang_RAD * RAD2DEG
                        self.topicTarget.num_exposures = target.numexp

                        self.sal.putSample_targetTest(self.topicTarget)
                        self.log.info("Main: tx target Id=%i, field=%i, filter=%s" %
                                      (target.targetId, target.fieldId, target.filter))

                        waitObservation = True
                        lastObsTime = time.time()
                        while waitObservation:
                            scode = self.sal.getNextSample_observationTest(self.topicObservation)
                            if (scode == 0 and self.topicObservation.targetId != 0):
                                measCount += 1
                                visitCount += 1
                                if (self.topicTarget.targetId == self.topicObservation.targetId):
                                    lastObsTime = time.time()
                                    syncCount += 1

                                    self.log.info("Main: rx observation target Id=%i" %
                                                  (self.topicObservation.targetId))
                                    self.schedulerDriver.registerObservation(self.topicObservation)

                                    break
                                else:
                                    self.log.warning("Main: rx unsync observation Id=%i for target Id=%i" %
                                                     (self.topicObservation.targetId,
                                                      self.topicTarget.targetId))
                            else:
                                to = time.time()
                                if (to - lastObsTime > 10.0):
                                    waitObservation = False
                                self.log.debug("Main: t=%f lastObsTime=%f" % (to, lastObsTime))

                            newTime = time.time()
                            deltaTime = newTime - measTime
                            if (deltaTime >= self.measInterval):
                                rate = float(measCount) / deltaTime
                                self.log.log(INFOX, "Main: rix %.0f visits/sec total=%i visits sync=%i" %
                                             (rate, visitCount, syncCount))
                                measTime = newTime
                                measCount = 0
                    else:
                        self.log.warning("Main: rx backward time previous=%f new=%f" %
                                         (timestamp, self.topicTime.timestamp))

                else:
                    tc = time.time()
                    if (tc - lastCondTime > 30.0):
                        waitConditions = False

                newTime = time.time()
                deltaTime = newTime - measTime
                if (deltaTime >= self.measInterval):
                    rate = float(measCount) / deltaTime
                    self.log.log(INFOX, "Main: rx %.0f visits/sec total=%i visits sync=%i" %
                                 (rate, visitCount, syncCount))
                    measTime = newTime
                    measCount = 0

        except KeyboardInterrupt:
            self.log.info("Main: scheduler interrupted")

        self.schedulerDriver.endSurvey()

        self.log.info("Main: scheduler stopped")
        self.sal.salShutdown()
        sys.exit(0)
