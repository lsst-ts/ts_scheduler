.. _Version_History:

===============
Version History
===============

v1.17.0
-------

* Add new submodule ``utils/scheduled_targets_info.py`` defining a data class ``ScheduledTargetsinfo``` which holds information about scheduled targets.

  This is going to be used by the ``check_scheduled_targets`` method in the (new) ``Model`` class to return information about targets that were verified.
  This is part of a refactor of the ``SchedulerCSC`` code which extracts into the ``Model`` class some of the functionality related to the control loop operation, reducing the amount of code in the CSC and improving separation of concerns.

* Add new submodule ``model.py`` which implements the ``Model`` class.

  This class holds the bulk of the logic behind the control loop operations.
  It contains the following information from the ``SchedulerCSC`` class:

  * telemetry_stream_handler: Handle retrieval of telemetry from the EFD.
  * models: Dictionary with the available models.
  * raw_telemetry: Dictionary with all the raw telemetry values.
  * script_info: Dictionary with information about queued scripts.
  * driver: Instance of the scheduler driver, that encapsulates the mechanism to drive the scheduling algorithm.

  In addition, the ``Model`` class now extracts from the CSC class all the logic to manage these resources, such that the CSC can call the model to execute the required operations.
  The idea is to improve the separation of concerns, improving the maintainability of the package, and reducing bloat in the CSC code.

* In ``scheduler_csc.py``:

  * Refactor ``SchedulerCSC`` to use the new ``Model`` class.

    This removes a lot of the logic interacting with the ``Driver`` to generate targets into the ``Model`` class, reducing the amount of code and operations implemented in the CSC.

  * Add compatibility with xml 13.

  * Extract the ``set_detailed_state`` decorator from the CSC into the utility package.

  * Remove ``set_detailed_state`` and use method defined in ``utils/csc_utils.py``.

v1.16.0
-------

* In ``utils/csc_utils``, add ``DetailedState`` enumeration.

  This enumeration will be removed once we release a version of ts-idl with it.
  For now it will be kept here for backward compatibility.

* In ``utils/exceptions``:

  * Rename exception ``UnableToFindTarget`` to ``UnableToFindTargetError``.

  * Add new exception ``FailedToQueueTargetsError``.

* In ``scheduler_csc``:

  * Fix typo in ``begin_start`` exception logging.

  * Improve handling simulation mode and DRY operation mode in ``begin_enabled`` by merging condition into a single if statement.

  * Background tasks management refactor:

    Add a ``_tasks`` dictionary to store all background tasks that need to be managed by the CSC when going in and out of disabled state.
    Move tasks ``target_production_task`` and ``telemetry_loop_task`` to this new dictionary.
    Add methods ``_stop_all_background_tasks`` and ``_stop_background_task`` to handle stopping background tasks.

    In ``begin_disable``, replace inline management of stopping ``target_production_task`` with call to ``_stop_all_background_tasks``.

    In ``handle_summary_state``, replace management of ``telemetry_loop_task`` with call to ``_stop_all_background_tasks``.

  * Add detailed state transition facility.

    The detailed state transition is mostly managed using a decorator.
    Methods decorated with ``set_detailed_state`` will first acquire a detailed state lock, guaranteeing no other detailed state transition can happen at the same time.
    Then they assert that the detailed state is ``RUNNING``, otherwise they cannot go into one of the operational sub states.
    Next, the state switches to the desired new detailed state, executes the decorated coroutine and, once it is done, returns the system to ``RUNNING``.
    There are also methods to send the CSC from IDLE to ``RUNNING`` and vise-versa.

  * Refactoring ``advance_target_loop``.

    * Extract method to add targets to the queue into a new method ``queue_targets``.
      This method will switch the detailed state to ``QUEUEING_TARGET`` and execute the operations previously done inline in ``advance_target_loop``.
      If the method fails to produce targets and fails to find a target in the future, it raises a new exception ``FailedToQueueTargetsError``.

    * Change how ``generate_target_queue`` and ``compute_predicted_schedule`` runs.

      Instead of calling them sequentially, which causes a delay in producing targets, call ``generate_target_queue`` first and then, while waiting for targets to execute, call ``compute_predicted_schedule``.
      This new way improves over the previous implementation but still leaves room for conditions where ``compute_predicted_schedule`` can take longer to execute than the targets to be observed and then lead to additional delay.
      Nevertheless, conditions like this were only observed with the AuxTel configuration, which is a lot heavier than the one for the main telescope, and because there was a bug in the predictive loop which would continue to compute targets until the queue was filled up.

    * Update to future-proof against deprecated feature in python>3.11.
      Stop using coroutine directly in ``asyncio.wait`` and schedule a task with ``asyncio.create_task`` instead.

    * In situations where the ``generate_target_queue`` can't find a suitable target for the immediate future but succeeds in finding one in the future, the method waits for a timer task.
      When this condition happens, switch the detailed state to ``WAITING_NEXT_TARGET_TIMER_TASK``.

    * Add info log message before entering the loop.

  * Minor cosmetic updates on ``check_scheduled`` to improve logging information.

    Instead of sending a debug message inside the loop, collect the messages and log them all in a single message at the end.

  * Rename exception ``UnableToFindTarget`` to ``UnableToFindTargetError``.

  * Change how ``_do_computePredictedSchedule`` executes ``compute_predicted_schedule``.

    Instead of awaiting for the method directly, run it in a background task that is included in the ``_tasks`` dictionary.
    This way, if the CSC is disabled while executing ``compute_predicted_schedule``, the ``_stop_all_background_tasks`` will handle stopping the computation.

* In ``tests/test_advanced_target_loop.py``, update unit tests to check the DetailedState events published by the CSC.

* In ``tests/test_csc.py`` add new ``test_disable_while_computing_predicted_schedule`` unit test to check that the ``computing_predicted_schedule`` is interrupted if the CSC is sent to DISABLED state.

* In ``tests/test_csc.py``, check that CSC publishes detailed state on startup with the correct value.

* In ``tests/conftest.py``:
  
  * Fix start_ospl_daemon fixture handling condition where the ospl daemon is already running.

  * Update address of the sky brightness server in ``download_sky_file`` utility method.

v1.15.2
-------

* Delete examples directory with old, unused jupyter notebooks.

* Update doc/conf.py to ignore style checks.

* Add new test configurations for the Scheduler.

* Add test fixture to download the required sky brightness files for the tests.
  The fixture is configured with a ``session`` scope and with ``autouse=True``, so tests dont need to request them.
  The fixture first tests to see if a suitabe sky brightness file exists and then proceeds to download it if not.
  If it can not file a suitable file in the server it fails with a ``RuntimeError``.

* In ``DriverTarget``, fix parsing note into target name.

  Split the name in the first colon (``:``) and use the last part of the split.
  This works such that:

  * ``PROJECT:TARGET_NAME`` -> ``TARGET_NAME``

  * ``TARGET_NAME`` -> ``TARGET_NAME``

  * ``PROJECT:TARGET_NAME:ADDITIONAL_INFO`` -> ``TARGET_NAME:ADDITIONAL_INFO``

* In ``DriverTarget`` set ``requestTime`` from ``obs_time`` instead of ``time``.

* In ``SchedulerCSC`` update ``init_models`` such that it will reset the models if it fails to configure one of them.
  This fixes an issue with the SchedulerCSC when it fails to setup a model due to transient reasons (e.g. lack of sky brightness files or misconfiguration) which then requires restarting the CSC when the condition is corrected.
  With this the CSC no longer needs to be restarted.

* Remove empty line in ``SchedulerCSC.check_scheduled`` docstring.

* In ``SchedulerCSC._get_targets_in_time_window`` fix 2 issues found during testing.

    * The ``predictedScheduler.mjd`` fields were all set to zero, because ``target.obs_time`` is not set by the driver, because all observations are configured to be taken as soon as possible.
      Set the time for ``time_scheduler_evaluation``.

    * At each loop with a successful observation, update ``time_scheduler_evaluation`` to be at the end of the observation.
      This issue was causing the Scheduler to compute all the 1000 maximum observations.

* In ``SchedulerCSC.callback_script_info`` fix setting the script_info index to use ``data.scriptSalIndex`` instead of ``data.salIndex``.
  The index is supposed to be the index of the SAL Script and not of the ScriptQueue.
  This was causing observations to not be properly registered by the scheduler.


* In ``test_advanced_target_loop`` update ``test_with_queue`` to use ``advance_target_loop_sequential_std_visit`` configuration, wait for at least one script to finish executing and add check that observation event was published.

* In test_csc, update ``test_compute_predicted_schedule`` to use new ``advance_target_loop_fbs`` configuration and expand checks so it verifies the size of the computed predicted schedule and the values.

* Fix ``standard_visit`` test script and update script to only wait for a second before finishing.
  This script is used in unit tests.

* Add pre-commit-config file with configuration for pre-commit hooks.

* Update pyproject.toml with configuration for isort.

* Sort imports with isort.

v1.15.1
-------

* Improve how feature scheduler driver sets the object name and program on scripts.

v1.15.0
-------

* Update conda build to use pyproject.toml.

* General updates in the tests and codebase to work with latest version of ``rubin-sim``.

* In Scheduler CSC:

  * Update telemetry loop such that the CSC will only go to FAULT if it cannot determine the observatory state in case the CSC is in enabled, is running and the queue is also running.
  * Update ``generate_target_queue`` such that it will only execute ``handle_no_targets_on_queue`` if no targets were found and there are no scheduled targets.
  * Fix publishing time to next target in ``estimate_next_target``.
  * In Scheduler refactor handle_no_targets_on_queue to always run ``estimate_next_target`` but only schedule stop tracking target once per occurrence.

v1.14.0
-------

* In Scheduler CSC:

  * Add new command `computePredictedSchedule`, using the new `support_command` utility to maintain backward compatibility.
  * Publish general info.
  * Publish time to next target.
  * Add `compute_predicted_schedule` feature.
    The method runs in the advance control loop just after generating the target queue.
  * Add `_get_targets_in_time_window`, to run the scheduler into the future until it produces a set number of targets or reaches the end of the specified time window.
  * Refactor `estimate_next_target` to use `_get_targets_in_time_window`.
  * Add `current_scheduler_state` async context manager.
    This context manager stores a snapshot, optionally publishes it to the lfoa, yields and then restores the state of the scheduler.
  * Refactor `generate_target_queue` to use `current_scheduler_state` context manager to handle the snapshot.
  * Send ack in progress for all commands with a timeout of 1 min.

* Update advance target loop unit test to check that the predicted target queue was published as expected, as well as the new events `timeToNextTarget` and `generalInfo`.

* In csc_utils, add `support_command` method, to determine if the CSC supports a specific command.
  This is useful to provide backward compatibility with different xml versions.

* Add unit test for new `computePredictedSchedule` command.

v1.13.1
-------

* Add special condition/error code for when the CSC fails to update telemetry.

v1.13.0
-------

* In SchedulerCSC:

  * Implement cold start. This startup method is able to load observations from a local sql database or from an EFD query.
  * Implement warm start.
  * Refactor ``configure_driver_hot``, separating its content into two new methods; ``_load_driver_from`` and ``_handle_startup``.
  * Add methods to handle the different startup types; hot, warm and cold.
  * Add ``_handle_driver_configure_scheduler`` coroutine to handle running ``driver.configure_scheduler``, which is a regular method.
  * Update telemetry_loop so it will only go to fault if it cannot determine the observatory state if the CSC is in ENABLED state and running.
  * Add _handle_load_snapshot method to handle retrieving snapshots and running drive.load. Update do_load to use it.
  * Update typing and DriverTarget import statements.
  * Remove unecessary override of begin_start method.
  * Use register_observation when registering a target after observation was successfully completed.

* In FeatureSchedulerDriver:

  * Add methods to support converting ``observation`` from EFD queries into ``FeatureSchedulerTarget`` objects.
  * Add a ``default_observation_database_name`` property that is used as the default value for ``observation_database_name``.
  * Implement ``FeatureSchedulerDriver.parse_observation_database`` method.
  * Implement ``cold_start`` and ``parse_observation_database`` methods.
  * Implement ``register_observation``. 
    The method will store the observations in a sqlite database that can later be loaded and played back during cold start.

* In Driver base class:

  * Add methods convert_efd_observations_to_targets and _get_driver_target_from_observation_data_frame to deal with cold start.
  * Add get_survey_topology method to generate the survey topology and update configure_scheduler to use it.
  * Add register_observation method.
    This method should be called after the observation was successfully observed.
  * Add type hints.

* In ``utils/efd_utils``, add methods to mock querying the EFD for scheduler observations to use in unit testing cold start of the scheduler CSC.

* In ``utils/csc_utils``, add methods to determine if a string is a valid EFD query, and a constant with the list of named parameters for an observation.

* Add unit test for ``FeatureSchedulerDriver.parse_observation_database`` method.

* Add new test utility submodule with a FeatureSchedulerSim class, to help simulate running the feature scheduler for unit testing.

* Update configuration documentation with more detailed information about the different startup methods.

* Update CSC unit tests to take into account new ``SchedulerCSC.telemetry_loop`` behavior.
  CSC now only goes to FAULT if it cannot determine the observatory state if it is in ENABLED state and running.

* Add test_csc_utils with unit tests for new is_uri utility method.

* Add new csc_utils.is_uri method, to check if a string is a valid uri.

* Update description of startup_type configuration parameter in config_schema.

* Update FeatureScheduler unit tests to check register_observation data roundtrip (insertion and retrieval of data to a local databbase).

* Add ``SchemaConverter`` utility for the feature scheduler.
  This class converts observations into entries in a sqlite database and vice-versa.

* In DriverTarget, implement get_observation and get_additional_information.

* Add Observation data structure.

* In efd_utils, fix mock imports.

* Add type hints in DriverTarget.

* Rename `Driver.register_observation` -> `Driver.register_observed_target`.


v1.12.0
-------

* Upgrade to salobj 7.
* Update conda recipe to remove pins on ts-idl and ts-salobj.

v1.11.1
-------

* Improve handling of "no targets on queue" condition:
  * Add a custom exception to track when there are no new targets in the next allotted window.
  * Add new error code for this condition.
  * Improve error message.
* Pin version of ts_salobj and ts_idl in conda recipe.

v1.11.0
-------

* Implement estimate_next_target.
  This method steps into the future to estimate how long it will take for the next target to be available.
  It is mostly used in the advance_target_production_loop when there are no targets to determine how long it will take for the next target.
  Then it sets a timer task that the loop can wait on until it evaluates the queue again.
  It also sets a maximum time which the scheduler can accomodate without new targets.
  If it takes longer than the allotted time, the scheduler will go to fault.
* Support `program` field in unit tests for feature scheduler target.
* In `FeatureSchedulerTarget`, fill in `program` field in script configuration.
* In `FeatureSchedulerDriver` pass logger to `FeatureSchedulerTarget`.
* Add logger to `DriverTarget`.
* Add unit test for `FeatureSchedulerTarget` when running with multiple observations.
* In `FeatureSchedulerTarget` add support for multiple observations.
* Update setup.cfg to ignore everything under `doc/`.

v1.10.1
-------

* Add Jenkinsfile to build/upload documentation.
* Update documentation.
* Update .gitignore to ignore documentation build files.

v1.10.0
-------

* Updated unit tests for compatibility with ts_salobj 6.8, which is now required.

v1.9.0
------

* Implement telemetry stream parsing on Scheduler CSC.
* General improvements and bug fixes caught during night-time tests with the Auxiliary Telescope.

v1.8.0
------

* Replace calls to `salobj` methods that moved to new `utils` package.
* Improve how `salobj ` is imported in `tests/test_advanced_target_loop`.
* Move observing script setup to the `driver_configuration` section.
* Adds two new invalid configurations to check the CSC configuration schema.
* Reformat `all_fields` test configuration.
* Changes in the CSC configuration schema:
  * Make the top level CSC configuration reject `additionalProperties`.
    This was used to pass in configurations for the driver, but had the drawback that it did not check the top level against mistakes.
  * Add a new required configuration section for the driver; driver_configuration.
    This new section is basically an dictionary that users can rely on to pass in configurations for the drivers.
    The driver themselves will be in charge of verifying the configuration.
* Fix issue in test_simple_target_loop, where it was not configuring the scheduler with the correct configuration.
* Rename `DriverTarget.as_evt_topic` -> `DriverTarget.as_dict`.
* Fix issue in `advance_target_production_loop` when there are no target in the `target_queue`.
* Fix `test_advance_target_loop` unit test.
* Move `DriverTarget` into its own sub-module in `driver.



v1.7.0
------

* Replace lsst_sims with new rubin-sim conda package.
* Add conda recipe and packaging script.

v1.6.0
------

* Implement advance_target_production_loop.
* Update test_simple_target_loop:
  * load a sequential scheduler during the test.
  * check error code when testing that the queue is not running.
* Fix termination of simple_target_production_loop if something inside the try/except statement already put the CSC in FAULT.
* Minor update to test_driver to setup logging.
* Update test_csc to check error code when testing going to fault due to lack of observatory state updates.
* Fix issue that would cause the scheduler to continuously go to fault state when the pointing component is not enabled.
* Fix test SAL Scripts.
* Implement save/reset scheduler state to/from file in the base Driver, in the FeatureScheduler and in the SequentialScheduler.
* Remove usage of deprecated asynctest library.
* Reorganize scheduler_csc module.
  * Move SchedulerCscParameters to a utils submodule.
  * Move error codes to a utils submodule.
  * Move Script "non final states" to a utils submodule.
* Update scheduler CSC configuration to use new salobj methodology, using `config_schema.py` package instead of the `schema.yaml` file.
* Enable pytest-black.
* Support publishing CSC version.

v1.5.3
------

* Reformat code using black 20.
* Update documentation format.
