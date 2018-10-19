import time
import logging

from lsst.ts.scheduler.sal_utils import SALUtils
from lsst.ts.scheduler.setup import WORDY
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.astrosky.model import AstronomicalSkyModel

from lsst.sims.seeingModel import SeeingModel
from lsst.sims.cloudModel import CloudModel
from lsst.sims.downtimeModel import ScheduledDowntime, UnscheduledDowntime

from scheduler_config.constants import CONFIG_DIRECTORY, CONFIG_DIRECTORY_PATH

try:
    from git import Repo
except ImportError:
    raise ImportError("gitpython not installed. Please install it with 'pip install gitpython' before proceeding.")

DEFAULT_STATE = "OFFLINE"

__all__ = ['Model']


class Model:
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
    def __init__(self):
        """The Model object is planned to be configurable by a method TODO:

            The Model is the highest level interface for the State Machine to interact
            with. The Scheduler State Machine has multiple states. Rather than having
            to import many objects from different locations we import this Model object.
            Allowing the Scheduler State Machine one unified object to make all its
            calls from.

        """
        self._current_state = DEFAULT_STATE
        self._previous_state = DEFAULT_STATE

        self.log = logging.getLogger("schedulerModel")
        # FIXME options arg removed from init, hardcoded value to be set with method in future release.
        self.sal = SALUtils(2000)  # FIXME: This is probably going away with salobj
        self.configuration_path = str(CONFIG_DIRECTORY)
        self.configuration_repo = Repo(str(CONFIG_DIRECTORY_PATH))
        self.current_setting = str(self.configuration_repo.active_branch)
        self.valid_settings = self.read_valid_settings()

        self.models = {}  # Dictionary to host all the available models.
        self.raw_telemetry = {}  # Dictionary to host all required telemetry from the models.

        self.driver = None  # This will be setup during the configuration procedure

    def sal_start(self):  # FIXME: This is probably something that should go on the CSC
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
        """Publish valid settings over SAL and return a string with a list of valid settings.

        Returns
        -------
            valid_settings: string: Comma delimited string of available branches for configuring.
                This contains the short branch name. For example 'master' rather than 'origin/master'.

        """
        valid_settings = ''
        for setting in self.valid_settings[:-1]:
            valid_settings += setting[setting.find('/') + 1:]
            valid_settings += ','
        valid_settings += self.valid_settings[-1][self.valid_settings[-1].find('/') + 1:]

        self.sal.topicValidSettings.packageVersions = valid_settings
        self.sal.logEvent_validSettings(self.sal.topicValidSettings, 5)

        return valid_settings

    def init_models(self):
        """Initialize scheduler models. They will be initialized but not configured.

        Returns
        -------

        """
        self.models['location'] = ObservatoryLocation()
        self.models['observatory_model'] = ObservatoryModel(self.models['location'], WORDY)
        self.models['observatory_state'] = ObservatoryState()
        self.models['sky'] = AstronomicalSkyModel(self.models['location'])
        self.models['seeing'] = SeeingModel()
        # FIXME: I'll leave cloud model out for now as we need to flush out the cloud model.
        # self.models['cloud'] = CloudModel()
        self.models['scheduled_downtime'] = ScheduledDowntime()
        self.models['unscheduled_downtime'] = UnscheduledDowntime()

        # Fixme: The list of raw telemetry should be something that the models return, plus some additional standard
        # telemetry like time.
        # Observatory Time. This is NOT observation time. Observation time will be derived from observatory time by
        # the scheduler and will aways be in the future.
        self.raw_telemetry['timeHandler'] = None
        self.raw_telemetry['observatoryState'] = None  # Observatory State
        self.raw_telemetry['bulkCloud'] = None  # Transparency measurement
        self.raw_telemetry['seeing'] = None  # Seeing measurement

    def update_telemetry(self):
        """ Update data on all the telemetry values.

        Returns
        -------
        None

        """
        pass

    def put_on_queue(self, targets, position=None):
        """ Given a list of targets, put them on the queue to be observed. By default targets are appended to the
        queue. An optional position argument is available and specify the position on the queue. Position can either
        be a single integer number or a list. If an integer, the position is considered to be for the first target on
        the list. If a list, it must have the same number of elements as targets.

        Parameters
        ----------
        targets: list(Targets): A list of targets to put on the queue.
        position: int or list(int): Position of the targets on the queue. By default (None) append to the queue.

        Returns
        -------

        """
        pass

    def configure(self, setting):
        """This method is responsible for configuring the scheduler models and the scheduler algorithm, given the
        input setting. It will raise an exception if the input setting is not valid.

        Parameters
        ----------
        setting: string: A valid setting from the the `read_valid_settings` method.

        Returns
        -------
        None

        """
        pass

    def configure_driver(self):
        """Load driver for selected scheduler and configure its basic parameters.

        Returns
        -------

        """
        pass

    def configure_scheduler(self):
        """Configure driver scheduler and publish survey topology.

        Returns
        -------

        """
        survey_topology = self.driver.configure_scheduler(config=self.config,
                                                          config_path=self.configuration_path)

        # FIXME: use salobj to publish survey topology
        # self.sal.topic_schedulerTopology = survey_topology.to_topic()
        # self.sal.putSample_surveyTopology(self.sal.topic_schedulerTopology)

    def run(self):
        """ This is the method that runs when the system is in enable state. It is responsible for the target
        production loop, updating telemetry, requesting targets from the driver to build a queue and filling
        the queue with targets.

        Returns
        -------

        """
        pass
