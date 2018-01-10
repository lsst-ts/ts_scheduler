.. _usage_label:

========
Usage
========

To use LSST Scheduler in a project::

    import ts_scheduler



.. _sim_env_label:

------------------------------
Simulated environment (SOCS)
------------------------------

The LSST scheduler is designed to be used by the Observatory Control System (OCS) and, as such, follow some strict
guidelines. For instance, one of the main features of the LSST scheduler is the communication middleware (DDS/SAL).
This middleware is responsible for all the communication from and to the scheduler (and, in fact, all other
observatory subsystems). This guarantees that the scheduler is fed with proper telemetry information and also that all
input/output communication is properly logged. During operations the LSST scheduler runs as a stand alone program
feeding from the telemetry stream and answering to requests for targets, all through this middleware interface.

In order to stress the system from the beginning, the simulated environment (SOCS) is also built upon this interface.
Which means that, when running a survey simulation, SOCS actually mimics the real operation of the scheduler. Further
information about SOCS can be found `here <https://lsst-sims.github.io/sims_ocs/>`_.

Basically, a simulation is done using the ``opsim4`` script provided by SOCS. This script will setup the simulation
environment, call ``scheduler.py``, initializing the scheduler, and wait for targets to observe. The scheduler then
gets all the parameters needed to configure itself and its submodules via the middleware communication and, once it is
done it will start serving targets to SOCS. A list of self contained modules that the scheduler has access to and that
are configured in the initialization process can be found at :ref:`submodules_label`.