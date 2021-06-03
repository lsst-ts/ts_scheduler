.. _Version_History:

===============
Version History
===============

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
