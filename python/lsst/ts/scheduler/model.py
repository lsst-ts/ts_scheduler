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

    The purpose of the model is to wrap all functionality that the Scheduler
    Commandable Sal Component (Scheduler CSC) needs. This is so that in our 
    State machine we are not importing an arbitrary amount of packages an
    libraries. Rather we import this Model class and obtain all functionality. 
    """

    def __init__(self, driver = Driver()):
        self._current_state = DEFAULT_STATE
        self._previous_state = DEFAULT_STATE

        self.log = logging.getLogger("schedulerModel")
        self.sal = SALUtils(2000)
        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))
        self.current_setting = str(self.configuration_repo.active_branch)
        self.valid_settings = self.read_valid_settings()

    def sal_start(self):
        self.sal.start()

    def read_valid_settings(self):
        self.current_setting = str(self.configuration_repo.active_branch)
        remote_branches = []
        for ref in self.configuration_repo.git.branch('-r').split('\n'):
            if 'HEAD' not in ref:
                remote_branches.append(ref)

        return remote_branches

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, state):
        # TODO: Some actual handing on the state changing mechanism. 
        self._previous_state = self._current_state
        self._current_state = state

    @property
    def previous_state(self):
        return self._previous_state

    def send_valid_settings(self):
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        self.sal.topicValidSettings.packageVersions = valid_settings
        self.sal.logEvent_validSettings(self.sal.topicValidSettings, 5)

        return valid_settings
