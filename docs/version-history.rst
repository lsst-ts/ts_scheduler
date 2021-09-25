.. _Version_History:

===============
Version History
===============

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
