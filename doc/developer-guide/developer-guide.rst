.. _Developer_Guide:

#########################################
Scheduler Developer Guide
#########################################

This page describes some of the current implementation details of the Scheduler CSC.
It may be that some details described here are not yet in line with the Scheduler requirements and some requirements are still not fully implemented.
These will be corrected in future updates to the software and documentation as we work towards fulfilling all the requirements.

The primary classes in the Scheduler CSC are:

* :py:class:`SchedulerCSC <lsst.ts.scheduler.scheduler_csc.SchedulerCSC>`; Commandable SAL Component that manages the interaction with the observatory control system and computes the observing queue.

* :py:class:`Driver <lsst.ts.scheduler.driver.Driver>`; A base class that implements an API for integrating scheduling algorithms in the context of the Rubin Observatory.

These two main classes are intrinsically interconnected, with the :py:class:`SchedulerCSC <lsst.ts.scheduler.scheduler_csc.SchedulerCSC>` using the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` to generate a list of observations and interacting with the other parts of the observatory control software to execute them.
While doing so, the SchedulerCSC makes some assumptions about the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` implementation and overall behavior.
When implementing a new scheduling algorithm to use with the :py:class:`SchedulerCSC <lsst.ts.scheduler.scheduler_csc.SchedulerCSC>`, one must take into account these assumptions and make sure they are not violated or, at least, that they understand their impact on the output of their underlying implementation.

In the following sections we will explore each one of these modules individually.

.. _Developer_Guide_Scheduler_CSC:

Scheduler CSC
=============

The SchedulerCSC follows the standard definition of CSCs in the context of the Rubin Observatory Control System.
In short the CSC works as follows;

* While in STANDBY state, the CSC will not perform any work, and simply establishes itself as alive and ready.

  In this state the CSC will not hold an instance of the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` or any other object it uses for operation.
  One should assume that any state gathered by the CSC when it is in other states is wiped out when the CSC is in STANDBY.

  This is particularly important when developing new :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` classes, since one should not expect state to be persisted when the CSC is transitioned to this state.
  
  Any state that the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` or the model classes construct is done when transitioning from STANDBY to DISABLED.

* When transitioning from STANDBY to DISABLED, the CSC will re-construct instances to all the objects it needs (:py:class:`Driver <lsst.ts.scheduler.driver.Driver>` and models alike).

  In the default mode of operation this means the CSC will start with bare initialized objects.

  The CSC provides a mechanism to reconstruct state for the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` through the ``startup_type`` and ``startup_database`` configuration parameters.

  See more details in :ref:`Developer_Guide_Startup_Modes`.

* Once in ENABLED state the CSC will monitor and synchronize the observatory state with its own observatory state object.

  The CSC will not perform any additional action upon entering the ENABLED state, therefore it is safe to keep the CSC in ENABLED state at any time.

* When ready to handle control of the observatory to the SchedulerCSC, the operator must send a ``resume`` command to the CSC.

  This will cause the CSC to activate the target production loop, which will then interact with the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` to produce a sequence of observations and later send the associated observations to the ``ScriptQueue``.

* Operators can continue to interact with the ``ScriptQueue`` while the SchedulerCSC is operating.

  In all modes of operation, the SchedulerCSC monitors the content of the ScriptQueue and can interoperate with scripts scheduled by other parties.
  
  In most cases, this simply consists of waiting for the Script to finish executing before adding sending more targets for observations.

  Nevertheless, the SchedulerCSC tries to do more than simply wait.
  If the Script has information about telescope position and duration, the Scheduler CSC will take that information into account when determining the observatory state for future observations.
  For more information see the :ref:`Developer_Guide_Operation_Modes`.

* To stop the SchedulerCSC, operators can send the ``stop`` command.

  The stop command will interrupt the target production loop.
  By default, the SchedulerCSC will allow the currently scheduled observations (those it already sent to the ScriptQueue) to continue and will continue to register them in the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>`.

  Alternatively, users can tell the SchedulerCSC to interrupt any scheduled observation.

.. _Developer_Guide_Startup_Modes:

Startup Modes
-------------

