#########################
Scheduler
#########################

.. update the following links to point to your CSC
.. image:: https://img.shields.io/badge/SAL-API-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/Scheduler.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_scheduler
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_scheduler
.. image:: https://img.shields.io/badge/Jenkins-gray.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_scheduler/

.. _Overview:

Overview
========

The Scheduler Commandable SAL Component (CSC) is a software application in charge of computing a sequence of observations and sending them to the `ScriptQueue`_ CSC for execution.

.. _ScriptQueue: https://ts-scriptqueue.lsst.io

Instead of implementing the full logic to compute the sequence of observations, the Scheduler CSC implements a set of execution strategies and exposes an API for implementing algorithms (referred to in this document as "Scheduling Algorithms") that can be configured and called at runtime to produce a sequence of observations.
As part of the execution strategies, the CSC is also in charge of gathering telemetry from the different systems, including observatory state and weather information, and presenting them to the underlying algorithm in a well-defined and comprehensive way.

These details mostly drill down from higher-level requirements documents for the Vera Rubin Observatory Control System.

The relevant documents are;

* `LSE-30 <ls.lt/LSE-030>`__: Observatory System Specifications.
* `LSE-62 <ls.st/LSE-062>`__: Observatory Control System Requirements.
* `LSE-369 <ls.st/LSE-369>`__: Scheduler Requirements.

For information on the Feature Based Scheduler application, one of the options in computing sequence of observations, see the `Rubin Sim`_ package.

.. _Rubin Sim: https://rubin-sim.lsst.io

.. _User_Documentation:

User Documentation
==================

User-level documentation, found at the link below, is aimed at personnel looking to perform the standard use-cases/operations with the Scheduler.

This documentation page is intended for observatory operators and personnel that are planning on interacting with the Scheduler CSC for operational purposes.

.. toctree::
    user-guide/user-guide
    :maxdepth: 2

.. _Configuration:

Configuring the Scheduler
=========================

The configuration for the Scheduler is described at the following link.

This page will focus mainly on the Scheduler CSC configuration itself.
"Scheduling Algorithms" integrated with the CSC will probably have additional configuration files that are required.
Although this page contains information on how these additional configuration parameters are used, details on how to add them are left for the :ref:`Development_Documentation` section.

.. toctree::
    configuration/configuration
    :maxdepth: 1


.. _Development_Documentation:

Development Documentation
=========================

This area of documentation focuses on the classes used, API's, and how to participate to the development of the Scheduler software packages.

This documentation is intended for those developing "Scheduling Algorithms" and other inner features from the Scheduler.

.. toctree::
    developer-guide/developer-guide
    :maxdepth: 1

.. _Scheduler_Version_History:

Version History
===============

The version history of the Scheduler is found at the following link.

.. toctree::
    version-history
    :maxdepth: 1
