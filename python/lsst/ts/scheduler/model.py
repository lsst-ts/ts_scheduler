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
    """A class that contains that contains the necessary attributes and methods
    for a statemachine to control the Scheduling algorith.

    Parameters
    ----------
    driver : ``module``
        Optional driver for the Model to use. This allows external developers
        to plug in thier own scheduling algorithms. External Driver's must
        comply with the the Driver interface here 
        https://docs.google.com/document/d/1wQ467QGqVP2e4iXOKcW2slLMgOzI_1Qk284b1gDGqaI

    Notes
    -----
    The Model is the highest level interface for the State Machine to interact
    with. The Scheduler State Machine has multiple states. Rather than having
    to import many objects from different locations we import this Model object.
    Allowing the Scheduler State Machine one unified object to make all its
    calls from.
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
