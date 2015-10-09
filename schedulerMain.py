import sys
import time
import datetime

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

        return

    def run(self):

        self.sal.salTelemetrySub("scheduler_timeHandler")
        self.sal.salTelemetrySub("scheduler_observationTest")
        self.sal.salTelemetryPub("scheduler_targetTest")

        measInterval = 1.0

        measCount  = 0
        visitCount = 0
        syncCount  = 0

        measTime = time.time()
        loopTime = time.time()

        timestamp = 0.0

        try:
            waitConditions  = True
            while waitConditions:
                scode = self.sal.getNextSample_timeHandler(self.topicTime)
                t = time.time()
                if (scode == 0 and self.topicTime.timestamp != 0):
                    loopTime = t
                    if (self.topicTime.timestamp > timestamp):
                        timestamp = self.topicTime.timestamp

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

                        waitObservation = True
                        while waitObservation:
                            scode = self.sal.getNextSample_observationTest(self.topicObservation)
                            t = time.time()
                            if (scode == 0 and self.topicObservation.targetId != 0):
                                loopTime = t
                                measCount += 1
                                visitCount += 1
                                if (self.topicTarget.targetId == self.topicObservation.targetId):
                                    syncCount += 1

                                    self.schedulerDriver.registerObservation(self.topicObservation)

                                    break
                                else:
                                    print("UNSYNC targetId=%i observationId=%i" % (self.topicTarget.targetId, self.topicObservation.targetId))
                            else:
                                if (t - loopTime > 10.0):
                                    waitObservation = False

                            newTime = time.time()
                            deltaTime = newTime - measTime
                            if (deltaTime >= measInterval):
                                rate = float(measCount)/deltaTime
                                print("rix %.0f visits/sec total=%i visits sync=%i" % (rate, visitCount, syncCount))
                                measTime = newTime
                                measCount = 0
                    else:
                        print("BACKWARD previous=%f new=%f" % (timestamp, self.topicTime.timestamp))

                else:
                    if (t - loopTime > 30.0):
                        waitConditions = False

                newTime = time.time()
                deltaTime = newTime - measTime
                if (deltaTime >= measInterval):
                    rate = float(measCount)/deltaTime
                    print("rx %.0f visits/sec total=%i visits sync=%i" % (rate, visitCount, syncCount))
                    measTime = newTime
                    measCount = 0

        except KeyboardInterrupt:
            self.sal.salShutdown()
            sys.exit(0)

