=====================
Driver API
=====================

The operation of the LSST scheduler follow a set of rules that flow down for a series of documents. Most of the inner
operational workings of the scheduler (access to telemetry stream, middleware communication, etc) can be generalized,
enabling it to be connected to virtually any target selection algorithm. Even in these cases, a set of rules must be
followed to enable the proper function and logging of the observations to the database. These rules are described here
to ease the development of new algorithms.

.. _driver-figure:

.. figure:: _static/driver.jpg
   :scale: 50 %
   :alt: Driver diagram
   :align: center

   Diagram showing the Driver data structure and all available methods. Not all properties of the class are showed here,
   only the most important ones.

Before proceeding make sure you read and understand the :ref:`scheduler_label` section.

---------------------
Configuration
---------------------

When starting a run, the scheduler is handled a series of configuration parameters to configure its submodules and the
scheduling algorithm (this later may change in the future for external scheduling algorithms). Some of the
configuration methods are quite self-explanatory and won't be expanded here, others have some subtleties and require
some explanation (given furthermore). In some cases, there are planned changes in the near future to accommodate
external scheduling algorithms while other are module-related and will likely be kept unchanged. If nothing is said,
assume no change will be made or will be required. The sequence of calls is as follows:

#. ``configure_duration``: Receives the duration of the survey in days. In the future, this could be moved to the next
   item in the list.
#. ``configure``: This method is used to configure some of the driver behaviour. The way it is right now, some
   of those parameters are related to the current scheduling algorithm and will be taken off. Others are more
   general parameters regarding the actual driver behaviour. The list of parameters is:

      - ``coadd_values``
      - ``time_balancing``
      - ``timecost_dc``
      - ``timecost_dt``
      - ``timecost_k``
      - ``timecost_weight``
      - ``night_boundary`` \*
      - ``ignore_sky_brightness``
      - ``ignore_airmass``
      - ``ignore_clouds``
      - ``ignore_seeing``
      - ``new_moon_phase_threshold`` \*

   Parameters marked with an \* are more general-behaviour and more likely to be kept. The others are particular to the
   current scheduler algorithm and may be removed.

#. ``configure_location``: Configures the observatory location submodule.
#. ``configure_telescope``: Configures the internal telescope kinematic models. There are two kinematic models inside
   driver. One provides access to telemetry and is synchronized with the telescope module, the other is used to check
   the telescope limits (see :ref:`prop_targets_sec` for further details).
#. ``configure_dome``:
#. ``configure_rotator``:
#. ``configure_camera``:
#. ``configure_slew``: This method configures the properties of telescope slew. Basically it states the actions
   required for a slew operation and how they must be performed. In combination with the kinematic model it enables the
   observatory model to properly estimate the slew time.
#. ``configure_optics``:
#. ``configure_park``:

The next step in the process is configuring the :ref:`prop_sec`. The procedure is designed to configure the current
scheduler algorithm and does not consider or allow too much freedom in the process. To start with, there is one call
to one of two different methods (``create_area_proposal`` or ``create_sequence_proposal``), for each proposal,
depending on the proposal type (either General or Sequence), each using a different set of parameters. A more general
approach would be to make a single call to a ``configure_proposals`` method responsible for setting up the entire
process.

It is important to note that, the ``Proposals`` needs to be properly set for the scheduler to work.

---------------------
Telemetry
---------------------

NONONO

.. _prop_sec:

---------------------
Proposals
---------------------

NONONO

---------------------
Target
---------------------

Change control documents LTS-347 specifies minimum parameters describing a target published by the scheduler.
Those are;

    * field ID, filter,
    * list of proposals, list of sequence IDs, list of values, target rank
    * part of a deep drilling event
    * RA, Dec, Angle,
    * number of exposures, list of exposure times,
    * expected LST, mount-Alt, mount-Az, Rot, dome-Alt, dome-Az at start of first exposure
    * expected maximum speeds for mount-Alt, mount-Az, Rot, dome-Alt, dome-Az during slew
    * expected slew time
    * expected airmass, sky brightness at start of first exposure
    * expected seeing, transparency at start of first exposure

The current implementation of the scheduler uses a slight more complex data structure. This can be seen on the figure
bellow.

.. _target-figure:

.. figure:: _static/target.jpg
   :scale: 50 %
   :alt: Target diagram
   :align: center

   Diagram showing the Target data structure and available methods.

See :ref:`prop_targets_sec` section to check how this class needs to be populated.

.. _prop_targets_sec:

------------------------------------------
Proposing targets
------------------------------------------

NONONO

------------------------------------------
Validating targets
------------------------------------------
