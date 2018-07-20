import time
import threading
import logging

from SALPY_scheduler import SAL_scheduler, scheduler_logevent_targetC

 
class TargetProducer(threading.Thread):
    """TargetProducer is a utility class for the Scheduler_CSC's state machine. 

    The Target Producer class is created to delegate all thread related work 
    involved in retrieving Targets from the Driver. This frees the state machine
    State objects from the dirty tasks of handling threads.  
    """

    def __init__(self):
        threading.Thread.__init__(self)
 
        # Flag indicating to shut down the thread.
        self.start_flag = threading.Event()
        
        # Grab our logger, plus some booleans to help make useful logs in run()
        self.log = logging.getLogger("TargetProducer")
        self.first_pass = True
        self.log_switch = True

        self.mgr = SAL_scheduler()
        self.mgr.salEvent("scheduler_logevent_target")

    def run(self):
        while self.start_flag.wait():
            
            if self.log_switch:
                if self.first_pass:
                    self.log.info("run: Target production started")
                    self.first_pass = False
                    self.log_switch = False
                else:
                    self.log.info("run: Target production resumed")
                    self.log_switch = False    

            # TODO: Get real targets produced by the scheduler from the model
            myData = scheduler_logevent_targetC()
            myData.targetId=1
            myData.ra=1.2
            myData.decl=1.3
            myData.skyAngle=1.4
            myData.filter="y"
            myData.numExposures=2
            myData.exposureTimes[0] = 9.9
            myData.exposureTimes[1] = 9.9
            myData.exposureTimes[2] = 9.9
            myData.exposureTimes[3] = 9.9
            myData.exposureTimes[4] = 9.9
            myData.exposureTimes[5] = 9.9
            myData.exposureTimes[6] = 9.9
            myData.exposureTimes[7] = 9.9
            myData.exposureTimes[8] = 9.9
            myData.exposureTimes[9] = 9.9
            myData.slewTime=9.9
            myData.offsetX=9.9
            myData.offsetY=9.9
            myData.proposalId[0] = 2
            myData.proposalId[1] = 2
            myData.proposalId[2] = 2
            myData.proposalId[3] = 2
            myData.proposalId[4] = 2
            myData.isSequence=1
            myData.sequenceNVisits=1
            myData.sequenceVisits=1
            myData.sequenceDuration=9.9
            myData.priority=1
            priority=1
            self.mgr.logEvent_target(myData, priority)
            self.log.info("run: Producing Targets")
            time.sleep(0.5)

    def pause(self):
        self.log.info("run: Target production paused")
        self.start_flag.clear()
        self.log_switch = True
        # TODO: Calls on the model telling it to save whatever needs saving

    def produce_targets(self):
        # Threading module only allows start() to every be called once
        if self.isAlive():
            self.start_flag.set()
        else:
            self.start()
            self.start_flag.set()
