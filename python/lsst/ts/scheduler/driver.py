from builtins import object
import logging
import time
import yaml

from lsst.ts.scheduler.kernel import SurveyTopology
from lsst.ts.scheduler.setup import WORDY

from lsst.ts.observatory.model import Target

import lsst.pex.config as pexConfig

from SALPY_Scheduler import Scheduler_logevent_targetC

__all__ = ["Driver", "DriverParameters"]


class DriverTarget(Target):
    """This class provides a wrapper around `lsst.ts.observatory.model.Target` to add utility
    methods used by the Scheduler. The base class itself provides utility methods to interface
    with the observatory model. The methods added here are scheduler-specific, hence the need
    to subclass.

    Parameters
    ----------
    targetid : int
        A unique identifier for the given target.
    fieldid : int
        The ID of the associated OpSim field for the target.
    band_filter : str
        The single character name of the associated band filter.
    ra_rad : float
        The right ascension (radians) of the target.
    dec_rad : float
        The declination (radians) of the target.
    ang_rad : float
        The sky angle (radians) of the target.
    num_exp : int
        The number of requested exposures for the target.
    exp_times : list[float]
        The set of exposure times (seconds) for the target. Needs to length
        of num_exp.

    """
    def __init__(self, sal_index=0, targetid=0, fieldid=0, band_filter="",
                 ra_rad=0.0, dec_rad=0.0, ang_rad=0.0,
                 num_exp=0, exp_times=[]):
        self.sal_index = sal_index
        super().__init__(targetid=targetid, fieldid=fieldid, band_filter=band_filter, ra_rad=ra_rad,
                         dec_rad=dec_rad, ang_rad=ang_rad, num_exp=num_exp, exp_times=exp_times)

        # TODO: This method might need to be expanded in the future. Keeping it here as
        # placeholder for now.

    def get_script_config(self):
        """Returns a yaml string representation of a dictionary with the configuration to be
        used for the observing script.

        Returns
        -------
        config_str: str
        """
        script_config = {'targetid': self.targetid,
                         'band_filter': self.filter,
                         'ra': self.ra,
                         'dec': self.dec,
                         'ang': self.ang,
                         'num_exp': self.num_exp,
                         'exp_times': self.exp_times}

        return yaml.safe_dump(script_config)

    def as_evt_topic(self):
        """Returns a SAL target topic with the Target information.

        Returns
        -------
        topic_target: `SALPY_Scheduler.Scheduler_logevent_targetC`

        """
        topic_target = Scheduler_logevent_targetC()

        topic_target.targetId = self.targetid
        topic_target.filter = self.filter
        topic_target.requestTime = self.time
        topic_target.ra = self.ra
        topic_target.decl = self.dec
        topic_target.skyAngle = self.ang
        topic_target.numExposures = self.num_exp
        for i, exptime in enumerate(self.exp_times):
            topic_target.exposureTimes[i] = int(exptime)
        topic_target.airmass = self.airmass
        topic_target.skyBrightness = self.sky_brightness
        topic_target.cloud = self.cloud
        topic_target.seeing = self.seeing
        topic_target.slewTime = self.slewtime
        topic_target.numProposals = self.num_props
        for i, prop_id in enumerate(self.propid_list):
            topic_target.proposalId[i] = prop_id
        topic_target.note = self.note

        return topic_target


class DriverParameters(pexConfig.Config):
    """Actual global driver configuration parameters.

    This can be expanded for other scheduler drivers. For instance, if your scheduler uses a certain
    configuration file it is possible to subclass this and add the required parameters (e.g. file paths
    or else). Then, replace `self.params` on the Driver by the subclassed configuration.
    """
    pass


class Driver(object):
    """The Scheduler Driver is the module that normalizes the interface between any scheduling algorithm
    to the LSST Scheduler CSC. The interface implements three main behaviours; configure an underlying
    algorithm, request targets and register successful observations.

    If the Scheduler algorithm requires a specific set of parameters the user must subclass
    `DriverParameters`, in the same module as the `Driver`, and add the appropriate parameters using
    the LSST pexConfig module.

    Access to the telemetry stream and models are also interfaced by `Driver`. The full list of default
    available telemetry data is shown in the scheduler_csc module. Nevertheless, the full list of telemetry
    may vary depending on the models used. The user has control over this while configuring the
    Scheduler CSC.

    Parameters
    ----------
    models: `dict`
        A dictionary with models available for the scheduling algorithm.
    raw_telemetry: `dict`
        A dictionary with available raw telemetry.
    """
    def __init__(self, models, raw_telemetry, parameters=None):
        self.log = logging.getLogger("schedulerDriver")

        if parameters is None:
            self.parameters = DriverParameters()
        else:
            self.parameters = parameters
        self.models = models
        self.raw_telemetry = raw_telemetry
        self.targetid = 0

    def configure_scheduler(self):
        """This method is responsible for running the scheduler configuration and returning the
        survey topology, which specifies the number, name and type of projects running by the scheduler.

        By default it will just return a test survey topology.

        Returns
        -------
        survey_topology: `lsst.ts.scheduler.kernel.SurveyTopology`

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

        By default it will just return a dummy test target.

        Returns
        -------
        Target

        """
        self.log.log(WORDY, 'Selecting next target.')

        self.targetid += 1
        target = DriverTarget(targetid=self.targetid)

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
        self.log.log(WORDY, 'Registering observation %s.', observation)

        return [observation]
