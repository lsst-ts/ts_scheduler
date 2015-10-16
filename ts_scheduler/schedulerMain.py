import sys
import time
import datetime
import logging

from SALPY_scheduler import *
from schedulerDriver import *
from schedulerTarget import *

class schedulerMain(object):

    def __init__(self):

        self.schedulerDriver = schedulerDriver()

        self.sal = SAL_scheduler()
        self.sal.setDebugLevel(0)

        self.topicTime           = scheduler_timeHandlerC()
        self.topicObservation    = scheduler_observationTestC()
        self.topicTarget         = scheduler_targetTestC()

        self.log = logging.getLogger("scheduler")
        timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
        hdlr = logging.FileHandler("scheduler.%s.log" % (timestr))
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)
        self.log.setLevel(logging.DEBUG)

        return

    def run(self):

        self.log.info("Main: scheduler started")

        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observationTest")
        self.sal.salTelemetryPub("scheduler_targetTest")

        self.schedulerDriver.startSurvey()

        measInterval = 1.0

        measCount  = 0
        visitCount = 0
        syncCount  = 0

        measTime     = time.time()

        timestamp = 0.0

        try:
            waitConditions  = True
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
                        self.topicTarget.targetId      = target.targetId
                        self.topicTarget.fieldId       = target.fieldId
                        self.topicTarget.filter        = target.filter
                        self.topicTarget.ra            = target.ra
                        self.topicTarget.dec           = target.dec
                        self.topicTarget.angle         = target.angle
                        self.topicTarget.num_exposures = target.num_exposures

                        self.sal.putSample_targetTest(self.topicTarget)
                        self.log.info("Main: tx target Id=%i, field=%i, filter=%s" % (target.targetId, target.fieldId, target.filter))

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

                                    self.log.info("Main: rx observation target Id=%i" % (self.topicObservation.targetId))
                                    self.schedulerDriver.registerObservation(self.topicObservation)

                                    break
                                else:
                                    self.log.warning("Main: rx unsync observation Id=%i for target Id=%i" % (self.topicObservation.targetId, self.topicTarget.targetId))
                                    print("UNSYNC targetId=%i observationId=%i" % (self.topicTarget.targetId, self.topicObservation.targetId))
                            else:
                                t = time.time()
                                if (t - lastObsTime > 10.0):
                                    waitObservation = False
                                self.log.debug("Main: t=%f lastObsTime=%f" % (t, lastObsTime))

                            newTime = time.time()
                            deltaTime = newTime - measTime
                            if (deltaTime >= measInterval):
                                rate = float(measCount)/deltaTime
                                print("rix %.0f visits/sec total=%i visits sync=%i" % (rate, visitCount, syncCount))
                                measTime = newTime
                                measCount = 0
                    else:
                        self.log.warning("Main: rx backward time previous=%f new=%f" % (timestamp, self.topicTime.timestamp))
                        print("BACKWARD previous=%f new=%f" % (timestamp, self.topicTime.timestamp))

                else:
                    t = time.time()
                    if (t - lastCondTime > 30.0):
                        waitConditions = False

                newTime = time.time()
                deltaTime = newTime - measTime
                if (deltaTime >= measInterval):
                    rate = float(measCount)/deltaTime
                    print("rx %.0f visits/sec total=%i visits sync=%i" % (rate, visitCount, syncCount))
                    measTime = newTime
                    measCount = 0

        except KeyboardInterrupt:
            self.log.info("Main: scheduler interrupted")

        self.schedulerDriver.endSurvey()

        self.log.info("Main: scheduler stopped")
        self.sal.salShutdown()
        sys.exit(0)

