.. _Configuration_details:

#######################
Scheduler Configuration
#######################

The Scheduler CSC has a set of rich configuration parameters and is organized into sections for the different modules.
As all other Configurable CSCs in the Vera Rubin Observatory Control System, the primary configuration file consists of a standard yaml file which is validated against a `json schema <https://raw.githubusercontent.com/lsst-ts/ts_scheduler/develop/python/lsst/ts/scheduler/config_schema.py>`__.

Most configuration parameters are defined with appropriate default values, which means users usually won't need to worry about filling most of them.

Nervertheless, unlike most CSCs, the Scheduler CSC has a set of required fields for which appropriate defaults are not provided.
This means users must always provide a minimum set of parameters.

The Scheduler CSC is part of the "Observatoy Control System" (OCS) group and its configuration files are stored in the `ts_config_ocs <https://github.com/lsst-ts/ts_config_ocs>`__ package.

.. _Configuration_details_required_parameters:

Required Parameters: Driver configuration
=========================================

The Scheduler configuration has a section dedicated to the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` module.
The :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` is the main hub for plugging in the so called "Scheduling Algorithms" to the Scheduler CSC.
More details about the driver can be found in the :ref:`Developer_Guide`; here we will focus on the configuration alone.

The basic scheduler driver configuration is composed of the following items:

* parameters; Contains basic :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` configurations:

  * night_boundary; Sun elevation to define the start/end of the night (in degrees).

  * new_moon_phase_threshold; Moon illumination threshold that defines dark time.
    The specified value is a number between 0 (fully obscured) and 100 (fully illuminated), representing the % illuminated fraction.

* default_observing_script_name; The name of the script that is executed in the script queue by the scheduler for each target.
  By default the scheduler will use this script, but the application (e.g. "Scheduling Algorithms") can override it.

.. _default_observing_script_is_standard:

* default_observing_script_is_standard; Is the default observing script a standard script?

  The ScriptQueue contains two types of SAL Script; standard and external.
  Standard scripts contains officially supported, unit-tested operations, whereas external scripts may contain experimental features and user-provided test operations.
  This flag is passed to the ScriptQueue to indicate if the default observing script is a standard or external SAL Script.

* stop_tracking_observing_script_name; The name of the script to execute if the Scheduler does not produce a target to observe in the middle of the night.
* stop_tracking_observing_script_is_standard; Is the stop tracking script standard?
  See default_observing_script_is_standard_ for more information.

Furthermore, this section of the configuration is defined to accept additional parameters values not specified in the configuration schema.
This allows especialized :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` implementations to receive additional parameters.

Even though all the parameters that are defined in the ``driver_configuration`` section have default values, the schema forces the user to provide some configuration.
The main reason we force the user to provide some configuration is because the ``driver_configuration`` section accepts additional fields that are not specified in the schema.
This means, validation of the schema is done in two steps, when parsing the configuration and when configuring the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>`, which has information about the additional fields in ``driver_configuration``.
By forcing the user to provide a configuration we make sure the initial schema validation will capture potential conflicts between the two steps in the validation.

 postponed to a later state, after the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>`

A minimum valid yaml Scheduler configuration file will look like:

.. code-block:: yaml

   driver_configuration:

The full set of defined values will look like:

.. code-block:: yaml

    driver_configuration:
        parameters:
            night_boundary: -6.0
            new_moon_phase_threshold: 20.0
        default_observing_script_name: standard_visit
        default_observing_script_is_standard: true
        stop_tracking_observing_script_name: stop_tracking.py
        stop_tracking_observing_script_is_standard: true


.. _Configuration_details_top_level_parameters:

Top-level Parameters
====================

The scheduler has some top-level parameters that are used to configure the overall behavior of the CSC.
These parameters are:

