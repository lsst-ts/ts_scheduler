import sys
import time
import datetime

from SALPY_scheduler import *

sal = SAL_scheduler()
sal.setDebugLevel(0)

topicTime = scheduler_timeHandlerC()
sal.salTelemetryPub("scheduler_timeHandler")

start_date = "2010-10-01 16:28:00"
start_seconds = time.mktime(time.strptime(start_date, "%Y-%m-%d %H:%M:%S"))
delta_seconds = 40

topicTime.timestamp = int(start_seconds)

measInterval = 1
stime = time.time()
count = 0
try:
    while True:
        ntime = time.time()
        dtime = ntime - stime
        if dtime >= measInterval:
            rate = float(count)/dtime
            print("tx %.0f msg/sec" % rate)
            stime = ntime
            count = 0
        sal.putSample_timeHandler(topicTime)
        topicTime.timestamp += delta_seconds
        count += 1
        #print("{}".format(datetime.datetime.fromtimestamp(topicTime.timestamp).isoformat()))
except KeyboardInterrupt:
    sal.salShutdown()
    sys.exit(0)

