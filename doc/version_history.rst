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
