.. :changelog:

History
-------

1.0   (2017-02-28)
==================

* Deep Drilling extension
#	modified:   python/lsst/ts/scheduler/proposals/sequence.py
#	modified:   python/lsst/ts/scheduler/proposals/subsequence.py
#	modified:   python/lsst/ts/scheduler/proposals/time_distribution.py
#	modified:   python/lsst/ts/scheduler/driver.py
#	modified:   python/lsst/ts/scheduler/kernel/target.py
    New extensions to the code to support Deep Drilling
    new target.sequenceid is fieldid for now
    new target.subsequencename is the sub-sequence name
    target.groupid is reused as event counter
    target.groupix is reused as subevent (filter) counter
    new target.remaining_dd_visits is regresive counter for total visits in the event

    Reduced log verbosity at level -v

0.9.0 (2017-02-23)
==================

* Time Distribution Proposal
#	python/lsst/ts/scheduler/proposals/sequence.py
#	python/lsst/ts/scheduler/proposals/subsequence.py
#	python/lsst/ts/scheduler/proposals/time_distribution.py
    New code to implement time distribution.
    Sequence observation with multiple subsequences as children

#	modified:   python/lsst/ts/scheduler/main.py
#	modified:   python/lsst/ts/scheduler/driver.py
    Extended to instantiate the time distribution proposals from config

#	modified:   python/lsst/ts/scheduler/fields/field_selection.py
#	modified:   python/lsst/ts/scheduler/proposals/proposal.py
    user regions implemented for deep drilling

#	modified:   python/lsst/ts/scheduler/fields/create_fields_data.py
#	modified:   python/lsst/ts/scheduler/fields/create_fields_db.py
#	modified:   python/lsst/ts/scheduler/fields/create_fields_table.py
#	modified:   python/lsst/ts/scheduler/fields/ingest_fields_data.py
#	modified:   python/lsst/ts/scheduler/proposals/__init__.py
    updated for "pep8" compliance

0.8.8 (2017-02-13)
==================

* Restructured repository
* Renamed modules
* Uses scons to get version information

0.8.5 (2017-01-06)
==================

* Driver

  * New cost function for time interval since last filter change.
  * This cost function adds to the slew time cost.
  * New parameters to control this new behavior.

* Target

  * Renamed cost_bonus into cost.
  * cost is now a quantity that is substracted from rank.

0.8 (2016-12-22)
================

* Observatory Model

  * normalized angles
  * Tracking=False when a limit is reached

* Driver

  * Remaining tracking time verified for targets before sending them

* Sky regions

  * Time ranges for areas

0.7 (2016-12-08)
================

* Area Distribution Proposal

  * hybrid area-time behavior
  * configurable grouped visits
  * configurable time window
  * configurable constraint to revisit group per night

* Interested Proposal

  * feedback to SOCS about Proposals getting credit from observation

* Downtime handling

* Filter changer

  * filter swaps
  * configurable constraints for filter changes

* Weather handling

  * clouds
  * seeing

* Airmass bonus

* Park method implemented

0.3 (2016-05-27)
================

* Area Distribution Proposal
* Configuration from SOCS
* New cost functions
* New value functions
* New flexible serendipity
* Repeatable code
* New sky brightness
* Observatory Model constantly updated from telemetry
* Several unit tests

0.2   (2015-12-23)
==================

* Observatory Model states and tracking implemented.
* Generic basic Proposal implemented.
* First version of scripted proposal implemented.
* Fields table read from configuration file.
* Configuration from external SOCS.
* Transmission of fields.

0.1.4 (2015-10-22)
==================

LSS_DDS_DOMAIN handling
logger extended to stdout for INFO* level

#	deleted:    ts_scheduler/build_scheduler
    unused copy
#	deleted:    ts_scheduler/dev_setup.env
    replaced by scheduler.env

#	new file:   ts_scheduler/schedulerDefinitions.py
    logger INFOX level definition

#	modified:   ts_scheduler/scheduler.env
    LSST_DDS_DOMAIN variable added
#	modified:   ts_scheduler/schedulerMain.py
    logger extended to stdout when level appropriate

0.1.3 (2015-10-21)
==================
* Cookiecutter compliant

0.1.2 (2015-10-14)
==================
* Logger

0.1.1 (2015-10-09)
==================
* Interface tests

* scheduler.py
* schedulerMain.py
* schedulerDriver.py
* schedulerTarget.py
* schedulerTest.py
* build_scheduler

0.1.0 (2015-08-31)
==================
* First release on ts_scheduler repository.
