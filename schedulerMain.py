import sys
import time
import datetime

from SALPY_scheduler import *

sal = SAL_scheduler()
sal.setDebugLevel(0)

topicTime = scheduler_timeHandlerC()
sal.salTelemetrySub("scheduler_timeHandler")

measInterval = 1
stime = time.time()
count = 0
try:
	while True:
		ntime = time.time()
		dtime = ntime - stime
		if dtime >= measInterval:
			rate = float(count)/dtime
			print("rx %.0f msg/sec" % rate)
			stime = ntime
			count = 0
		scode = sal.getNextSample_timeHandler(topicTime)
		if scode == 0 and topicTime.timestamp != 0:
			count += 1
			#print("{}".format(datetime.datetime.fromtimestamp(topicTime.timestamp).isoformat()))

except KeyboardInterrupt:
    sal.salShutdown()
    sys.exit(0)

