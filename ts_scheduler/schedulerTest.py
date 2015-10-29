import sys
import time
import datetime

from SALPY_scheduler import *

sal = SAL_scheduler()
sal.setDebugLevel(0)

topicTime           = scheduler_timeHandlerC()
topicObservation    = scheduler_observationTestC()
topicTarget         = scheduler_targetTestC()

sal.salTelemetryPub("scheduler_timeHandler")
sal.salTelemetryPub("scheduler_observationTest")
sal.salTelemetrySub("scheduler_targetTest")

start_date = "2010-10-01 16:28:00"
start_seconds = time.mktime(time.strptime(start_date, "%Y-%m-%d %H:%M:%S"))
delta_seconds = 40

#topicTime.timestamp = int(start_seconds)
topicTime.timestamp = time.time()

measInterval = 1
stime = time.time()
count = 0
totalcount = 0
observationId = 0
try:
    while True:
        sal.putSample_timeHandler(topicTime)

        while True:
            scode = sal.getNextSample_targetTest(topicTarget)
            if scode == 0 and topicTarget.targetId != 0:
                observationId += 1
                topicObservation.observationId = observationId
                topicObservation.targetId      = topicTarget.targetId

#                topicTime.timestamp += delta_seconds
                topicTime.timestamp = time.time()

                sal.putSample_observationTest(topicObservation)

                break

        ntime = time.time()
        dtime = ntime - stime
        if dtime >= measInterval:
            rate = float(count)/dtime
            print("tx %.0f msg/sec total=%i messages" % (rate, totalcount))
            stime = ntime
            count = 0
        count += 1
        totalcount += 1
        if (totalcount >= 300000):
            break

except KeyboardInterrupt:
    sal.salShutdown()
    sys.exit(0)

