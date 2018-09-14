import time
from SALPY_scheduler import SAL_scheduler, scheduler_logevent_validSettingsC

DEFAULT_STATE = "OFFLINE"

class Model():
    """The model contains all business logic related to the scheduler.

    The Model class is designed to solely interact with an interface object
    called Driver. This is so that we can "plug and play" different scheduling
    algorithms as long as they can interact with the Driver. Most of the methods
    called on this class are called by the state machine, assuming we are in
    operations mode. In order for any model to interact with the state machine
    from ts_statemachine it must have an attribute "state". The "state" attribute is
    used to store the current state of the state machine.
    """

    def __init__(self):

        self.state = DEFAULT_STATE
        self.previous_state = self.state

        self.mgr = SAL_scheduler()

    def change_state(self, state):

        self.previous_state = self.state
        self.state = state

    def send_valid_settings(self):
        # This function could be part of a utility class. The important thing is
        # that the states contain no logic, all it does is call Model methods
        # TODO: Get real valid settings from the model
        mgr = SAL_scheduler()
        mgr.salEvent("scheduler_logevent_validSettings")
        myData = scheduler_logevent_validSettingsC()
        myData.package="package"
        myData.packageVersions="packageVersions"
        myData.aliases="aliases"
        myData.priority=1
        priority=int(myData.priority)
        mgr.logEvent_validSettings(myData, priority)
        time.sleep(1)
        mgr.salShutdown()