* s3instance; The name of the s3 bucket instance.

  Depending on the operational configuration, the scheduler will save the state of the underlying scheduling algorithm at particular points in time.
  For logging purposes, the state is stored in the Large File Object Annex (LFOA), which allows observatory personnel to inspect, debug and audit the scheduler aftwerwards.
  To configure the LFOA we need to provide the name of s3 bucket instance through this parameter.

* driver_type; Which driver to configure the Scheduler with.

  As we mention throughout this document, the Scheduler CSC can operate with different types of Scheduling Algorithms.
  These algorithms are implemented as subclasses to the base :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` class.
  This parameter allows the user to select which driver to load.
  By default the Scheduler CSC implements a set of supported drivers, but this parameter can also point to externally provided options.

  The input is in the format of the module path, e.g.; ``lsst.ts.scheduler.driver.feature_scheduler`` will search and import a subclass of :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` in this module.

  For a list of supported drivers see :ref:`the module API <lsst.ts.scheduler.api>`.

  For information on developing new drivers see the :ref:`Developer_Guide`.

* startup_type; The method used to startup the scheduler.

  The Scheduler has a couple different startup types that defines how the intenal state of the scheduling algorithm is constructed/re-constructed.

  The available options are:

  * HOT; hot start.

    In this mode the scheduler loads a snapshot of a previously executed and stored scheduler state.
    The input (see startup_database_ further down) will be similar to the files stored in the LFOA as mentioned above.

  * WARM; warm start.

    In this mode, the scheduler will start a driver with its initial empty setting, load a set of observations from a database and play those observations into the driver, like it would if the observations where being executed.
    
  * COLD; cold start (default).

    In this mode the scheduler will only initiate the driver and will not playback any observations.
 
.. _startup_database:

* startup_database; Path to a file holding scheduler state or observation database to be used on HOT or WARM start.

    The Scheduler CSC doesn't know how to load these databases.
    The process is entirely handled by the selected driver and the Scheduler is only responsible for initializing the driver and call appropriate methods, passing on this information.

* mode; The mode of operation of the scheduler.

  The scheduler CSC has a couple different modes of operations that defines how it interacts with the ScriptQueue, the telemetry stream and the scheduling algorithm.

  The available options are:

  * SIMPLE;

    The simple mode of operation causes the scheduler to deal with one target at a time.
    When operating in this mode the Scheduler will:
    1. gather telemetry,
    2. update the driver with the most recent telemetry,
    3. request one target,
    4. send the target to the ScriptQueue for execution,
    5. wait for the script execution to complete,
    6. if the observation executes successfully, register the observation in the driver.

  * ADVANCE;

    The advanced mode of operation is the one intended for real operation.
    In this mode the Scheduler implements a rather complex look-ahead routine intended to satisfy the scheduler operational requirements.
    Mode details about this mode can be found in the :ref:`Developer_Guide`.

  * DRY;

    This mode of operation is mostly used for unit testing.
    In this case, the scheduler does not produce any targets.

* n_targets; Number of targets to put in the queue ahead of time.
  
  This parameter is only used when the scheduler is configured with the ADVANCE mode.
  It specifies how many targets the Scheduler will send to the queue in advance.

* predicted_scheduler_window; Size of predicted scheduler window, in hours.

  This parameter is only used when the scheduler is configured with the ADVANCE mode.
  It specifies how much futher into the future the Scheduler will predict and publish information about the observing plan.

  Note that the Scheduler won't necessarily execute the targets it predicts.
  If the conditions are changing the predicted observations and the actual observations may differ.

* loop_sleep_time; How long should the target production loop wait when there is a wait event. Unit = seconds.

  This parameter is used to define an internal timer on the Scheduler.
  During operations, the Scheduler is constantly waiting for status from the ScriptQueue and other components.
  In order to prevent dead-locks (in case a component crashes for instance), the Scheduler will wait only this much time before actively polling for information.

* cmd_timeout; Global command timeout. Unit = seconds.

  Timeout used by the Scheduler when sending commands to other components (e.g. ScriptQueue).

