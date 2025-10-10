v2.6.0 (2025-10-10)
===================

New Features
------------

- Changed configuration repository from ts_config_ocs to ts_config_scheduler. (`OSW-847 <https://rubinobs.atlassian.net//browse/OSW-847>`_)


Other Changes and Additions
---------------------------

- Fixes documentation build. (`OSW-847 <https://rubinobs.atlassian.net//browse/OSW-847>`_)


v2.5.2 (2025-09-26)
===================

New Features
------------

- Added a ``close`` method to the ``Model`` class to cleanup resources. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)
- Added a ``close`` method to the ``SchedulerCSC`` (overriding the parent method) to call ``Model.cleanup``. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)


Bug Fixes
---------

- Fixed how lsst_efd_client.EfdClient patch is defined in ``tests/test_csc.py``. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)
- Updated the feature scheduler test configurations to reduce the memory footprint created when importing them.
  The Scheduler CSC loads these configurations by importing them.
  This caused an issue with the garbage collector that is not able to clenaup any resources created in the process. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)
- Updated unit test to handle the fact that now the driver class is deleted when the Scheduler is closed. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)
- Updated ``tests/test_csc_hot_start.py`` and ``tests/test_csc_warm_start.py`` to handle the removal of the conditions object from the test configuration. (`OSW-1128 <https://rubinobs.atlassian.net//browse/OSW-1128>`_)


v2.5.1 (2025-09-17)
===================

New Features
------------

- Added placeholder for new CSC commands; flush and reshedule, and mark them as extra commands for backwards compatibility. (`OSW-670 <https://rubinobs.atlassian.net//browse/OSW-670>`_)


v2.5.0 (2025-08-12)
===================

New Features
------------

- Initial implementation of handling targets of opportunity. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)
- Initial implementation of handling cloud maps. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)
- Added new LFAClient class to handle retrieving cloud data from the Large File Annex server. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)
- Added new ToOClient class to handle retrieving target of opportunity alerts from the EFD. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)


Bug Fixes
---------

- Improved the predicted scheduled implementation to take into account the current scheduled targets. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)
- Fixed a sky model timing issue in ``FeatureScheduler._format_conditions``.

  The method was not updating the timestamp in the sky model which was causing the method to calculate wrong values for the sun/moon and even sky brightness. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)
- Updated ``Model.load_observing_blocks`` to catch exceptions when parsing block files and augment the exception with the name of the file. (`OSW-527 <https://rubinobs.atlassian.net//browse/OSW-527>`_)


v2.4.1 (2025-06-02)
===================

Bug Fixes
---------

- Fixes condition when the FBS returns ``None`` as a target (e.g. no target condition). (`DM-51040 <https://rubinobs.atlassian.net//browse/DM-51040>`_)
- Fixes issue in the telemetry loop to handle setting the observatory state synchronization flag. (`DM-51040 <https://rubinobs.atlassian.net//browse/DM-51040>`_)


v2.4.0 (2025-05-08)
===================

New Features
------------

- Added observation_reason to the script configuration payload. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Added mapping of filter name to band name. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Set target name for the target payload. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)


Bug Fixes
---------

- Stopped overriding the rotSkyPos in the observation after target validation. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Fixed a bug in the Scheduler CSC stop command that would leave the detailed state as RUNNING if the target generation loop didn't stop in time and had to be cancelled. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Fixed how the FeatureSchedulerDriver retrieves a list of targets. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)


Documentation
-------------

- Added documentation about the target parameters that are passed from the Scheduler Target and the Block/SAL Scripts. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Added support for towncrier to manage version history. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)


Other Changes and Additions
---------------------------

- Added general improvements to the feature scheduler metadata translation.
  This included correct handling of band and filter name, passing scheduler_note as note and some others. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Updated some frequent logging messages to use trace level instead of debug. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Added new trace level to the logging module for the Scheduler. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Updated conda recipe to remove ts-idl, add label for xml version on test requirements and remove pin on numpy. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Replaced enumeration imports from idl to xml. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Updated the Scheduler CSC put_on_queue method to included additional metadata to the target event.
  This added the snapshot url in addition to the index of the first script of the block.
  It should help us track which scripts belong to each target as well as which snapshop was used to generate the target. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Added a timer task in the Scheduler CSC telemetry loop to ensure it is not executing faster than a heartbeat. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- Updated how rubin_scheduler version is imported. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
- For rubin_schedule v3.6 and above, replaced ID with target_id to get the id of the target from the feature based scheduler observation. (`DM-39506 <https://rubinobs.atlassian.net//browse/DM-39506>`_)
