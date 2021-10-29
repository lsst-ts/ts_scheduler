# This file is part of ts_scheduler.
#
# Developed for Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/master/schema/Scheduler.yaml
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: Scheduler v3
description: Schema for Scheduler configuration files
type: object
additionalProperties: false
required:
  - driver_configuration
properties:
  s3instance:
    description: >-
      Large File Annex S3 instance, for example "nts", "tuc", "ls", "cp".
    type: string
    default: "cp"
  driver_type:
    description: >-
      Choose a driver to use. This should be an import string that is passed
      to `importlib.import_module()`. Model will look for a subclass of Driver
      class inside the module.
    type: string
    default: "lsst.ts.scheduler.driver.driver"
  driver_configuration:
    description: >-
      Configuration section dedicated to the driver. This is a dictionary with
      no fixed setting and can be adapted to the different drivers. The driver
      will add a verification of the schema.
    type: object
    additionalProperties: true
    properties:
      parameters:
        description: Base driver parameters.
        type: object
        additionalProperties: false
        properties:
          night_boundary:
            decription: Sun altitude for the start of the night.
            default: -12.0
            type: number
          new_moon_phase_threshold:
            description: Moon ilumination (1/100) for dark time.
            default: 20.0
            type: number
      default_observing_script_name:
        description: >-
          Name of the default observing script. This is used by default in the
          driver. The application can override them internally when needed.
        type: string
        default: standard_visit.py
      default_observing_script_is_standard:
        description: Is the default observing script standard?
        type: boolean
        default: true
      stop_tracking_observing_script_name:
        description: >-
          Name of the SAL script used to stop the telescope if there is no
          target from the Scheduler.
        type: string
        default: stop_tracking.py
      stop_tracking_observing_script_is_standard:
        description: Is the stop tracking script standard?
        type: boolean
        default: true
  startup_type:
    description: The method used to startup the scheduler.
    type: string
    enum:
    - HOT
    - WARM
    - COLD
    default: "HOT"
  startup_database:
    description: >-
      Path to the file holding scheduler state or observation database to be
      used on WARM or COLD start.
    type: string
    default: " "
  mode:
    description: >-
      The mode of operation of the scheduler. This basically chooses one of
      the available target production loops.
    type: string
    default: "SIMPLE"
    enum:
    - SIMPLE
    - ADVANCE
    - DRY
  n_targets:
    description: Number of targets to put in the queue ahead of time.
    type: integer
    default: 1
  predicted_scheduler_window:
    description: Size of predicted scheduler window, in hours.
    type: number
    default: 2.
  loop_sleep_time:
    description: >-
      How long should the target production loop wait when there is a wait
      event. Unit = seconds.
    type: number
    default: 1.
  cmd_timeout:
    description: Global command timeout. Unit = seconds.
    type: number
    default: 60.
  observing_script:
    description: Name of the default observing script.
    type: string
    default: 'standard_visit.py'
  observing_script_is_standard:
    description: Is default observing script standard?
    type: boolean
    default: true
  max_scripts:
    description: Maximum number of scripts to keep track of
    type: integer
    default: 100
  models:
    type: object
    description: Scheduler models configuration.
    additionalProperties: false
    default:
      location:
        obs_site:
          name: Vera Rubin Observatory
    properties:
      location:
        type: object
        default:
          obs_site:
            name: Vera Rubin Observatory
        properties:
          obs_site:
            type: object
            properties:
              name:
                description: Name of the observatory.
                type: string
                default: Vera Rubin Observatory
              latitude:
                description: Observatory Latitude (degrees).
                type: number
                default: -30.244728
              longitude:
                description: Observatory Longitude (degrees).
                type: number
                default: -70.747698
              height:
                description: Observatory height (meter).
                type: number
                default: 2663.0
            additionalProperties: false
        additionalProperties: false
      observatory_model:
        type: object
        default:
          telescope:
            altitude_minpos: 20.0
            altitude_maxpos: 86.5
            azimuth_minpos: -270.0
            azimuth_maxpos: 270.0
            altitude_maxspeed: 3.5
            altitude_accel: 3.5
            altitude_decel: 3.5
            azimuth_maxspeed: 7.0
            azimuth_accel: 7.0
            azimuth_decel: 7.0
            settle_time: 3.0
        properties:
          telescope:
            type: object
            properties:
              altitude_minpos:
                default: 20.0
                description: Minimum altitude from horizon (degrees)
                type: number
              altitude_maxpos:
                default: 86.5
                description: Maximum altitude for zenith avoidance (degrees)
                type: number
              azimuth_minpos:
               default: -270.0
               type: number
               description: Minimum azimuth cable-wrap limit (degrees).
              azimuth_maxpos:
                default: 270.0
                type: number
                description: Maximum azimuth cable-wrap limit (degrees).
              altitude_maxspeed:
                type: number
                default: 3.5
                description: Maximum speed in altitude (degrees/sec).
              altitude_accel:
                type: number
                default: 3.5
                description: Accelaration in altitude (degrees/sec^2).
              altitude_decel:
                type: number
                default: 3.5
                description: Deceleration in altitude (degrees/sec^2).
              azimuth_maxspeed:
                type: number
                default: 7.0
                description: Maximum speed in azimuth (degrees/sec).
              azimuth_accel:
                type: number
                default: 7.0
                description: Accelaration in azimuth (degrees/sec^2).
              azimuth_decel:
                type: number
                default: 7.0
                description: Deceleration in azimuth (degrees/sec^2).
              settle_time:
                type: number
                default: 3.0
                description: Settle time.
            additionalProperties: false
          dome:
            type: object
            properties:
              altitude_maxspeed:
                default: 1.75
                type: number
                description: Dome maximum speed in elevation (degrees/s).
              altitude_accel:
                default: 0.875
                type: number
                description: Dome acceleration in elevation (degrees/s^2).
              altitude_decel:
                default: 0.875
                type: number
                description: Dome deceleration in elevation (degrees/s^2).
              altitude_freerange:
                default: 0.
                type: number
                description: >-
                  Dome slit free-range in elevation (degrees). Specify how much
                  the dome can move in elevation without blocking the telescope
                  FoV.
              azimuth_maxspeed:
                default: 1.5
                type: number
                description: Dome maximum speed in azimuth (degrees/s).
              azimuth_accel:
                default: 0.75
                type: number
                description: Dome acceleration in azimuth (degrees/s^2).
              azimuth_decel:
                default: 0.75
                type: number
                description: Dome deceleration in azimuth (degrees/s^2).
              azimuth_freerange:
                default: 4.0
                type: number
                description: >-
                  Dome slit free-range in azimuth (degrees). Specify how much the
                  dome can move in azimuth without blocking the telescope FoV.
              settle_time:
                default: 1.0
                type: number
                description: >-
                  Dome axis settle time (seconds). This is applied on the
                  individual axis (elevation/azimuth) only if the respective
                  "free range" parameter is zero.
            additionalProperties: false
          rotator:
            type: object
            properties:
              minpos:
                default: -90.0
                type: number
                description: Minimum rotator position (degrees).
              maxpos:
                type: number
                description: Maximum rotator position (degrees).
                default: 90.0
              filter_change_pos:
                type: number
                default: 0.0
                description: Rotator position for filter changes (degrees).
              maxspeed:
                type: number
                description: Maximum rotator speed (degrees/s).
                default: 3.5
              accel:
                type: number
                description: Rotator acceleration (degrees/s^2).
                default: 1.0
              decel:
                type: number
                description: Rotator deceleration (degrees/s^2).
                default: 1.0
              follow_sky:
                type: boolean
                description: >-
                  If True enables the movement of the rotator during slews to put
                  North-Up. If range is insufficient, then the alignment is
                  North-Down. If the flag is False, then the rotator does not move
                  during the slews, it is only tracking during the exposures. Note
                  that this must be TRUE to allow *any* movement of the rotator
                  during a slew. FALSE locks the rotator.
                default: True
              resume_angle:
                type: boolean
                description: >-
                  If True enables the rotator to keep the image angle after a
                  filter change, moving back the rotator to the previous angle
                  after the rotator was placed in filter change position. If the
                  flag is False, then the rotator is left in the filter change
                  position. This must be TRUE to allow any movement of the
                  rotator after a filter change.
                default: true
            additionalProperties: false
          camera:
            type: object
            properties:
              readout_time:
                type: number
                decription: Camera readout time (seconds).
                default: 2.0
              shutter_time:
                type: number
                description: Time it takes to open/close camera shutter (seconds).
                default: 1.0
              filter_change_time:
                type: number
                description: Time it takes to perform a filter change (seconds).
                default: 120.0
              filter_max_changes_burst_num:
                type: number
                description: Maximum number of filter changes in a night.
                default: 1.
              filter_max_changes_burst_time:
                type: number
                description: Minimum time (seconds) between filter changes in a night.
                default: 0
              filter_max_changes_avg_num:
                type: number
                description: Maximum average number of filter changes per year.
                default: 3000
              filter_max_changes_avg_time:
                type: number
                description: Maximum time (seconds) for the average number of filter changes.
                default: 31557600.0
              filter_mounted:
                type: array
                description: >-
                  Initial state for the mounted filters. Empty positions must be
                  filled with id="" no (filter).
                default: [g, r, i, z, y]
              filter_removable:
                type: array
                description: List of mounted filters that are removable for swapping
                default: [y, z]
              filter_unmounted:
                type: array
                description: List of unmounted but available filters to swap
                default: [u]
            additionalProperties: false
          optics_loop_corr:
            type: object
            properties:
              tel_optics_ol_slope:
                type: number
                description: >-
                    Delay factor for Open Loop optics correction, in units of seconds/degrees.
                default: 0.2857
              tel_optics_cl_delay:
                type: array
                description: >-
                    Table of delay factors for Closed Loop optics correction according to the altitude
                    slew range.
                default: [0.0, 36.0]
              tel_optics_cl_alt_limit:
                type: array
                description: Altitude ranges for optics closed loop correction.
                default: [0.0, 9.0, 90.0]
            additionalProperties: false
          slew:
            type: object
            description: >-
              Specify dependencies for different slew activities. Possible values for the
              arrays are: telalt, telaz, telrot, telsettle, telopticsopenloop,
              telopticsclosedloop, domalt, domaz, domazsettle, filter, readout, exposures.
            properties:
              prereq_telalt:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: >-
                  Which activity is required to complete before telescope motion in altitude can start?
                default: []
              prereq_telaz:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: >-
                  Which activity is required to complete before telescope motion in azimuth can start?
                default: []
              prereq_telrot:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before rotaro motion can start?
                default: []
              prereq_telsettle:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before telescope settle starts?
                default: [telalt,telaz]
              prereq_telopticsopenloop:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: >-
                  Which activity is required to complete before telescope optics open loop can start?
                default: [telalt,telaz]
              prereq_telopticsclosedloop:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: >-
                  Which activity is required to complete before telescope optics closed loop can start?
                default: [domalt,domazsettle,telsettle,readout,telopticsopenloop,filter,telrot]
              prereq_domalt:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before dome motion in altitude can start?
                default: []
              prereq_domaz:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before dome motion in azimuth can start?
                default: []
              prereq_domazsettle:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before dome settle in azimuth can start?
                default: [domaz]
              prereq_filter:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before filter change can start?
                default: []
              prereq_readout:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before readout can start?
                default: []
              prereq_exposures:
                type: array
                items:
                  type: string
                  enum:
                    - "telalt"
                    - "telaz"
                    - "telrot"
                    - "telsettle"
                    - "telopticsopenloop"
                    - "telopticsclosedloop"
                    - "domalt"
                    - "domaz"
                    - "domazsettle"
                    - "filter"
                    - "readout"
                    - "exposures"
                description: Which activity is required to complete before exposure can start?
                default: [telopticsclosedloop]
            additionalProperties: false
          park:
            type: object
            properties:
              telescope_altitude:
                type: number
                description: Telescope altitude parking position (degrees).
                default: 86.5
              telescope_azimuth :
                type: number
                description: Telescope azimuth parking position (degrees).
                default:  0.0
              telescope_rotator:
                type: number
                description: Telescope rotator parking position (degrees).
                default:  0.0
              dome_altitude:
                type: number
                description: Dome altitude parking position (degrees).
                default: 90.0
              dome_azimuth :
                type: number
                description: Dome azimuth parking position (degrees).
                default:  0.0
              filter_position:
                type: string
                description: Park filter position.
                default: r
            additionalProperties: false
        additionalProperties: false
      sky:
        type: object
        properties:
          exclude_planets:
            type: boolean
            description: Flag to mask planets in sky brightness information.
            default: true
        additionalProperties: false
      seeing:
        type: object
        properties:
          telescope_seeing:
            description: Telescope contribution to IQ (arcsec).
            type: number
            default: 0.25
          optical_design_seeing:
            description: Optics contribution to IQ (arcsec).
            type: number
            default: 0.08
          camera_seeing:
            description: Camera contribution to IQ (arcsec).
            type: number
            default: 0.30
          raw_seeing_wavelength:
            description: Wavelength of input zenith IQ (nm).
            type: number
            default: 500
          filter_list:
            description: List of filters for which to calculate seeing.
            type: array
            default: ['u', 'g', 'r', 'i', 'z', 'y']
          filter_effwavelens:
            description: Effective wavelengths for filters (nm).
            type: array
            default: [367.06988658, 482.68517118, 622.32403587, 754.59752265, 869.09018708, 971.02780848]
          throughputs_version:
            description: Version of the throughputs files
            type: string
            default: '1.1'
        additionalProperties: false
  telemetry:
    type: object
    description: Scheduler telemetry configuration.
    additionalProperties: false
    default:
      efd_name: summit_efd
    properties:
      efd_name:
        type: string
        description: Name of the EFD instance telemetry should be queried from.
        default: summit_efd
      streams:
        type: array
        items:
          type: object
          additionalProperties: false
          required:
            - name
            - efd_table
            - efd_columns
            - efd_delta_time
          properties:
            name:
              type: string
              description: Name of the telemetry stream.
            efd_table:
              type: string
              description: Which EFD table to query data from.
            efd_columns:
              type: array
              items:
                type: string
              minItems: 1
            efd_delta_time:
              description: >-
                Length of history to request from the EFD (in seconds).
              type: number
              exclusiveMinimum: 0
            fill_value:
              description: >-
                Which value to assign the telemetry when no data point is
                obtained.
              default: null
              anyOf:
                - type: "null"
                - type: number
"""
)