* max_scripts; Maximum number of scripts to keep track of.

  During operations the scheduler keeps track of the previous scripts it sent to the ScriptQueue.
  This parameter controls how many scripts the Scheduler will keep track of. 

.. _Configuration_details_models_parameters:

Models Parameters
=================

The Scheduler CSC has a set of models it exposes to the driver that can be used to process the telemetry stream in various different ways.

In most cases, the Scheduler CSC will only configure the models with the input parameters and pass them to the driver, without any other intervention. 
The only exception to this rule is the observatory model.

The observatory model has an internal object that stores the state of the observatory.
In parallel, the Scheduler also keeps a separate copy of the observatory state.

The Scheduler copy of the observatory state is kept in synchronization with the actual observatory state, by listening for the state of the different components and continually updating this object.

When the Scheduler is updating the telemetry stream, it will synchronize the observatory state in the model with its observatory state.
From that on, the Driver can modify the state of the observatory model to compute future observations.

The following is a list of available models.
Each model has a specific section in the configuration for inputting their parameters.
The parameters for each model can be found in the schema file.

* location; The location of the observatory.
* observatory_model; The observatory model.
* sky; Sky model, including sky brighness models.
* seeing; Seeing model, includes functionality to convert from raw seeing measurements into seeing in the different bands and at different elevations.

The models all come with suitable default configurations so users will seldom require changing them.
One example of updating some of the observatory model configuration is as follows:

.. code-block:: yaml

   models:
       observatory_model:
           camera:
               filter_max_changes_burst_num: 1
               filter_max_changes_avg_num: 30000
           optics_loop_corr:
               tel_optics_cl_alt_limit:
               - 0
               - 30
               - 90

In the case above, the user is customizing the values of ``filter_max_changes_burst_num`` and ``filter_max_changes_avg_num`` in the ``camera`` submodule and ``tel_optics_cl_alt_limit`` of the ``optics_loop_corr`` submodule of the ``observatory_model``.

.. _Configuration_details_telemetry_parameters:

Telemetry Parameters
====================

The Scheduler exposes a pretty rich interface for users to define how it interacts with the telemetry stream.
In short, users can select a table in the EFD to be queried along with some basic information about how the Scheduler will query.

The telemetry configuration consists of the following parameters:

* efd_name; the name of the EFD instance which will be queried, e.g., summit or efd.
* streams; List of telemetry streams.

  Each item has the following properties:

  * name: Name of the telemetry.
  
    This is basically a dictionary key the Scheduler will use to identify the telemetry.
  
  * efd_table: The name of the EFD table to query the information from.
  * efd_columns: The column in the EFD table to query the information from.
  * efd_delta_time: Length of history to request from the EFD (in seconds).
  * fill_value: **Optional** field specifying which value to assign the telemetry when no data is obtained.
    The default value is ``"null"`` which is equivalent to ``None`` in python.
    Developers must make sure their :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` implementation is capable of dealing with missing values.

An example telemetry configuration is as follows:

.. code-block:: yaml

    telemetry:
        efd_name: summit_efd
        streams:
            - 
                name: seeing
                efd_table: lsst.sal.DIMM.logevent_dimmMeasurement
                efd_columns:
                    - fwhm
                efd_delta_time: 300.0
            - 
                name: wind_speed
                efd_table: lsst.sal.WeatherStation.windSpeed
                efd_columns:
                    - avg2M
                efd_delta_time: 300.0
            - 
                name: wind_direction
                efd_table: lsst.sal.WeatherStation.windDirection
                efd_columns:
                    - avg2M
                efd_delta_time: 300.0

Note that none of the streams above specify a value for ``fill_value``.
This means that, if the Scheduler CSC in unable to retrieve a value for one of those entries, the value passed to the :py:class:`Driver <lsst.ts.scheduler.driver.Driver>` would be ``None``.
