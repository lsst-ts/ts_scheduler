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
    """Model contains the attributes and methods to control the Scheduling algorithm.

    Attributes:
        _current_state (str): Current state of the model.
        _previous_state (str): Previous state of the model, needed to determine
            actions that require knoewledge of the state the model trasnitions
            out of.
        log (logging.Logger): Logger for the Scheduler Model.
        sal (SALPY_scheduler.SAL_scheduler.SALUtils): Utility class for
            middleware communication capabilities.
        configuration_path (str): Directory path for configuration files.
        configuration_repo (str): Comma delimmited string of available branches
            for configuring. This contains the full branch name.
        current_setting (str): Current setting, defaults to the active branch on
            the configuration_repo.
        valid_settings (str): Comma delimmited string of available branches
            for configuring. This contains the short branch name. For example
            'master' rather than 'origin/master'.

    """
    def __init__(self, driver = Driver()):
        """The Model object is planned to be configurable by a method TODO:

        Note:
            The Model is the highest level interface for the State Machine to interact
            with. The Scheduler State Machine has multiple states. Rather than having
            to import many objects from different locations we import this Model object.
            Allowing the Scheduler State Machine one unified object to make all its
            calls from.

        Args:
            driver (:obj:`Driver()`, optional): Externally provided Drivers must
                comply with the Driver interface here
                https://docs.google.com/document/d/1wQ467QGqVP2e4iXOKcW2slLMgOzI_1Qk284b1gDGqa.
                Current Driver can be found in lsst.ts.scheduler.Driver

        """
        self._current_state = DEFAULT_STATE
        self._previous_state = DEFAULT_STATE

        self.log = logging.getLogger("schedulerModel")
        self.sal = SALUtils(2000)
        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))
        self.current_setting = str(self.configuration_repo.active_branch)
        self.valid_settings = self.read_valid_settings()

    def sal_start(self):
        """Initializes SAL communication.

        Note:
            SAL communication is not initialized within our init function so
            that we may test various methods that do not require SAL
            communication.

        """
        self.sal.start()

    def read_valid_settings(self):
        """Reads the branches on the configuration repo and preps them.

        Returns:
            List of branches on the configuration repository. A single branch
            represents a valid setting.

        """
        remote_branches = []
        for ref in self.configuration_repo.git.branch('-r').split('\n'):
            if 'HEAD' not in ref:
                remote_branches.append(ref)

        return remote_branches

    @property
    def current_state(self):
        """str: Represents the current state of the model.

        When changed the previous_state becomes the current state.
        """
        return self._current_state

    @current_state.setter
    def current_state(self, state):
        # TODO: Some actual handing on the state changing mechanism.
        self._previous_state = self._current_state
        self._current_state = state

    @property
    def previous_state(self):
        """str: Represents the previous state of the model.

        Before current_state is updated, the previous_state becomes the
        current_state.
        """
        return self._previous_state

    def send_valid_settings(self):
        """Sends the valid settings over SAL.

        Returns:
            Comma delimmited string of available branches for configuring.
            This contains the short branch name. For example 'master' rather
            than 'origin/master'.

        """
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        self.sal.topicValidSettings.packageVersions = valid_settings
        self.sal.logEvent_validSettings(self.sal.topicValidSettings, 5)

        return valid_settings
