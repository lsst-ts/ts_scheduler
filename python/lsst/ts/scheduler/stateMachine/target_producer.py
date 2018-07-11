import time
import threading
import logging

from SALPY_scheduler import *

 
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
            myData.target_id=1
            myData.ra=1.2
            myData.decl=1.3
            myData.sky_angle=1.4
            myData.filter="y"
            myData.num_exposures=2
            myData.exposure_times[0] = 9.9
            myData.exposure_times[1] = 9.9
            myData.exposure_times[2] = 9.9
            myData.exposure_times[3] = 9.9
            myData.exposure_times[4] = 9.9
            myData.exposure_times[5] = 9.9
            myData.exposure_times[6] = 9.9
            myData.exposure_times[7] = 9.9
            myData.exposure_times[8] = 9.9
            myData.exposure_times[9] = 9.9
            myData.slew_time=9.9
            myData.offset_x=9.9
            myData.offset_y=9.9
            myData.proposal_id[0] = 2
            myData.proposal_id[1] = 2
            myData.proposal_id[2] = 2
            myData.proposal_id[3] = 2
            myData.proposal_id[4] = 2
            myData.is_sequence=1
            myData.sequence_n_visits=1
            myData.sequence_visits=1
            myData.sequence_duration=9.9
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