The SchedulerCSC supports three different types of startup modes, that controls how the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` is initialized.

.. _Developer_Guide_Startup_Modes_Cold_Start:

Cold Start
^^^^^^^^^^

This mode of operation will reconstruct the state of the scheduling algorithm from scratch, reconstructing state by playing back observations read from the EFD or from a local sqlite database.

After performing a fresh configuration (overriding any previous values) the Scheduler will perform the following actions:

- If :ref:`startup database <startup_database>` is empty; finish startup as soon as the configuration is loaded.

- If :ref:`startup database <startup_database>` points to an existing file path:

   1.  Assume it is an observations database that the ``Driver`` understands.
   2.  Call :py:meth:`Driver <lsst.ts.scheduler.driver.Driver.parse_observation_database>` to retrieve a list of observations.
   3.  Call :py:meth:`Driver <lsst.ts.scheduler.driver.Driver.cold_start>`, passing in the result of the previous call.

   If any of these steps fail, it will reject the ``start`` command and remain in STANDBY.

- If neither of the above;

   1.  Assume :ref:`startup database <startup_database>` is an EFD query that retrieves a list of observations.
   2.  If the result is empty, fail the startup process.
   3.  Perform the query to the EFD and pass the results to :py:meth:`Driver <lsst.ts.scheduler.driver.Driver.cold_start>`.

   If any of these steps fails, it will reject the ``start`` command and remain in STANDBY.

.. _Developer_Guide_Startup_Modes_Hot_Start:

Hot Start
^^^^^^^^^

This is the most versatile startup mode and is designed to rapidly initialize the scheduler to an operational state.

The scheduler will check if it was previously configured, then perform the following actions;
   
- If scheduler algorithm is not configured (first time after a shutdown): 

   1. Perform a fresh driver configuration.

   2. If a :ref:`startup database <startup_database>` is provided, the Scheduler assumes it is a snapshot uri, and overrides the scheduling algorithm with the one indicated by this parameter.
      If it fails to load the startup database as a snapshot, the start command will be rejected and the Scheduler will remain in standby.

- If yes (scheduler was already configured and is being re-enabled, e.g. after a fault):

   1. Skip driver configuration and retain all previous state.
      This also means it will ignore any :ref:`startup database <startup_database>` provided.

Note that, to make sure the Scheduler will load a new configuration, one should either use WARM or COLD start.
When executing in HOT start the Scheduler will default to using an already existing configuration.

.. _Developer_Guide_Startup_Modes_Warm_Start:

Warm Start
^^^^^^^^^^

This mode of operation works similarly to HOT start except that it always reconfigures the scheduler.
In this case the Scheduler will perform the following actions:

1. Perform a fresh configuration.

2. If a :ref:`startup database <startup_database>` is provided, the Scheduler assumes it is a snapshot uri, and overrides the scheduling algorithm with the one indicated by this parameter.
   If it fails to load the startup database as a snapshot, the start command will be rejected and the Scheduler will remain in standby.

.. _Developer_Guide_Operation_Modes:

Operation Modes
---------------

.. _Developer_Guide_Operation_Modes_Simple:

Simple
^^^^^^

The simple mode of operation causes the scheduler to deal with one target at a time.
When operating in this mode the Scheduler will;

1. gather telemetry,
2. update the driver with the most recent telemetry,
3. request one target,
4. send the target to the ScriptQueue for execution,
5. wait for the script execution to complete,
6. if the observation executes successfully, register the observation in the driver.

This mode is mostly to be used for testing the system is a sequential way.

.. _Developer_Guide_Operation_Modes_Advance:

Advance
^^^^^^^

The advance mode is the one intended for actual operation of the observatory.

What this mode does is to compute a (configurable) number of targets ahead of time and commit to execute them.
However, even though it is committed to execute those observations, it has mechanisms to allow rolling back the scheduling algorithm state whenever observations fails to execute.

The Advance mode of operation works like this:

1. Gather telemetry,
2. Synchronize the model observatory state with the current observatory state.
3. Save a snapshot of the driver state, by calling :py:meth:`Driver.save_state <lsst.ts.scheduler.driver.Driver.save_state>`.
   The data is stored in the LFOA and an event is published with information about the file.

4. Generate a list of targets with the following procedure:

   1. Request one target by calling :py:meth:`select_next_target <lsst.ts.scheduler.driver.Driver.select_next_target>`.
      For each target, store the state of the scheduler used to generate it.

   2. Register the target as observed.

      This process involves:

      * Simulate the observation in the observatory model.
      * Register the observation in the driver with :py:meth:`Driver.register_observation <lsst.ts.scheduler.driver.Driver.register_observation>`.

   3. Repeat until :ref:`n_targets <n_targets>` are generated or if no target is returned in step 1.

   Note that at the end of this process the observatory state will have been modified like the scheduled observations were successfully completed, even though they have not been scheduled or observed yet.

6. Schedule 2 targets in the ScriptQueue for observing.

   While one target executes the second target is waiting to be executed.
   When the running target finishes it will send a new one to make sure there is always a target waiting to execute in the ScriptQueue.

   When a target is observed successfully (Script finishes executing) delete the stored state.

   If the observation fails:

   1. Remove all previouly scheduled scripts from the ScriptQueue.

   2. Discards all previously calculated targets.

   3. Reset the state of the Scheduler to the state before the failed target was calculated.

7. When all targets generated in step 4 are scheduled for observation in the ScriptQueue, start again from step 1. 

.. _Developer_Guide_Operation_Modes_Dry:

Dry
^^^

The SchedulerCSC has a third mode of operation that is mainly used for testing.

When configured in this mode the SchedulerCSC will not initialize the driver and the target generation loop.
It is still possible to bring the component to the ENABLED state with this mode and command it to resume and stop, but no target will be generated in any condition.

This mode is only provided for unit testing purposes and should not be used in general.

.. _Developer_Guide_Driver:

Driver
======

The Driver provides an interface for integrating different *scheduling algorithms* with the Scheduler CSC.
When implementing new *scheduling algorithms*, developers should first subclass :py:class:`Driver <lsst.ts.scheduler.driver.Driver>`.
The default implementation provides most of the business logic, leaving to the developer to implement a couple different methods to specify how the application is initialized, configured, consume telemetry and produce targets for observation.

The standard :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` implementation is paired with a standard set or parameters and a standard target class; :py:class:`DriverParameters <lsst.ts.scheduler.driver.DriverParameters>` and :py:class:`DriverTarget <lsst.ts.scheduler.driver.DriverTarget>`, respectively.
These only provide some basic parameters used by the Driver in it standard operations.
Developers can further expand the parameters and the target class on their implementation by sub-classing them.

