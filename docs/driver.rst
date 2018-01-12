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

A telemetry stream is available to the scheduler with crucial information regarding the state of the observatory
(telescope, camera, etc), environment (seeing, wind, clouds, sky brightness, etc), data quality and so on. During
real operations there is going to be a mix of real and simulated data that the scheduler uses. For instance, the
scheduler has access to information about the current state of the observatory as well as to an updated observatory
model that is capable of estimating slew times between different states. While the first is provided to the scheduler
using the DDS/SAL telemetry stream, the later is computed internally and made available to the scheduling algorithm
with an appropriate interface.

The scheduler itself also produces telemetry information that needs to be sent to the system for proper logging. Part
of it is done with using the :ref:`prop_sec` and :ref:`target_sec` interfaces but there is also others; some will be
handled directly by Driver (like informing the OCS of any issue with the scheduler or the lack of some telemetry
data), others have a default behaviour in the Driver and can be easily overwritten by the user algorithm (like
requesting for the u band filter to be swapped in to the carousel).

Here is a list of the current telemetry information available on the Driver and how to access it. This list will be
updated in the future as more information is made available. Some of this information can/need to be used by the
scheduling algorithm for target selection others may be for the scheduler internal logic.

- ``location [lsst.ts.dateloc.ObservatoryLocation]``: The scheduler can access information regarding the site
  location using.
- ``sunset_timestamp [float]``: The current sunset time stamp. Can be converted to MJD using
  ``lsst.ts.dateloc.DateProfile``.
- ``sunrise_timestamp [float]``: The current sunrise time stamp. Can be converted to MJD using
  ``lsst.ts.dateloc.DateProfile``.
- ``observatoryState [lsst.ts.observatory.model.ObservatoryState]``: The state of the observatory gathers general
  information about telescope position (alt/az), camera rotator angle, tracking and fail state, etc. This
  represents the state of the actual observatory (regardless of it being a simulation or real operation).
- ``observatoryModel [lsst.ts.observatory.model.ObservatoryModel]``: Inside Driver there are two distinct
  models, a main model and a secondary model. This is the main observatory model and is always synchronized with the
  actual observatory, thus providing information regarding available filters, slew time estimates from current state
  to desired states and so on. This is the property that needs to be used for passing information to the scheduling
  algorithm when building the telemetry stream. Some important methods of this object are:

    - ``observatoryModel.dateprofile.mjd [float]``: Current MJD date.
    - ``observatoryModel.dateprofile.lst_rad [float]``: Current LST in radians.
    - ``observatoryModel.get_slew_delay(Target) [float]``: Compute slew time between current state and the state
      required by Target.
    - ``observatoryModel.get_approximate_slew_delay(ra, dec, filter) [np.array]``: Compute approximate slew time
      between current state and (ra, dec, filter) combination (camera rotation is not considered yet).

  Look at the class definition to see other methods available.

- ``observatoryModel2 [lsst.ts.observatory.model.ObservatoryModel]``: The secondary observatory model available
  to the scheduler. This one is used internally to check that a state is valid to be acquired and tracked for
  a specified amount of time and, as such, may be unsynchronized with the observatory. For more information see
  :ref:`prop_targets_sec` and :ref:`validate_targets_sec` sections.
- ``seeing [float]``: This property provides the latest DIM seeing measurement in arcseconds. There's currently no
  skymap for the seeing but on can compute and scale internally using some model.
- ``cloud [float]``: The bulk cloud coverage measurement. There's currently no skymap for clouds available to the
  scheduler.
- ``wind []``: TBD
- ``temperatures []``: TBD (needed?)
- ``sky_brightness []``: TBD. There's currently no information regarding measured sky brightness to the scheduler, only
  internal models.
- ``sky [lsst.ts.astrosky.model.AstronomicalSkyModel]``: This property gives access to a sky model, including sun/moon
  position and sky brightness model (using OpSim fields).

The telemetry information required by the OCS to be produced by the scheduler is:

- ``need_filter_swap [bool]``: Set to ``True`` when the scheduler requires a filter swap during daytime operations.
- ``filter_to_unmount [str]``: In case a filter swap is needed, specifies which filter should be unmounted. Note that there
  is a limit on the observatory to which filter can be unmounted (default to u, y and z).
- ``filter_to_mount [str]``: In case a filter swap is needed, specifies which filter should be mounted.
- ``select_next_target() [Target]``: Return a target to observe. See :ref:`target_sec`.
- ``register_observation() [list]``: Validates targets and return list of successfully completed observations.

.. _prop_sec:

---------------------
Proposals
---------------------

NONONO

.. _target_sec:

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

.. _validate_targets_sec:

------------------------------------------
Validating targets
------------------------------------------

NONONO

------------------------------------------
Operation flow
------------------------------------------
