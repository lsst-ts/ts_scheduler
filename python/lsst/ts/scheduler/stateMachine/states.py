""" For more documentation on the Scheduler CSC states, visit 
https://docs.google.com/document/d/1DTzgfP_HeBgQ8PC7klwInj4XehC03ckxc85KBW38kKY/edit

When transitioning from a state the following is called;

1) [current state].exit()
    
    For example this could be OfflineState.exit()
    
2) [current state].[command]

    For example, were we currently in StandbyState there would be two
    possibilites. Standby.exit_control() or Standby.start().

3) [new state].do()
    
    Here we call all methods that we want to call when transition into the state.
    If there is behavior we wish to have that is specific from a certain state
    we can ask mode.previous_state.
"""

from lsst.ts.statemachine import states 
from lsst.ts.scheduler.stateMachine import TargetProducer

class OfflineState(states.OfflineState):


    def __init__(self, subsystem_tag):
        super(OfflineState, self).__init__(subsystem_tag)


class StandbyState(states.StandbyState):

    def __init__(self, subsystem_tag):
        super(StandbyState, self).__init__(subsystem_tag)

    def do(self, model):

        if model.previous_state == "OFFLINE":
            model.send_valid_settings()


class DisabledState(states.DisabledState):

    def __init__(self, subsystem_tag):
        super(DisabledState, self).__init__(subsystem_tag)


class EnabledState(states.EnabledState):

    def __init__(self, subsystem_tag):
        super(EnabledState, self).__init__(subsystem_tag)

        self.target_producer = TargetProducer()

    def do(self, model):
        
        # Begin the target production thread
        self.target_producer.produce_targets()

    def exit(self, model):
        # Exiting Enable, pause the thread, we don't know if we want to kill yet
        self.target_producer.pause()


class FaultState(states.FaultState):

    def __init__(self, subsystem_tag):
        super(FaultState, self).__init__(subsystem_tag)