The following is the minimum set of methods that needs to be implemented by the driver:

* :py:meth:`Driver.configure_scheduler <lsst.ts.scheduler.driver.Driver.configure_scheduler>`
* :py:meth:`Driver.update_conditions <lsst.ts.scheduler.driver.Driver.update_conditions>`
* :py:meth:`Driver.select_next_target <lsst.ts.scheduler.driver.Driver.select_next_target>`
* :py:meth:`Driver.register_observation <lsst.ts.scheduler.driver.Driver.register_observation>`

With this minimum set of methods implemented it is possible to run some simple integration tests.
Nevertheless, for real operations of the observatory, the following methods should also be implemented.

* :py:meth:`Driver.save_state <lsst.ts.scheduler.driver.Driver.save_state>`
* :py:meth:`Driver.parse_observation_database <lsst.ts.scheduler.driver.Driver.parse_observation_database>`
* :py:meth:`Driver.reset_from_state <lsst.ts.scheduler.driver.Driver.reset_from_state>`

Finally, the following functional methods are needed for full-featured operations.

* :py:meth:`Driver.load <lsst.ts.scheduler.driver.Driver.load>`
* :py:meth:`Driver.cold_start <lsst.ts.scheduler.driver.Driver.cold_start>`

Block and Script Configuration
------------------------------

When the Scheduler CSC executes an observation of a target, it does so by executing a Block.
A Block is a sequence of SAL Scripts that will be executed in order by the Scheduler.

When writting a Block we need to configure which parameters will be passed from the Scheduler to each of the Scripts in the block.
The following is a list of parameters that the Scheduler will pass along:

* ``targetid``: An integer id of the target.
* ``band_filter``: The band name, e.g. u, g, r, i, z, y.
* ``filter_name``: The name of the filter. This is the identifier of the element itself, e.g. ``SDSSr_65mm``, ``r_01_xyz``.
* ``name``: The target name.
* ``note``: A note about the target.
* ``ra``: Right ascention of the target in the ICRS coordinates frame in sexagesimal format; HH:MM:SS.sss.
* ``dec``: Declination of the target in the ICRS coordinates frame in sexagesimal format; DD:MM:SS.sss.
* ``rot_sky``: Sky angle, in degrees (0 means north up, east right).
* ``alt``: Expected altitute/elevation of the target in degrees. This is usually calculated from the ``ra`` and ``dec`` parameters for the expected time of the observations.
* ``az``: Expected azimuth of the target in degrees. This is usually calculated from the ``ra`` and ``dec`` parameters for the expected time of the observations.
* ``rot``: Expected physical position of the rotator. This is usually calculated from ``ra``, ``dec`` and ``rot_sky``. However, in some cases, this could be provided directly from the scheduling algorithm.
* ``obs_time``: Expected MJD time the target will be observed.
* ``num_exp``: Number of exposures.
* ``exp_times``: List of exposure times, in seconds.
* ``estimated_slew_time``: Estimated slew time, in seconds.
* ``program``: The name of the program/block.
* ``observation_reason``: The reason for this observation.

In order to configure a block to use any of the parameters above, you can simply add a ``$`` before the parameter name in the block.
For example, the following block configuration;

.. code-block:: json

  {
      "name": "Imaging",
      "program": "BLOCK-303",
      "constraints": [],
      "scripts": [
          {
              "name": "maintel/track_target.py",
              "standard": true,
              "parameters": {
                "slew_icrs": {
                  "ra": "$ra",
                  "dec": "$dec"
                },
                "rot_value": "$rot",
                "rot_type": "PhysicalSky",
                "track_for": 30.0,
                "stop_when_done": false
              }
          }
      ]
  }

