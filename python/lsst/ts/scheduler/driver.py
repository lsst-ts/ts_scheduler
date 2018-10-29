from builtins import object
import logging

from lsst.ts.scheduler.kernel import SurveyTopology

from lsst.ts.observatory.model import Target

import lsst.pex.config as pexConfig

__all__ = ["Driver", "DriverParameters"]


class DriverParameters(pexConfig.Config):
    """Actual global driver configuration parameters.

    This can be expanded for other scheduler drivers. For instance, if your scheduler uses a certain configuration file
    it is possible to subclass this and add the required parameters (e.g. file paths or else). Then, replace
    self.params on the Driver by the subclassed configuration.
    """
    pass

class Driver(object):
    def __init__(self, models, raw_telemetry, params=None):
        """Initialize base scheduler driver.

        Parameters
        ----------
        models: A dictionary with models available for the scheduling algorithm.
        raw_telemetry: A dictionary with available raw telemetry.
        """
        self.log = logging.getLogger("schedulerDriver")

        if params is None:
            self.params = DriverParameters()
        else:
            self.params = params
        self.models = models
        self.raw_telemetry = raw_telemetry

    def configure_scheduler(self):
        """

        Parameters
        ----------
        config_name : The name of the file with the scheduler configuration.
        config_path : The path to the scheduler configuration.
        kwargs : Optional keyword arguments for the scheduler algorithm.

        Returns
        -------

        """
        survey_topology = SurveyTopology()

        survey_topology.num_general_props = 1
        survey_topology.general_propos = ["Test"]
        survey_topology.num_seq_props = 0
        survey_topology.sequence_propos = []

        return survey_topology

    def cold_start(self, observations):
        """Rebuilds the internal state of the scheduler from a list of observations.

        Parameters
        ----------
        observations : list of Observation objects

        Returns
        -------
        None
        """
        raise NotImplemented

    def update_conditions(self):
        """

        Returns
        -------

        """
        pass

    def select_next_target(self):
        """Picks a target and returns it as a target object.

        Parameters
        ----------
        None

        Returns
        -------
        Target
        """

        target = Target()

        target.targetid = 0
        target.num_exp = 2
        target.exp_times = [15.0, 15.0]
        target.num_props = 1
        target.propid_list = [0]

        return target

    def register_observation(self, observation):
        """Validates observation and returns a list of successfully completed observations.

        Parameters
        ----------
        observation : Observation or a python list of Observations

        Returns
        -------
        Python list of one or more Observations
        """

        return [observation]
