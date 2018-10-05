============
Installation
============

The scheduler is the part of the system responsible for generating observations and, as such, there is little it can
do alone. You will probably need to have sims_ocs installed before using the LSST scheduler. Installing the sims_ocs
package can be tricky because of the required middleware communication objects and libraries. You can work around
this using one of the provided docker containers see :ref:`docker_container_sec`.

Using eups (recommended)::

    $ eups distrib install ts_scheduler -t latest

With easy_install::

    $ easy_install ts_scheduler

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv ts_scheduler
    $ pip install ts_scheduler

.. _docker_container_sec:

Docker containers
---------------------

You can find docker containers with the latest official release of the code
`here <https://hub.docker.com/r/oboberg/opsim4/>`_. You will find instructions on how to setup and run the container
and simulations on the link. These containers are already setup
with the full simulation environment so you won't need to worry about installing sims_ocs or even ts_scheduler.
