# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_scheduler/blob/master/schema/Scheduler.yaml
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: Scheduler v8
description: Schema for Scheduler configuration files
definitions:
  instance_specific_config:
    description: Configuration for the Auxiliary Telescope Scheduler.
    type: object
    additionalProperties: false
    required:
      - driver_configuration
    allOf:
      -
        if:
          properties:
            driver_type:
              const: driver
        then:
            required: []
      -
        if:
          properties:
            driver_type:
              const: sequential
        then:
            required: ["sequential_driver_configuration"]
      -
        if:
          properties:
            driver_type:
              const: feature_scheduler
        then:
            required: ["feature_scheduler_driver_configuration"]
    properties:
      models:
        type: object
        description: Scheduler models configuration.
        additionalProperties: false
        properties:
          location:
            type: object
            properties:
              obs_site:
                type: object
                properties:
                  name:
                    description: Name of the observatory.
                    type: string
                  latitude:
                    description: Observatory Latitude (degrees).
                    type: number
                  longitude:
                    description: Observatory Longitude (degrees).
                    type: number
                  height:
                    description: Observatory height (meter).
                    type: number
                additionalProperties: false
            additionalProperties: false
          observatory_model:
            type: object
            properties:
              telescope:
                type: object
                properties:
                  altitude_minpos:
                    description: Minimum altitude from horizon (degrees)
                    type: number
                  altitude_maxpos:
                    description: Maximum altitude for zenith avoidance (degrees)
                    type: number
                  azimuth_minpos:
                    type: number
                    description: Minimum azimuth cable-wrap limit (degrees).
                  azimuth_maxpos:
                    type: number
                    description: Maximum azimuth cable-wrap limit (degrees).
                  altitude_maxspeed:
                    type: number
                    description: Maximum speed in altitude (degrees/sec).
                  altitude_accel:
                    type: number
                    description: Accelaration in altitude (degrees/sec^2).
                  altitude_decel:
                    type: number
                    description: Deceleration in altitude (degrees/sec^2).
                  azimuth_maxspeed:
                    type: number
                    description: Maximum speed in azimuth (degrees/sec).
                  azimuth_accel:
                    type: number
                    description: Accelaration in azimuth (degrees/sec^2).
                  azimuth_decel:
                    type: number
                    description: Deceleration in azimuth (degrees/sec^2).
                  settle_time:
                    type: number
                    description: Settle time.
                additionalProperties: false
              dome:
                type: object
                properties:
                  altitude_maxspeed:
                    type: number
                    description: Dome maximum speed in elevation (degrees/s).
                  altitude_accel:
                    type: number
                    description: Dome acceleration in elevation (degrees/s^2).
                  altitude_decel:
                    type: number
                    description: Dome deceleration in elevation (degrees/s^2).
                  altitude_freerange:
                    type: number
                    description: >-
                      Dome slit free-range in elevation (degrees). Specifies how much
                      the dome can move in elevation without blocking the telescope
                      FoV.
                  azimuth_maxspeed:
                    type: number
                    description: Dome maximum speed in azimuth (degrees/s).
                  azimuth_accel:
                    type: number
                    description: Dome acceleration in azimuth (degrees/s^2).
                  azimuth_decel:
                    type: number
                    description: Dome deceleration in azimuth (degrees/s^2).
                  azimuth_freerange:
                    type: number
                    description: >-
                      Dome slit free-range in azimuth (degrees). Specifies how much the
                      dome can move in azimuth without blocking the telescope FoV.
                  settle_time:
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
                    type: number
                    description: Minimum rotator position (degrees).
                  maxpos:
                    type: number
                    description: Maximum rotator position (degrees).
                  filter_change_pos:
                    type: number
                    description: Rotator position for filter changes (degrees).
                  maxspeed:
                    type: number
                    description: Maximum rotator speed (degrees/s).
                  accel:
                    type: number
                    description: Rotator acceleration (degrees/s^2).
                  decel:
                    type: number
                    description: Rotator deceleration (degrees/s^2).
                  follow_sky:
                    type: boolean
                    description: >-
                      If True enables the movement of the rotator during slews to put
                      North-Up. If range is insufficient, then the alignment is
                      North-Down. If the flag is False, then the rotator does not move
                      during the slews, it is only tracking during the exposures. Note
                      that this must be TRUE to allow *any* movement of the rotator
                      during a slew. FALSE locks the rotator.
                  resume_angle:
                    type: boolean
                    description: >-
                      If True enables the rotator to keep the image angle after a
                      filter change, moving back the rotator to the previous angle
                      after the rotator was placed in filter change position. If the
                      flag is False, then the rotator is left in the filter change
                      position. This must be TRUE to allow any movement of the
                      rotator after a filter change.
                additionalProperties: false
              camera:
                type: object
                properties:
                  readout_time:
                    type: number
                    description: Camera readout time (seconds).
                  shutter_time:
                    type: number
                    description: Time it takes to open/close camera shutter (seconds).
                  filter_change_time:
                    type: number
                    description: Time it takes to perform a filter change (seconds).
                  filter_max_changes_burst_num:
                    type: number
                    description: Maximum number of filter changes in a night.
                  filter_max_changes_burst_time:
                    type: number
                    description: Minimum time (seconds) between filter changes in a night.
                  filter_max_changes_avg_num:
                    type: number
                    description: Maximum average number of filter changes per year.
                  filter_max_changes_avg_time:
                    type: number
                    description: Maximum time (seconds) for the average number of filter changes.
                  filter_mounted:
                    type: array
                    description: >-
                      Initial state for the mounted filters. Empty positions must be
                      filled with id="" no (filter).
                  filter_removable:
                    type: array
                    description: List of mounted filters that are removable for swapping
                  filter_unmounted:
                    type: array
                    description: List of unmounted but available filters to swap
                additionalProperties: false
              optics_loop_corr:
                type: object
                properties:
                  tel_optics_ol_slope:
                    type: number
                    description: >-
                        Delay factor for Open Loop optics correction, in units of seconds/degrees.
                  tel_optics_cl_delay:
                    type: array
                    description: >-
                        Table of delay factors for Closed Loop optics correction according to the altitude
                        slew range.
                  tel_optics_cl_alt_limit:
                    type: array
                    description: Altitude ranges for optics closed loop correction.
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
                    description: >-
                      Which activity is required to complete before dome motion in altitude can start?
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
                    description: >-
                      Which activity is required to complete before dome motion
                      in azimuth can start?
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
                    description: >-
                      Which activity is required to complete before dome settle
                      in azimuth can start?
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
                additionalProperties: false
              park:
                type: object
                properties:
                  telescope_altitude:
                    type: number
                    description: Telescope altitude parking position (degrees).
                  telescope_azimuth :
                    type: number
                    description: Telescope azimuth parking position (degrees).
                  telescope_rotator:
                    type: number
                    description: Telescope rotator parking position (degrees).
                  dome_altitude:
                    type: number
                    description: Dome altitude parking position (degrees).
                  dome_azimuth :
                    type: number
                    description: Dome azimuth parking position (degrees).
                  filter_position:
                    type: string
                    description: Park filter position.
                additionalProperties: false
            additionalProperties: false
          sky:
            type: object
            properties:
              exclude_planets:
                type: boolean
                description: Flag to mask planets in sky brightness information.
            additionalProperties: false
          seeing:
            type: object
            properties:
              telescope_seeing:
                description: Telescope contribution to IQ (arcsec).
                type: number
              optical_design_seeing:
                description: Optics contribution to IQ (arcsec).
                type: number
              camera_seeing:
                description: Camera contribution to IQ (arcsec).
                type: number
              raw_seeing_wavelength:
                description: Wavelength of input zenith IQ (nm).
                type: number
              filter_list:
                description: List of filters for which to calculate seeing.
                type: array
              filter_effwavelens:
                description: Effective wavelengths for filters (nm).
                type: array
              throughputs_version:
                description: Version of the throughputs files
                type: string
            additionalProperties: false
      telemetry:
        type: object
        description: Scheduler telemetry configuration.
        additionalProperties: false
        properties:
          efd_name:
            type: string
            description: Name of the EFD instance telemetry should be queried from.
          too_client:
            type: object
            description: Configuration for the Target of Opportunity client.
            additionalProperties: false
            properties:
              topic_name:
                type: string
                description: The name of the topic with the ToO data in the EFD.
              delta_time:
                type: number
                description: How long in the past to look for ToO alerts (seconds)?
              db_name:
                type: string
                description: The name of the database where the topics are written.
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
                - fill_value
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
                csc_index:
                  description: Index of the CSC to query data from.
                  anyOf:
                    - type: "null"
                    - type: integer
                  default: null
                fill_value:
                  description: >-
                    Which value to assign the telemetry when no data point is
                    obtained.
                  anyOf:
                    - type: "null"
                    - type: number
      driver_type:
        description: >-
          Choose a driver to use from the available options.
        type: string
        enum:
          - "driver"
          - "sequential"
          - "feature_scheduler"
      sequential_driver_configuration:
        description: Configuration for the sequential driver.
        type: object
        additionalProperties: false
        required: ["observing_list"]
        properties:
          observing_list:
            description: Observing list.
            type: string
      feature_scheduler_driver_configuration:
        description: Configuration for the sequential driver.
        type: object
        additionalProperties: false
        required: ["scheduler_config"]
        properties:
          scheduler_config:
            description: Scheduler configuration path.
            type: string
          observation_database_name:
            description: >-
              Path to the observations database. This is an sqlite database the
              feature scheduler uses to store its observations history.
            type: string
      driver_configuration:
        description: >-
          Configuration section dedicated to the driver. This is a dictionary with
          no fixed setting and can be adapted to the different drivers. The driver
          will add a verification of the schema.
        type: object
        additionalProperties: false
        properties:
          parameters:
            description: Base driver parameters.
            type: object
            additionalProperties: false
            properties:
              night_boundary:
                description: Sun altitude for the start of the night.
                type: number
              new_moon_phase_threshold:
                description: Moon illumination (1/100) for dark time.
                type: number
              general_propos:
                description: List of general proposals.
                type: array
                items:
                  type: string
              sequence_propos:
                description: List of sequence proposals.
                type: array
                items:
                  type: string
              cwfs_block_name:
                description: Name of the CWFS block.
                type: string
          stop_tracking_observing_script_name:
            description: >-
              Name of the SAL script used to stop the telescope if there is no
              target from the Scheduler.
            type: string
          stop_tracking_observing_script_is_standard:
            description: Is the stop tracking script standard?
            type: boolean
      startup_type:
        description: >-
          The method used to startup the scheduler. See ts-scheduler.lsst.io for
          more information about the definition of each of these options.
        type: string
        enum:
        - HOT
        - WARM
        - COLD
      startup_database:
        description: >-
          Path to the file holding scheduler state or observation database to be
          used on WARM or COLD start.
        type: string
      mode:
        description: >-
          The mode of operation of the scheduler. This basically chooses one of
          the available target production loops.
        type: string
        enum:
        - SIMPLE
        - ADVANCE
        - DRY
      n_targets:
        description: Number of targets to put in the queue ahead of time.
        type: integer
      predicted_scheduler_window:
        description: Size of predicted scheduler window, in hours.
        type: number
      loop_sleep_time:
        description: >-
          How long should the target production loop wait when there is a wait
          event. Unit = seconds.
        type: number
      cmd_timeout:
        description: Global command timeout. Unit = seconds.
        type: number
      observing_script:
        description: Name of the default observing script.
        type: string
      observing_script_is_standard:
        description: Is default observing script standard?
        type: boolean
      max_scripts:
        description: Maximum number of scripts to keep track of
        type: integer
      path_observing_blocks:
        description: >-
          Path to the directory containing the observing blocks definition.
          This should be relative to the CSC configuration path.
        type: string
      instrument_name:
        description: Name of the instrument.
        type: string
        enum:
          - LATISS
          - MTCamera
          - CCCamera
      filter_band_mapping:
        description: >-
            The mapping between the filter name (the element identifier)
            and the band name (ugrizy).
        type: object
        additionalProperties:
            type: string
      filter_names_separator:
        description: >-
            Character used to separate the filter names.
        type: string
type: object
additionalProperties: false
properties:
  s3instance:
    description: >-
      Large File Annex S3 instance, for example "tuc" (Tucson Test Stand),
      "ls" (Base Test Stand), "cp" (summit).
    type: string
  script_paths:
    description: >-
      Path to the standard and external scripts. This is used to validate blocks.
      If not provided, will fallback to requestig from the ScriptQueue.
    type: object
    additionalProperties: false
    properties:
      standard:
        description: Path to the standard scripts.
        type: string
      external:
        description: Path to the external scripts.
        type: string
    required:
      - standard
      - external
  maintel:
    $ref: "#/definitions/instance_specific_config"
  auxtel:
    $ref: "#/definitions/instance_specific_config"
  ocs:
    $ref: "#/definitions/instance_specific_config"
"""
)
