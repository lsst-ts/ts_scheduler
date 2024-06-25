# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["SchedulerCscParameters"]

from dataclasses import dataclass


@dataclass
class SchedulerCscParameters:
    """Configuration of the LSST Scheduler's Model."""

    driver_type: str = "driver"
    # Choose a driver to use. This should be an import string that
    # is passed to `importlib.import_module()`. Model will look for
    # a subclass of Driver class inside the module.

    night_boundary: float = -12.0
    # Solar altitude (degrees) when it is considered night.

    new_moon_phase_threshold: float = 20.0
    # New moon phase threshold for swapping to dark time filter.

    startup_type: str = "HOT"
    # The method used to startup the scheduler.
    # allowed:
    # HOT: Hot start, this means the scheduler is started up from scratch
    # WARM: Reads the scheduler state from a previously saved internal state.
    # COLD: Rebuilds scheduler state from observation database.

    startup_database: str = ""
    # Path to the file holding scheduler state or observation database to be
    # used on WARM or COLD start.

    mode: str = "SIMPLE"
    # The mode of operation of the scheduler. This basically chooses one of the
    # available target production loops.
    # allowed={
    #     "SIMPLE": "The Scheduler will publish one target at a "
    #     "time, no next target published in advance "
    #     "and no predicted schedule.",
    #     "ADVANCE": "The Scheduler will pre-compute a predicted "
    #     "schedule that is published as an event and "
    #     "will fill the queue with a specified "
    #     "number of targets. The scheduler will then "
    #     "monitor the telemetry stream, recompute the "
    #     "queue and change next target up to a "
    #     "certain lead time.",
    # },

    n_targets: int = 1
    # Number of targets to put in the queue ahead of time.

    predicted_scheduler_window: float = 2.0
    # Size of predicted scheduler window, in hours.

    loop_sleep_time: float = 1.0
    # How long should the target production loop wait when there is a wait
    # event. Unit = seconds.

    cmd_timeout: float = 60.0
    # Global command timeout. Unit = seconds

    observing_script: str = "standard_visit.py"
    # Name of the observing script.

    observing_script_is_standard: bool = True
    # Is observing script standard?

    max_scripts: int = 100
    # Maximum number of scripts to keep track of.

    def set_defaults(self):
        """Set defaults for the LSST Scheduler's Driver."""
        self.driver_type = "driver"
        self.startup_type = "HOT"
        self.startup_database = ""
        self.mode = "SIMPLE"
        self.n_targets = 1
        self.predicted_scheduler_window = 2.0
        self.loop_sleep_time = 1.0
        self.cmd_timeout = 60.0
        self.observing_script = "standard_visit.py"
        self.observing_script_is_standard = True
        self.max_scripts = 100
