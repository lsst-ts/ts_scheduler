.. _scheduler_label:

===================================
LSST Scheduler
===================================

The LSST Scheduler is a complex software that relies on a series of submodules to properly function. Some of them
provides the interface with the (S)OCS while others provides access to crucial telemetry information, about the system
and the environment.

.. _config_label:

Scheduler configuration parameters
--------------------------------------------

.. _submodules_label:

Scheduler submodules
----------------------

Most of these submodules are configured at the initialization process and thus relies on the
scheduler interface. A list of these submodules with initialization parameters is provided
here. Some of these submodules are functional (a.k.a. the scheduler uses them as telemetry input or else) others are
responsible for setting up the survey and scheduling algorithms.

Observatory
^^^^^^^^^^^^^^^

The observatory module provides an interface to telemetry for both the real and simulated observatory. The scheduler
uses this module to take information from the system and to estimate things like slew time and telescope limits.
Setting up and function of this module should be seamless whether it is a simulation or real operation.

This module encapsulates the following sub-modules;

    * Telescope
    * Dome
    * Rotator
    * Camera
    * Filters
    * Slew
    * OpticsLoopCorr
    * Park
    * ObservatoryVariation

For use in the API the user should refer to the
`observatory model class <https://github.com/lsst-ts/ts_observatory_model>`_. Inside the scheduler ``Driver``, this
module is accessed as ``observatoryModel`` and ``observatoryModel2``, ultimately both instances are
synchronized to the (S)OCS observatory (model or real). The first instance is used for main synchronization while the
latter for secondary tests. So, for checking if a target/sequence is reachable and observable the user should use
``observatoryModel2`` and for telemetry information ``observatoryModel``. There's also a ``observatoryState`` instance
which, as the name suggests, tracks the state of the observatory, which is also synchronized with the main (S)OCS
observatory state.


Environment
^^^^^^^^^^^^^^^

These modules provides interface to environmental telemetry information gathered directly from (S)OCS through the
middleware communication layer. Right now the following information is available to the scheduler, and should be
updated soon to account for other information.

    * Seeing - Single value from seeing monitor (arcseconds). Accessed through ``seeing``.
    * Cloud - Single value from cloud monitor. This should eventually be a 2d map. Accessed through ``cloud``.
    * Transparency - Not available
    * Sky brightness - Not available
    * Wind - Not available
    * Temperatures - Not available

Downtime
^^^^^^^^^^^^^^^

These modules provides interface for scheduled and unscheduled downtime. On simulations unscheduled downtime are
generated randonly and the scheduler automatically responds by stopping operations until further notice.

Right now, there's no interface for downtime in the scheduler API.


Driver
^^^^^^^^^^^^^^^

The scheduler driver is the main piece of software responsible for connecting the scheduling algorithms with the
(S)OCS. This module provides the basic logic for configuring "the survey", which is represented by a set of
"proposals". The driver also provides an interface for the aforementioned telemetry stream that can be organized in
anyway needed by the algorithm being used (as long as the information is available to the Driver).

Currently, the driver receives a set of configurations that are particular to the way the current scheduling algorithm
works and may be updated soon to be more general. The set of available parameters are:

    * coadd_values: Flag to determine if two identical field/filter targets have their ranks added and then
      considered as one target.

    * time_balancing: Flag to detemine if cross-proposal time-balancing is used.

    * timecost_time_max: The slew time (units=seconds) where the time cost value equals one.

    * timecost_time_ref: The reference slew time (units=seconds) that sets the steepness of the cost function.

    * timecost_cost_ref: The cost value associated with the time cost reference slew time.

    * timecost_weight: The weighting value to apply to the slew time cost function result.

    * filtercost_weight: The weighting value to apply to the filter change cost function result.

    * propboost_weight: The weighting value to apply to the time balancing equations. This parameter should be
      greater than or equal to zero.

    * **night_boundary:** Solar altitude (degrees) when it is considered night.

    * **new_moon_phase_threshold:** New moon phase threshold for swapping to dark time filter.

    * ignore_sky_brightness: Flag to ignore sky brightness limits when rejecting targets.

    * ignore_airmass: Flag to ignore airmass limits when rejecting targets.

    * ignore_clouds: Flag to ignore cloud limits when rejecting targets.

    * ignore_seeing: Flag to ignore seeing limits when rejecting targets.

Parameters in bold face are those that are more likely to be kept for more general driver configuration. Or, this list
could be replaced by a single configuration file in any format that needs to be unpacked and configured by the driver.

Survey
^^^^^^^^^^^^^^^

This set of parameters are used at several levels for the scheduler and part of the simulation environment. For real
operation the simulation configuration will likely be dropped of but the scheduler part will still be needed. Some
of this parameters are particular to the current scheduler algorithm, and will be generalized for working with the API.

The set of available parameters are:

    * start_date: This parameter is used to configure the simulation, setting up the start date of the simulation.
      Specially it is used on several other instances to configure a ``TimeHandler`` class on SOCS. On normal operation
      this will be accessed through the telemetry stream and this parameter will probably be unused.

    * duration: This parameter is used both on the simulation but also exposed to the scheduler and the driver through
      ``survey_duration_DAYS``.

    * idle_delay: Basically used to configure the behaviour of the simulation in case no valid target is generated by
      the scheduler.
    * general_proposals: The list of available general proposals.
    * sequence_proposals = The list of available sequence proposals.
    * alt_proposal_dir = An alternative directory location for proposals.

Note that "general_proposals" and "sequence_proposals" are very particular to the current scheduler algorithms. The
idea is that they are going to be generalized to a single "proposals" statement, and that this general type of proposal
gathers only the basic information needed to configure a specific proposal, regardless of the scheduling algorithm
used. One must be aware that a proposal require some basic information to be passed to the scheduler (and then to the
OCS). Even if the scheduling algorithm implemented does not internally uses the same logic, it is important to make
this translation so that the proper information is passed to the (S)OCS.


Proposal
^^^^^^^^^^^^^^^

A Proposal is where algorithm information regarding each of the different science projects being executed on the
observatory are stored and translated into an observational strategy. There exists a number of different ways of doing
target selection. This object make sure any algorithm must generate and contain a certain number of information for
internal bookkeeping. It also provides an interface for configuration through the middleware.

Right now this configuration is done in a way very particular to the scheduling algorithm used by the scheduler and
will be generalized to accommodate different algorithms. Also, right now there are two different kinds of Proposals
with different sets of parameters (general and sequence proposals). In the future there will be a single kind of
proposal and, likely, a string will be passed which can contain a configuration file (or other configuration method).

These are the parameters currently used to configure a general proposal:

    * **name:** Name for the proposal.
    * sky_region: Sky region selection for the proposal.
    * sky_exclusion: Sky region selection for the proposal.
    * sky_nightly_bounds: Sky region selection for the proposal.
    * sky_constraints: Sky region selection for the proposal.
    * **filters:** Filter configuration for the proposal.
    * *scheduling:* Scheduling configuration for the proposal.

Parameters in **bold** letters are those likely to be kept for a general proposal. The *scheduling* parameter will
likely be re-purposed and host a string to be passed to Driver containing a configuration file (either parameter list
or other configuration method).
