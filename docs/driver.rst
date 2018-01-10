=====================
Driver API
=====================

The operation of the LSST scheduler follow a set of rules that flow down for a series of documents. Most of the inner
operational workings of the scheduler (access to telemetry stream, middleware communication, etc) can be generalized,
enabling it to be connected to virtually any target selection algorithm. Even in these cases, a set of rules must be
followed to enable the proper function and logging of the observations to the database. These rules are described here
to ease the development of new algorithms.

.. figure:: _static/driver.jpg
   :scale: 50 %
   :alt: Driver diagram
   :align: center

   Diagram showing the Driver data structure and available methods.

Before proceeding make sure you read and understand the :ref:`scheduler_label` section.

---------------------
Configuration
---------------------

NONONO

---------------------
Telemetry
---------------------

NONONO

---------------------
Proposals
---------------------

NONONO

---------------------
Target
---------------------

The parameters describing a target includes but are not limited to:

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

------------------------------------------
Proposing/validating targets
------------------------------------------

NONONO