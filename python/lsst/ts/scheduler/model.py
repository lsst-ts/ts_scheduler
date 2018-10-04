import time
import logging

from lsst.ts.scheduler import Driver
from lsst.ts.scheduler.sal_utils import SALUtils

from SALPY_scheduler import SAL_scheduler, scheduler_logevent_validSettingsC
from scheduler_config.constants import CONFIG_DIRECTORY, CONFIG_DIRECTORY_PATH

try:
    from git import Repo
except ImportError:
    raise ImportError("gitpython not installed. Please install it with 'pip install gitpython' before proceeding.")

DEFAULT_STATE = "OFFLINE"

class Model():
    """The model contains all business logic related to the scheduler.

    The Model class is designed to solely interact with an interface object
    called Driver. This is so that we can "plug and play" different scheduling
    algorithms as long as they can interact with the Driver. Most of the methods
    called on this class are called by the state machine, assuming we are in
    operations mode. In order for any model to interact with the state machine
    from salpytools it must have an attribute "state". The "state" attribute is
    used to store the current state of the state machine.
    """

    def __init__(self, options=None, driver = Driver()):
        self.log = logging.getLogger("schedulerModel")

        self.sal = None

        self._current_state = DEFAULT_STATE
        self._previous_state = DEFAULT_STATE

        self.configuration_path = None
        self.configuration_repo = None
        self.current_setting = None
        self.valid_settings = None
        
        if options is None:
            self.initialize_with_default()
        else:
            self.initialize_with_options(options)

        self.sal.start()

    def initialize_with_default(self):
        self.sal = SALUtils(2000)
        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))
        self.current_setting = str(self.configuration_repo.active_branch)
        
        remote_branches = []
        for ref in self.configuration_repo.git.branch('-r').split('\n'):
            if 'HEAD' not in ref:
                remote_branches.append(ref)

        self.valid_settings = remote_branches

    def initialize_with_options(self, options):
        self.sal = SALUtils(options.timeout)
        self.current_setting = "default"

    @property
    def current_state(self):
        return self._current_state

    @property
    def previous_state(self):
        return self._previous_state
    
    @current_state.setter()
    def _current_state(self, state):
        # TODO: Some actual handing on the state changing mechanism. 
        self._previous_state = self._current_state
        self._current_state = state

    def send_valid_settings(self):
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        self.sal.topicValidSettings.packageVersions = valid_settings
        self.sal.logEvent_validSettings(self.sal.topicValidSettings, 5)

        return valid_settings
