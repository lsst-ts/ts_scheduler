import sys
import time
import datetime

from SALPY_scheduler import *

sal = SAL_scheduler()
sal.setDebugLevel(0)

topicTime           = scheduler_timeHandlerC()
topicObservation    = scheduler_observationTestC()
topicTarget         = scheduler_targetTestC()

sal.salTelemetrySub("scheduler_timeHandler")
sal.salTelemetrySub("scheduler_observationTest")
sal.salTelemetryPub("scheduler_targetTest")

measInterval = 1

measCount  = 0
visitCount = 0
syncCount  = 0
targetId   = 0

stime = time.time()
try:
    while True:
        scode = sal.getNextSample_timeHandler(topicTime)
        if scode == 0 and topicTime.timestamp != 0:

            time.sleep(0.030)
            targetId += 1

            topicTarget.targetId = targetId
            topicTarget.fieldId  = 1234
            topicTarget.filter   = "z"
            topicTarget.ra       = 10.0
            topicTarget.dec      = 30.0
            topicTarget.angle    = 45.0
            topicTarget.num_exposures = 2
            sal.putSample_targetTest(topicTarget)

            while True:
                scode = sal.getNextSample_observationTest(topicObservation)
                if scode == 0 and topicObservation.targetId != 0:
                    measCount += 1
                    visitCount += 1
                    if topicTarget.targetId == topicObservation.targetId:
                        syncCount += 1
                        break
                    else:
                        print("UNSYNC targetId=%i observationId=%i" % (topicTarget.targetId, topicObservation.targetId))

        ntime = time.time()
        dtime = ntime - stime
        if dtime >= measInterval:
            rate = float(measCount)/dtime
            print("rx %.0f vitis/sec total=%i visits sync=%i" % (rate, visitCount, syncCount))
            stime = ntime
            measCount = 0

except KeyboardInterrupt:
    sal.salShutdown()
    sys.exit(0)

