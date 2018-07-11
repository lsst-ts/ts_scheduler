from salpytools import salpylib

from lsst.ts.scheduler import Model
from lsst.ts.scheduler.stateMachine import states

class Scheduler_CSC():
    """The Scheduler_CSC ties together the Context and our modelself.

    The Context handles the state machine. The Model handles all the business
    logic of our application. By giving our Context access to the Model we can
    implement individual state level behavior to make calls on the Model.
    """
    def __init__(self):

        self.model = Model()
        self.subsystem_tag = 'scheduler'
        self.states = {"OFFLINE" : states.OfflineState(self.subsystem_tag),
                       "STANDBY" : states.StandbyState(self.subsystem_tag),
                       "ENABLED" : states.EnabledState(self.subsystem_tag),
                       "DISABLED": states.DisabledState(self.subsystem_tag),
                       "FAULT"   : states.FaultState(self.subsystem_tag)}

        self.context = salpylib.Context(self.subsystem_tag, self.model, states=self.states)

        self.enter_control = salpylib.DDSController(self.context, 'enterControl')
        self.start = salpylib.DDSController(self.context, 'start')
        self.enable = salpylib.DDSController(self.context, 'enable')
        self.disable = salpylib.DDSController(self.context, 'disable')
        self.standby = salpylib.DDSController(self.context, 'standby')
        self.exit_control = salpylib.DDSController(self.context, 'exitControl')

        self.enter_control.start()
        self.start.start()
        self.enable.start()
        self.disable.start()
        self.standby.start()
        self.exit_control.start()