would replace ``$ra``, ``$dec`` and ``$rot`` with the ``ra``, ``dec`` and ``rot`` values, respectively.
This is an example where we use the sky coordinates for position and physical coordinates for the rotator.

.. _Developer_Guide_Driver_FBS:

The Feature-Based Scheduler Driver
----------------------------------

TBD

.. _Developer_Guide_Driver_Sequential:

The Sequential Driver
---------------------

TBD

.. _lsst.ts.scheduler.api:

Code API
========

.. automodapi:: lsst.ts.scheduler
    :no-main-docstr:

.. _Developer_Guide_Dependencies:

Dependencies
============

The Scheduler CSC is a Python salobj based CSC, as such it depends on the Observatory Control System core packages;

* ts_xml
* ts_sal
* ts_idl
* ts_salobj
* ts_ddsconfig

For development and testing we recommend using the ``ts-conda-build`` meta-package.

Furthermore, the Scheduler has additional test and run dependencies for the models, the supported scheduling algorithms and other observatory control packages (e.g. scriptqueue).
The list includes the following packages, which are available through conda;

* ts-scriptqueue (development and testing only)
* ts-observatory-model
* ts-astrosky-model
* ts-dateloc
* rubin-sim

.. _Developer_Guide_Build:

Build and Test
==============

There are two supported ways to build and test the Scheduler CSC, using ``eups`` or ``conda/pip``.
Selecting which method is more suitable for you depends on what kind of changes you are planning to make.

If the update you intend to make doesn't involves changes to CSC interface (which also means updates to ts_xml, the best option is to use ``conda/pip``.
If you need to update the CSC interface (event, command or telemetry), the preferred method is to use ``eups``.

Let us review both options.

.. _Developer_Guide_Build_Developing_with_conda:

Developing with conda
---------------------

I assume here you have a basic conda environment ready with a usable installation of OpenSpliceDDS.
The latter is the library that handles the Observatory Control Middleware and is used by the CSC to communicate with other components in the system.

Start by creating a conda environment with python 3.8 and activate it:

.. prompt:: bash

   conda create -y --name scheduler-dev python=3.8
   conda activate scheduler-dev

Then, install the test dependencies:

.. prompt:: bash

   conda install -y -c lsstts ts-conda-build=0.3 ts-idl ts-utils ts-salobj ts-scriptqueue ts-observatory-model ts-astrosky-model ts-dateloc rubin-sim

From inside the package now, install the package locally with ``pip``:

.. prompt:: bash

   pip install -e . --ignore-installed --no-deps

Now you should be able to run the package unit tests with:

.. prompt:: bash

   pytest 

.. _Developer_Guide_Build_Developing_with_eups:

Developing with eups
--------------------

For developing with eups we strongly recommend using the development environment docker image.
The image ships with all the necessary libraries to get starting with minimum setup.

The process to developing using the docker development environment and eups is as follows:

1. Pull the latest docker image:

   .. prompt:: bash

      docker pull lsstts/develop-env:develop

2. Run the docker image, exporting your local development directory:

   .. prompt:: bash

      docker run -it -v <path-to-local-development-directory>:/home/saluser/develop lsstts/develop-env:develop

   After running the command above you will be inside the docker container.
   From now on, I assume you are in the same prompt that you are left in after running the command above.

3. Install the scheduler dependencies:

   .. prompt:: bash

      conda install -y -c lsstts ts-observatory-model ts-astrosky-model ts-dateloc rubin-sim

   Note that we excluded some dependencies from the previous ``conda install`` command used in the :ref:`Developer_Guide_Build_Developing_with_conda`.
   This is because those packages are already available in the development environment.

4. Declare the scheduler package with eups:

   .. prompt:: bash

      cd ~/develop/ts_scheduler
      eups declare -r . -t $USER
      setup ts_scheduler -t $USER

.. _Developer_Guide_Usage:

Usage
=====

[Description on how to use the software, scripts, any useful programs etc. Basic operations such as startup/shutdown should be explained, ideally with example code/steps]


.. _Developer_Guide_Documentation:

Building the Documentation
==========================

Before building the documentation page, follow one of the development installation procedures in :ref:`Developer_Guide_Build`.

With the packages installed run:

.. prompt:: bash
   
   pip install -r doc/requirements.txt

To install the libraries required to build the documentation, and then:

.. prompt:: bash

   cd docs/
   package-docs build

.. _Developer_Guide_Contributing:

Contributing
============

Code and documentation contributions utilize pull-requests on github.
Feature requests can be made by filing a Jira ticket with the `Scheduler` label.
In all cases, reaching out to the :ref:`contacts for this CSC <ts_xml:index:master-csc-table>` is recommended.

