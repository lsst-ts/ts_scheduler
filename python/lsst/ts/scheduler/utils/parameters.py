# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
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

__all__ = ["SchedulerCscParameters"]

import lsst.pex.config as pex_config


class SchedulerCscParameters(pex_config.Config):
    """Configuration of the LSST Scheduler's Model."""

    driver_type = pex_config.Field(
        "Choose a driver to use. This should be an import string that "
        "is passed to `importlib.import_module()`. Model will look for "
        "a subclass of Driver class inside the module.",
        str,
        default="lsst.ts.scheduler.driver.driver",
    )
    night_boundary = pex_config.Field(
        "Solar altitude (degrees) when it is considered night.", float
    )
    new_moon_phase_threshold = pex_config.Field(
        "New moon phase threshold for swapping to dark time filter.", float
    )
    startup_type = pex_config.ChoiceField(
        "The method used to startup the scheduler.",
        str,
        default="HOT",
        allowed={
            "HOT": "Hot start, this means the scheduler is started up from scratch",
            "WARM": "Reads the scheduler state from a "
            "previously saved internal state.",
            "COLD": "Rebuilds scheduler state from " "observation database.",
        },
    )
    startup_database = pex_config.Field(
        "Path to the file holding scheduler state or observation "
        "database to be used on WARM or COLD start.",
        str,
        default="",
    )
    mode = pex_config.ChoiceField(
        "The mode of operation of the scheduler. This basically chooses "
        "one of the available target production loops. ",
        str,
        default="SIMPLE",
        allowed={
            "SIMPLE": "The Scheduler will publish one target at a "
            "time, no next target published in advance "
            "and no predicted schedule.",
            "ADVANCE": "The Scheduler will pre-compute a predicted "
            "schedule that is published as an event and "
            "will fill the queue with a specified "
            "number of targets. The scheduler will then "
            "monitor the telemetry stream, recompute the "
            "queue and change next target up to a "
            "certain lead time.",
        },
    )
    n_targets = pex_config.Field(
        "Number of targets to put in the queue ahead of time.", int, default=1
    )
    predicted_scheduler_window = pex_config.Field(
        "Size of predicted scheduler window, in hours.", float, default=2.0
    )
    loop_sleep_time = pex_config.Field(
        "How long should the target production loop wait when "
        "there is a wait event. Unit = seconds.",
        float,
        default=1.0,
    )
    cmd_timeout = pex_config.Field(
        "Global command timeout. Unit = seconds.", float, default=60.0
    )
    observing_script = pex_config.Field(
        "Name of the observing script.", str, default="standard_visit.py"
    )
    observing_script_is_standard = pex_config.Field(
        "Is observing script standard?", bool, default=True
    )
    max_scripts = pex_config.Field(
        "Maximum number of scripts to keep track of.", int, default=100
    )

    def set_defaults(self):
        """Set defaults for the LSST Scheduler's Driver."""
        self.driver_type = "lsst.ts.scheduler.driver.driver"
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
