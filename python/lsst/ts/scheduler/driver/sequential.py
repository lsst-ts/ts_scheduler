import os
import yaml

import lsst.pex.config as pex_config

from .driver import Driver, DriverParameters, DriverTarget


__all__ = ["SequentialParameters", "SequentialScheduler"]


class SequentialTarget(DriverTarget):

    def __init__(self, config, targetid=0):
        super().__init__(targetid=targetid)
        self.config = config

    def get_script_config(self):
        """Returns a yaml string representation of a dictionary with the
        configuration to be used for the observing script.

        Returns
        -------
        config_str: str
        """

        return yaml.safe_dump(self.config)


class SequentialParameters(DriverParameters):
    """Sequential driver parameters.

    Notes
    -----

    Example of a yaml configuration.

    target1:
        ra: 12:00:00
        dec: -10:00:00
        name: tile1
        exptimes:
            - 15.
            - 15.
        filters:
            - r
            - r
    target2:
        ra: 12:00:00
        dec: -13:30:00
        name: tile2
        exptimes:
            - 15.
            - 15.
        filters:
            - r
            - r
    target3:
        name: m104
        exptimes:
            - 15.
            - 15.
        filters:
            - r
            - r

    """
    observing_list = pex_config.Field("File with the list of targets to observe with the "
                                      "configuration.",
                                      str)


class SequentialScheduler(Driver):
    """ A simple scheduler driver that implements a sequential scheduler
    algorithm.

    The driver reads from an input file of targets provided by the user and
    send one target at a time.

    """

    def __init__(self, models, raw_telemetry, parameters=None):

        self.observing_list_dict = None

        super().__init__(models, raw_telemetry, parameters)

    def configure_scheduler(self, config=None):
        """This method is responsible for running the scheduler configuration
        and returning the survey topology, which specifies the number, name
        and type of projects running by the scheduler.

        By default it will just return a test survey topology.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by ``schema/Scheduler.yaml``

        Returns
        -------
        survey_topology: `lsst.ts.scheduler.kernel.SurveyTopology`

        """

        if not hasattr(config, "observing_list"):
            raise RuntimeError("No observing list provided in configuration.")

        if not os.path.exists(config.observing_list):
            raise RuntimeError(f"Observing list {config.observing_list} not found.")

        with open(config.observing_list, "r") as f:
            config_yaml = f.read()

        self.observing_list_dict = yaml.safe_load(config_yaml)

        self.log.debug(f"Got {len(self.observing_list_dict)} objects.")

        return super().configure_scheduler(config)

    def cold_start(self, observations):
        """Rebuilds the internal state of the scheduler from a list of
        observations.

        Parameters
        ----------
        observations : list of Observation objects

        """
        raise RuntimeError("Cold start not supported by SequentialScheduler.")

    def select_next_target(self):
        """Picks a target and returns it as a target object.

        By default it will just return a dummy test target.

        Returns
        -------
        Target

        """
        self.targetid += 1

        target = SequentialTarget(
            config=self.observing_list_dict.pop(list(self.observing_list_dict.keys())[0]),
            targetid=self.targetid
        )

        return target
