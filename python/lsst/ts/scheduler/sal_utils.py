
import math
import numpy
import logging
import logging.handlers


from SALPY_scheduler import SAL_scheduler
from SALPY_scheduler import scheduler_logevent_summaryStateC
from SALPY_scheduler import scheduler_logevent_needFilterSwapC
from SALPY_scheduler import scheduler_logevent_targetC
from SALPY_scheduler import scheduler_logevent_validSettingsC
from SALPY_scheduler import scheduler_timeHandlerC
from SALPY_scheduler import scheduler_observatoryStateC
from SALPY_scheduler import scheduler_bulkCloudC
from SALPY_scheduler import scheduler_seeingC
from SALPY_scheduler import scheduler_observationC
from SALPY_scheduler import scheduler_schedulerConfigC
from SALPY_scheduler import scheduler_driverConfigC
from SALPY_scheduler import scheduler_obsSiteConfigC
from SALPY_scheduler import scheduler_telescopeConfigC
from SALPY_scheduler import scheduler_domeConfigC
from SALPY_scheduler import scheduler_rotatorConfigC
from SALPY_scheduler import scheduler_cameraConfigC
from SALPY_scheduler import scheduler_slewConfigC
from SALPY_scheduler import scheduler_opticsLoopCorrConfigC
from SALPY_scheduler import scheduler_parkConfigC
from SALPY_scheduler import scheduler_generalPropConfigC
from SALPY_scheduler import scheduler_sequencePropConfigC
from SALPY_scheduler import scheduler_interestedProposalC
from SALPY_scheduler import scheduler_surveyTopologyC
from SALPY_scheduler import scheduler_command_enterControlC
from SALPY_scheduler import scheduler_command_enableC
from SALPY_scheduler import scheduler_command_startC


from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.observatory.model import Target, Observation

__all__ = ["SALUtils"]

class SALUtils(SAL_scheduler):

    def __init__(self, timeout):

        super(SALUtils, self).__init__()

        self.log = logging.getLogger("SALUtils")

        self.setDebugLevel(0)

        self.sal_sleeper = 0.1
        self.main_loop_timeouts = timeout

        self.topic_summaryState = scheduler_logevent_summaryStateC()
        self.topicTarget = scheduler_logevent_targetC()
        self.topicFilterSwap = scheduler_logevent_needFilterSwapC()
        self.topicValidSettings = scheduler_logevent_validSettingsC()

        self.topic_schedulerConfig = scheduler_schedulerConfigC()
        self.topic_driverConfig = scheduler_driverConfigC()
        self.topic_obsSiteConfig = scheduler_obsSiteConfigC()
        self.topic_telescopeConfig = scheduler_telescopeConfigC()
        self.topic_domeConfig = scheduler_domeConfigC()
        self.topic_rotatorConfig = scheduler_rotatorConfigC()
        self.topic_cameraConfig = scheduler_cameraConfigC()
        self.topic_slewConfig = scheduler_slewConfigC()
        self.topic_opticsConfig = scheduler_opticsLoopCorrConfigC()
        self.topic_parkConfig = scheduler_parkConfigC()
        self.topic_areaDistPropConfig = scheduler_generalPropConfigC()
        self.topic_sequencePropConfig = scheduler_sequencePropConfigC()
        self.topicTime = scheduler_timeHandlerC()
        self.topicObservatoryState = scheduler_observatoryStateC()
        self.topic_cloud = scheduler_bulkCloudC()
        self.topic_seeing = scheduler_seeingC()
        self.topicObservation = scheduler_observationC()
        self.tInterestedProposal = scheduler_interestedProposalC()
        self.topic_schedulerTopology = scheduler_surveyTopologyC()

        self.topic_command_enterControl = scheduler_command_enterControlC()
        self.topic_command_enable = scheduler_command_enableC()
        self.topic_command_start = scheduler_command_startC()

    def start(self):
        self.log.info("Starting pub/sub initialization")

        self.salEvent("scheduler_logevent_summaryState")
        self.salEvent("scheduler_logevent_target")
        self.salEvent("scheduler_logevent_needFilterSwap")
        self.salEvent("scheduler_logevent_validSettings")

        self.salProcessor("scheduler_command_enterControl")
        self.salProcessor("scheduler_command_enable")
        self.salProcessor("scheduler_command_start")

        self.salTelemetryPub("scheduler_schedulerConfig")
        self.salTelemetryPub("scheduler_driverConfig")
        self.salTelemetryPub("scheduler_obsSiteConfig")
        self.salTelemetryPub("scheduler_telescopeConfig")
        self.salTelemetryPub("scheduler_domeConfig")
        self.salTelemetryPub("scheduler_rotatorConfig")
        self.salTelemetryPub("scheduler_cameraConfig")
        self.salTelemetryPub("scheduler_slewConfig")
        self.salTelemetryPub("scheduler_opticsLoopCorrConfig")
        self.salTelemetryPub("scheduler_parkConfig")
        self.salTelemetryPub("scheduler_generalPropConfig")
        self.salTelemetryPub("scheduler_sequencePropConfig")
        self.salTelemetryPub("scheduler_interestedProposal")
        self.salTelemetryPub("scheduler_surveyTopology")

        self.salTelemetrySub("scheduler_timeHandler")
        self.salTelemetrySub("scheduler_observatoryState")
        self.salTelemetrySub("scheduler_bulkCloud")
        self.salTelemetrySub("scheduler_seeing")
        self.salTelemetrySub("scheduler_observation")

        self.log.info("Finished pub/sub initialization")

    @staticmethod
    def rtopic_driver_config(topic_driver_config):

        confdict = {}
        confdict["ranking"] = {}
        confdict["ranking"]["coadd_values"] = topic_driver_config.coaddValues
        confdict["ranking"]["time_balancing"] = topic_driver_config.timeBalancing
        confdict["ranking"]["timecost_time_max"] = topic_driver_config.timecostTimeMax
        confdict["ranking"]["timecost_time_ref"] = topic_driver_config.timecostTimeRef
        confdict["ranking"]["timecost_cost_ref"] = topic_driver_config.timecostCostRef
        confdict["ranking"]["timecost_weight"] = topic_driver_config.timecostWeight
        confdict["ranking"]["filtercost_weight"] = topic_driver_config.filtercostWeight
        confdict["ranking"]["propboost_weight"] = topic_driver_config.propboostWeight
        confdict["ranking"]["lookahead_window_size"] = topic_driver_config.lookaheadWindowSize
        confdict["ranking"]["lookahead_bonus_weight"] = topic_driver_config.lookaheadBonusWeight
        confdict["constraints"] = {}
        confdict["constraints"]["night_boundary"] = topic_driver_config.nightBoundary
        confdict["constraints"]["ignore_sky_brightness"] = topic_driver_config.ignoreSkyBrightness
        confdict["constraints"]["ignore_airmass"] = topic_driver_config.ignoreAirmass
        confdict["constraints"]["ignore_clouds"] = topic_driver_config.ignoreClouds
        confdict["constraints"]["ignore_seeing"] = topic_driver_config.ignoreSeeing
        confdict["darktime"] = {}
        confdict["darktime"]["new_moon_phase_threshold"] = topic_driver_config.newMoonPhaseThreshold
        confdict["startup"] = {}
        confdict["startup"]["type"] = topic_driver_config.startupType
        confdict["startup"]["database"] = topic_driver_config.startupDatabase

        return confdict

    @staticmethod
    def wtopic_driver_config(topic, config):

        topic.coaddValues = config.sched_driver.coadd_values
        topic.timeBalancing = config.sched_driver.time_balancing
        topic.timecostTimeMax = config.sched_driver.timecost_time_max
        topic.timecostTimeRef = config.sched_driver.timecost_time_ref
        topic.timecostCostRef = config.sched_driver.timecost_cost_ref
        topic.timecostWeight = config.sched_driver.timecost_weight
        topic.filtercostWeight = config.sched_driver.filtercost_weight
        topic.propboostWeight = config.sched_driver.propboost_weight
        topic.nightBoundary = config.sched_driver.night_boundary
        topic.newMoonPhaseThreshold = config.sched_driver.new_moon_phase_threshold
        topic.ignoreSkyBrightness = config.sched_driver.ignore_sky_brightness
        topic.ignoreAirmass = config.sched_driver.ignore_airmass
        topic.ignoreClouds = config.sched_driver.ignore_clouds
        topic.ignoreSeeing = config.sched_driver.ignore_seeing
        topic.lookaheadWindowSize = config.sched_driver.lookahead_window_size
        topic.lookaheadBonusWeight = config.sched_driver.lookahead_bonus_weight
        topic.startupType = config.sched_driver.startup_type
        topic.startupDatabase = config.sched_driver.startup_database

    @staticmethod
    def rtopic_location_config(topic_location_config):

        confdict = {}
        confdict["obs_site"] = {}
        confdict["obs_site"]["name"] = topic_location_config.name
        confdict["obs_site"]["latitude"] = topic_location_config.latitude
        confdict["obs_site"]["longitude"] = topic_location_config.longitude
        confdict["obs_site"]["height"] = topic_location_config.height

        return confdict

    @staticmethod
    def wtopic_location_config(obs_site_conf, config):

        obs_site_conf.name = config.observing_site.name
        obs_site_conf.latitude = config.observing_site.latitude
        obs_site_conf.longitude = config.observing_site.longitude
        obs_site_conf.height = config.observing_site.height
        obs_site_conf.pressure = config.observing_site.pressure
        obs_site_conf.temperature = config.observing_site.temperature
        obs_site_conf.relativeHumidity = config.observing_site.relative_humidity

    @staticmethod
    def rtopic_telescope_config(topic_telescope_config):

        confdict = {}
        confdict["telescope"] = {}
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitudeMinpos
        confdict["telescope"]["altitude_maxpos"] = topic_telescope_config.altitudeMaxpos
        confdict["telescope"]["azimuth_minpos"] = topic_telescope_config.azimuthMinpos
        confdict["telescope"]["azimuth_maxpos"] = topic_telescope_config.azimuthMaxpos
        confdict["telescope"]["altitude_maxspeed"] = topic_telescope_config.altitudeMaxspeed
        confdict["telescope"]["altitude_accel"] = topic_telescope_config.altitudeAccel
        confdict["telescope"]["altitude_decel"] = topic_telescope_config.altitudeDecel
        confdict["telescope"]["azimuth_maxspeed"] = topic_telescope_config.azimuthMaxspeed
        confdict["telescope"]["azimuth_accel"] = topic_telescope_config.azimuthAccel
        confdict["telescope"]["azimuth_decel"] = topic_telescope_config.azimuthDecel
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitudeMinpos
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitudeMinpos
        confdict["telescope"]["altitude_minpos"] = topic_telescope_config.altitudeMinpos
        confdict["telescope"]["settle_time"] = topic_telescope_config.settleTime

        return confdict

    @staticmethod
    def wtopic_telescope_config(tel_conf, config):

        tel_conf.altitudeMinpos = config.observatory.telescope.altitude_minpos
        tel_conf.altitudeMaxpos = config.observatory.telescope.altitude_maxpos
        tel_conf.altitudeMaxspeed = config.observatory.telescope.altitude_maxspeed
        tel_conf.altitudeAccel = config.observatory.telescope.altitude_accel
        tel_conf.altitudeDecel = config.observatory.telescope.altitude_decel
        tel_conf.azimuthMinpos = config.observatory.telescope.azimuth_minpos
        tel_conf.azimuthMaxpos = config.observatory.telescope.azimuth_maxpos
        tel_conf.azimuthMaxspeed = config.observatory.telescope.azimuth_maxspeed
        tel_conf.azimuthAccel = config.observatory.telescope.azimuth_accel
        tel_conf.azimuthDecel = config.observatory.telescope.azimuth_decel
        tel_conf.settleTime = config.observatory.telescope.settle_time

    @staticmethod
    def rtopic_dome_config(topic_dome_config):

        confdict = {}
        confdict["dome"] = {}
        confdict["dome"]["altitude_maxspeed"] = topic_dome_config.altitudeMaxspeed
        confdict["dome"]["altitude_accel"] = topic_dome_config.altitudeAccel
        confdict["dome"]["altitude_decel"] = topic_dome_config.altitudeDecel
        confdict["dome"]["altitude_freerange"] = topic_dome_config.altitudeFreerange
        confdict["dome"]["azimuth_maxspeed"] = topic_dome_config.azimuthMaxspeed
        confdict["dome"]["azimuth_accel"] = topic_dome_config.azimuthAccel
        confdict["dome"]["azimuth_decel"] = topic_dome_config.azimuthDecel
        confdict["dome"]["azimuth_freerange"] = topic_dome_config.azimuthFreerange
        confdict["dome"]["settle_time"] = topic_dome_config.settleTime

        return confdict

    @staticmethod
    def wtopic_dome_config(dome_conf, config):

        dome_conf.altitudeMaxspeed = config.observatory.dome.altitude_maxspeed
        dome_conf.altitudeAccel = config.observatory.dome.altitude_accel
        dome_conf.altitudeDecel = config.observatory.dome.altitude_decel
        dome_conf.altitudeFreerange = config.observatory.dome.altitude_freerange
        dome_conf.azimuthMaxspeed = config.observatory.dome.azimuth_maxspeed
        dome_conf.azimuthAccel = config.observatory.dome.azimuth_accel
        dome_conf.azimuthDecel = config.observatory.dome.azimuth_decel
        dome_conf.azimuthFreerange = config.observatory.dome.azimuth_freerange
        dome_conf.settleTime = config.observatory.dome.settle_time

    @staticmethod
    def rtopic_rotator_config(topic_rotator_config):

        confdict = {}
        confdict["rotator"] = {}
        confdict["rotator"]["minpos"] = topic_rotator_config.minpos
        confdict["rotator"]["maxpos"] = topic_rotator_config.maxpos
        confdict["rotator"]["maxspeed"] = topic_rotator_config.maxspeed
        confdict["rotator"]["accel"] = topic_rotator_config.accel
        confdict["rotator"]["decel"] = topic_rotator_config.decel
        confdict["rotator"]["filter_change_pos"] = topic_rotator_config.filterChangePos
        confdict["rotator"]["follow_sky"] = topic_rotator_config.followsky
        confdict["rotator"]["resume_angle"] = topic_rotator_config.resumeAngle

        return confdict

    @staticmethod
    def wtopic_rotator_config(rot_conf, config):

        rot_conf.minpos = config.observatory.rotator.minpos
        rot_conf.maxpos = config.observatory.rotator.maxpos
        rot_conf.filterChangePos = config.observatory.rotator.filter_change_pos
        rot_conf.maxspeed = config.observatory.rotator.maxspeed
        rot_conf.accel = config.observatory.rotator.accel
        rot_conf.decel = config.observatory.rotator.decel
        rot_conf.followsky = config.observatory.rotator.follow_sky
        rot_conf.resumeAngle = config.observatory.rotator.resume_angle

    @staticmethod
    def rtopic_optics_config(topic_optics_config):

        tel_optics_cl_alt_limit = []
        for k in range(3):
            tel_optics_cl_alt_limit.append(topic_optics_config.telOpticsClAltLimit[k])
        tel_optics_cl_delay = []
        for k in range(2):
            tel_optics_cl_delay.append(topic_optics_config.telOpticsClDelay[k])

        confdict = {}
        confdict["optics_loop_corr"] = {}
        confdict["optics_loop_corr"]["tel_optics_ol_slope"] = topic_optics_config.telOpticsOlSlope
        confdict["optics_loop_corr"]["tel_optics_cl_alt_limit"] = tel_optics_cl_alt_limit
        confdict["optics_loop_corr"]["tel_optics_cl_delay"] = tel_optics_cl_delay

        return confdict

    @staticmethod
    def wtopic_optics_config(olc_conf, config):

        olc_conf.telOpticsOlSlope = config.observatory.optics_loop_corr.tel_optics_ol_slope
        config.observatory.optics_loop_corr.set_array(olc_conf, "telOpticsClAltLimit")
        config.observatory.optics_loop_corr.set_array(olc_conf, "telOpticsClDelay")

    @staticmethod
    def rtopic_camera_config(topic_camera_config):

        confdict = {}
        confdict["camera"] = {}
        confdict["camera"]["readout_time"] = topic_camera_config.readoutTime
        confdict["camera"]["shutter_time"] = topic_camera_config.shutterTime
        confdict["camera"]["filter_change_time"] = topic_camera_config.filterChangeTime
        confdict["camera"]["filter_max_changes_burst_num"] = \
            topic_camera_config.filterMaxChangesBurstNum
        confdict["camera"]["filter_max_changes_burst_time"] = \
            topic_camera_config.filterMaxChangesBurstTime
        confdict["camera"]["filter_max_changes_avg_num"] = \
            topic_camera_config.filterMaxChangesAvgNum
        confdict["camera"]["filter_max_changes_avg_time"] = \
            topic_camera_config.filterMaxChangesAvgTime
        if topic_camera_config.filterRemovable != "":
            confdict["camera"]["filter_removable"] = topic_camera_config.filterRemovable.split(",")
        else:
            confdict["camera"]["filter_removable"] = []

        if topic_camera_config.filterMounted != "":
            confdict["camera"]["filter_mounted"] = topic_camera_config.filterMounted.split(",")
        else:
            confdict["camera"]["filter_mounted"] = []

        if topic_camera_config.filterUnmounted != "":
            confdict["camera"]["filter_unmounted"] = topic_camera_config.filterUnmounted.split(",")
        else:
            confdict["camera"]["filter_unmounted"] = []

        return confdict

    @staticmethod
    def wtopic_camera_config(cam_conf, config):

        cam_conf.readoutTime = config.observatory.camera.readout_time
        cam_conf.shutterTime = config.observatory.camera.shutter_time
        cam_conf.filterMountTime = config.observatory.camera.filter_mount_time
        cam_conf.filterChangeTime = config.observatory.camera.filter_change_time
        cam_conf.filterMaxChangesBurstNum = \
            config.observatory.camera.filter_max_changes_burst_num
        cam_conf.filterMaxChangesBurstTime = \
            config.observatory.camera.filter_max_changes_burst_time
        cam_conf.filterMaxChangesAvgNum = config.observatory.camera.filter_max_changes_avg_num
        cam_conf.filterMaxChangesAvgTime = config.observatory.camera.filter_max_changes_avg_time
        cam_conf.filterMounted = config.observatory.camera.filter_mounted_str
        cam_conf.filterPos = config.observatory.camera.filter_pos
        cam_conf.filterRemovable = config.observatory.camera.filter_removable_str
        cam_conf.filterUnmounted = config.observatory.camera.filter_unmounted_str

    @staticmethod
    def rtopic_slew_config(topic_slew_config):

        confdict = {}
        confdict["slew"] = {}

        prereq_str = topic_slew_config.prereqDomalt
        if prereq_str != "":
            confdict["slew"]["prereq_domalt"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domalt"] = []

        prereq_str = topic_slew_config.prereqDomaz
        if prereq_str != "":
            confdict["slew"]["prereq_domaz"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domaz"] = []

        prereq_str = topic_slew_config.prereqDomazSettle
        if prereq_str != "":
            confdict["slew"]["prereq_domazsettle"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_domazsettle"] = []

        prereq_str = topic_slew_config.prereqTelalt
        if prereq_str != "":
            confdict["slew"]["prereq_telalt"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telalt"] = []

        prereq_str = topic_slew_config.prereqTelaz
        if prereq_str != "":
            confdict["slew"]["prereq_telaz"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telaz"] = []

        prereq_str = topic_slew_config.prereqTelOpticsOpenLoop
        if prereq_str != "":
            confdict["slew"]["prereq_telopticsopenloop"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telopticsopenloop"] = []

        prereq_str = topic_slew_config.prereqTelOpticsClosedLoop
        if prereq_str != "":
            confdict["slew"]["prereq_telopticsclosedloop"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telopticsclosedloop"] = []

        prereq_str = topic_slew_config.prereqTelSettle
        if prereq_str != "":
            confdict["slew"]["prereq_telsettle"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telsettle"] = []

        prereq_str = topic_slew_config.prereqTelRot
        if prereq_str != "":
            confdict["slew"]["prereq_telrot"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_telrot"] = []

        prereq_str = topic_slew_config.prereqFilter
        if prereq_str != "":
            confdict["slew"]["prereq_filter"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_filter"] = []

        prereq_str = topic_slew_config.prereqExposures
        if prereq_str != "":
            confdict["slew"]["prereq_exposures"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_exposures"] = []

        prereq_str = topic_slew_config.prereqReadout
        if prereq_str != "":
            confdict["slew"]["prereq_readout"] = prereq_str.split(",")
        else:
            confdict["slew"]["prereq_readout"] = []

        return confdict

    @staticmethod
    def wtopic_slew_config(slew_conf, config):

        slew_conf.prereqDomalt = config.observatory.slew.get_string_rep("prereq_domalt")
        slew_conf.prereqDomaz = config.observatory.slew.get_string_rep("prereq_domaz")
        slew_conf.prereqTelalt = config.observatory.slew.get_string_rep("prereq_telalt")
        slew_conf.prereqTelaz = config.observatory.slew.get_string_rep("prereq_telaz")
        slew_conf.prereqTelOpticsOpenLoop = \
            config.observatory.slew.get_string_rep("prereq_telopticsopenloop")
        slew_conf.prereqTelOpticsClosedLoop = \
            config.observatory.slew.get_string_rep("prereq_telopticsclosedloop")
        slew_conf.prereqTelRot = config.observatory.slew.get_string_rep("prereq_telrot")
        slew_conf.prereqFilter = config.observatory.slew.get_string_rep("prereq_filter")
        slew_conf.prereqAdc = config.observatory.slew.get_string_rep("prereq_adc")
        slew_conf.prereqInsOptics = config.observatory.slew.get_string_rep("prereq_ins_optics")
        slew_conf.prereqGuiderPos = config.observatory.slew.get_string_rep("prereq_guider_pos")
        slew_conf.prereqGuiderAdq = config.observatory.slew.get_string_rep("prereq_guider_adq")
        slew_conf.prereqTelSettle = config.observatory.slew.get_string_rep("prereq_telsettle")
        slew_conf.prereqDomazSettle = config.observatory.slew.get_string_rep("prereq_domazsettle")
        slew_conf.prereqExposures = config.observatory.slew.get_string_rep("prereq_exposures")
        slew_conf.prereqReadout = config.observatory.slew.get_string_rep("prereq_readout")

    @staticmethod
    def rtopic_park_config(topic_park_config):

        confdict = {}
        confdict["park"] = {}
        confdict["park"]["telescope_altitude"] = topic_park_config.telescopeAltitude
        confdict["park"]["telescope_azimuth"] = topic_park_config.telescopeAzimuth
        confdict["park"]["telescope_rotator"] = topic_park_config.telescopeRotator
        confdict["park"]["dome_altitude"] = topic_park_config.domeAltitude
        confdict["park"]["dome_azimuth"] = topic_park_config.domeAzimuth
        confdict["park"]["filter_position"] = topic_park_config.filterPosition

        return confdict

    @staticmethod
    def wtopic_park_config(park_conf, config):

        park_conf.telescopeAltitude = config.observatory.park.telescope_altitude
        park_conf.telescopeAzimuth = config.observatory.park.telescope_azimuth
        park_conf.telescopeRotator = config.observatory.park.telescope_rotator
        park_conf.domeAltitude = config.observatory.park.dome_altitude
        park_conf.domeAzimuth = config.observatory.park.dome_azimuth
        park_conf.filterPosition = config.observatory.park.filter_position

    @staticmethod
    def rtopic_area_prop_config(topic_areapropconf):

        confdict = {}

        confdict["sky_nightly_bounds"] = {}
        confdict["sky_nightly_bounds"]["twilight_boundary"] = topic_areapropconf.twilightBoundary
        confdict["sky_nightly_bounds"]["delta_lst"] = topic_areapropconf.deltaLst

        confdict["constraints"] = {}
        confdict["constraints"]["max_airmass"] = topic_areapropconf.maxAirmass
        confdict["constraints"]["max_cloud"] = topic_areapropconf.maxCloud
        confdict["constraints"]["min_distance_moon"] = topic_areapropconf.minDistanceMoon
        confdict["constraints"]["exclude_planets"] = topic_areapropconf.excludePlanets

        confdict["sky_region"] = {}
        num_region_selections = topic_areapropconf.numRegionSelections
        region_types = topic_areapropconf.regionTypes
        if region_types == "":
            region_types_list = []
        else:
            region_types_list = region_types.split(",")

        region_list = []
        for k in range(num_region_selections):
            region_minimum = topic_areapropconf.regionMinimums[k]
            region_maximum = topic_areapropconf.regionMaximums[k]
            region_bound = topic_areapropconf.regionBounds[k]

            region = (region_types_list[k], region_minimum, region_maximum, region_bound)
            region_list.append(region)
        region_combiners = topic_areapropconf.regionCombiners
        if region_combiners == "":
            region_combiners_list = []
        else:
            region_combiners_list = region_combiners.split(",")
        confdict["sky_region"]["cuts"] = region_list
        confdict["sky_region"]["combiners"] = region_combiners_list

        num_time_ranges = topic_areapropconf.numTimeRanges
        if num_time_ranges:
            time_range_list = []
            selection_mappings = []
            selection_index = 0
            for k in range(num_time_ranges):
                time_range_list.append((topic_areapropconf.timeRangeStarts[k],
                                        topic_areapropconf.timeRangeEnds[k]))
                num_selection_mappings = topic_areapropconf.numSelectionMappings[k]
                selection_map = []
                for m in range(num_selection_mappings):
                    selection_map.append(topic_areapropconf.selectionMappings[selection_index])
                    selection_index += 1
                selection_mappings.append(selection_map)

            confdict["sky_region"]["time_ranges"] = time_range_list
            confdict["sky_region"]["selection_mappings"] = selection_mappings

        confdict["sky_exclusions"] = {}
        num_exclusion_selections = topic_areapropconf.numExclusionSelections
        exclusion_types = topic_areapropconf.exclusionTypes
        if exclusion_types == "":
            exclusion_types_list = []
        else:
            exclusion_types_list = exclusion_types.split(",")
        exclusion_list = []
        for k in range(num_exclusion_selections):
            exclusion_minimum = topic_areapropconf.exclusionMinimums[k]
            exclusion_maximum = topic_areapropconf.exclusionMaximums[k]
            exclusion_bound = topic_areapropconf.exclusionBounds[k]

            exclusion = (exclusion_types_list[k], exclusion_minimum,
                         exclusion_maximum, exclusion_bound)
            exclusion_list.append(exclusion)

        confdict["sky_exclusions"]["cuts"] = exclusion_list
        dec_window = topic_areapropconf.decWindow
        confdict["sky_exclusions"]["dec_window"] = dec_window

        num_filters = topic_areapropconf.numFilters
        filter_names = topic_areapropconf.filterNames
        filter_list = filter_names.split(",")
        exp_index = 0
        for k in range(num_filters):
            filter = filter_list[k]
            filter_section = "filter_%s" % filter
            confdict[filter_section] = {}
            confdict[filter_section]["visits"] = topic_areapropconf.numVisits[k]
            confdict[filter_section]["min_brig"] = \
                topic_areapropconf.brightLimit[k]
            confdict[filter_section]["max_brig"] = topic_areapropconf.darkLimit[k]
            confdict[filter_section]["max_seeing"] = topic_areapropconf.maxSeeing[k]
            num_exp = topic_areapropconf.numFilterExposures[k]
            exp_times_list = []
            for n in range(num_exp):
                exp_times_list.append(topic_areapropconf.exposures[exp_index])
                exp_index += 1
            confdict[filter_section]["exp_times"] = exp_times_list
            confdict[filter_section]["num_grouped_visits"] = topic_areapropconf.numGroupedVisits[k]
            confdict[filter_section]["max_grouped_visits"] = topic_areapropconf.maxGroupedVisits[k]

        confdict["scheduling"] = {}
        max_num_targets = topic_areapropconf.maxNumTargets
        accept_serendipity = topic_areapropconf.acceptSerendipity
        accept_consecutive_visits = topic_areapropconf.acceptConsecutiveVisits
        confdict["scheduling"]["max_num_targets"] = max_num_targets
        confdict["scheduling"]["accept_serendipity"] = accept_serendipity
        confdict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits
        confdict["scheduling"]["airmass_bonus"] = topic_areapropconf.airmassBonus
        confdict["scheduling"]["hour_angle_bonus"] = topic_areapropconf.hourAngleBonus
        confdict["scheduling"]["hour_angle_max"] = topic_areapropconf.hourAngleMax
        confdict["scheduling"]["field_revisit_limit"] = 2 #hardcoded for now

        confdict["scheduling"]["restrict_grouped_visits"] = topic_areapropconf.restrictGroupedVisits
        confdict["scheduling"]["time_interval"] = topic_areapropconf.timeInterval
        confdict["scheduling"]["time_window_start"] = topic_areapropconf.timeWindowStart
        confdict["scheduling"]["time_window_max"] = topic_areapropconf.timeWindowMax
        confdict["scheduling"]["time_window_end"] = topic_areapropconf.timeWindowEnd
        confdict["scheduling"]["time_weight"] = topic_areapropconf.timeWeight
        confdict["scheduling"]["field_revisit_limit"] = topic_areapropconf.fieldRevisitLimit

        return confdict

    @staticmethod
    def rtopic_seq_prop_config(topic_seqpropconf):

        confdict = {}

        confdict["sky_nightly_bounds"] = {}
        confdict["sky_nightly_bounds"]["twilight_boundary"] = topic_seqpropconf.twilightBoundary
        confdict["sky_nightly_bounds"]["delta_lst"] = topic_seqpropconf.deltaLst

        confdict["constraints"] = {}
        confdict["constraints"]["max_airmass"] = topic_seqpropconf.maxAirmass
        confdict["constraints"]["max_cloud"] = topic_seqpropconf.maxCloud
        confdict["constraints"]["min_distance_moon"] = topic_seqpropconf.minDistanceMoon
        confdict["constraints"]["exclude_planets"] = topic_seqpropconf.excludePlanets

        confdict["sky_region"] = {}
        num_user_regions = topic_seqpropconf.numUserRegions
        region_list = []
        for k in range(num_user_regions):
            region_list.append(topic_seqpropconf.userRegionIds[k])

        confdict["sky_region"]["user_regions"] = region_list

        confdict["sky_exclusions"] = {}
        confdict["sky_exclusions"]["dec_window"] = topic_seqpropconf.decWindow

        num_sub_sequences = topic_seqpropconf.numSubSequences
        if num_sub_sequences:
            confdict["subsequences"] = {}
            sub_sequence_names = topic_seqpropconf.subSequenceNames.split(',')
            confdict["subsequences"]["names"] = sub_sequence_names
            sub_sequence_filters = topic_seqpropconf.subSequenceFilters.split(',')
            sub_sequence_visits_per_filter = topic_seqpropconf.numSubSequenceFilterVisits
            index = 0
            for k, sname in enumerate(sub_sequence_names):
                sub_seq_section = "subseq_{}".format(sname)
                confdict[sub_seq_section] = {}
                num_sub_sequence_filters = topic_seqpropconf.numSubSequenceFilters[k]
                confdict[sub_seq_section]["filters"] = \
                    sub_sequence_filters[index:index + num_sub_sequence_filters]
                confdict[sub_seq_section]["visits_per_filter"] = \
                    sub_sequence_visits_per_filter[index:index + num_sub_sequence_filters]
                index += num_sub_sequence_filters
                confdict[sub_seq_section]["num_events"] = topic_seqpropconf.numSubSequenceEvents[k]
                confdict[sub_seq_section]["num_max_missed"] = topic_seqpropconf.numSubSequenceMaxMissed[k]
                confdict[sub_seq_section]["time_interval"] = topic_seqpropconf.subSequenceTimeIntervals[k]
                confdict[sub_seq_section]["time_window_start"] = \
                    topic_seqpropconf.subSequenceTimeWindowStarts[k]
                confdict[sub_seq_section]["time_window_max"] = \
                    topic_seqpropconf.subSequenceTimeWindowMaximums[k]
                confdict[sub_seq_section]["time_window_end"] = \
                    topic_seqpropconf.subSequenceTimeWindowEnds[k]
                confdict[sub_seq_section]["time_weight"] = topic_seqpropconf.subSequenceTimeWeights[k]

        num_master_sub_sequences = topic_seqpropconf.numMasterSubSequences
        if num_master_sub_sequences:
            confdict["master_subsequences"] = {}
            master_sub_sequence_names = topic_seqpropconf.masterSubSequenceNames.split(',')

            confdict["master_subsequences"]["names"] = master_sub_sequence_names
            confdict["master_subsequences"]["num_nested"] = \
                topic_seqpropconf.num_nested_sub_sequences[:num_master_sub_sequences]
            nested_sub_sequence_names = topic_seqpropconf.nested_sub_sequence_names.split(',')
            nested_sub_sequence_filters = topic_seqpropconf.nested_sub_sequence_filters.split(',')
            index = 0
            findex = 0
            for k, mname in enumerate(master_sub_sequence_names):
                msub_seq_section = "msubseq_{}".format(mname)
                confdict[msub_seq_section] = {}
                num_nested_sub_sequences = topic_seqpropconf.num_nested_sub_sequences[k]
                confdict[msub_seq_section]["nested_names"] = \
                    nested_sub_sequence_names[index:index + num_nested_sub_sequences]
                confdict[msub_seq_section]["num_events"] = topic_seqpropconf.num_master_sub_sequence_events[k]
                confdict[msub_seq_section]["num_max_missed"] = \
                    topic_seqpropconf.num_master_sub_sequence_max_missed[k]
                confdict[msub_seq_section]["time_interval"] = \
                    topic_seqpropconf.master_sub_sequence_time_intervals[k]
                confdict[msub_seq_section]["time_window_start"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_starts[k]
                confdict[msub_seq_section]["time_window_max"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_maximums[k]
                confdict[msub_seq_section]["time_window_end"] = \
                    topic_seqpropconf.master_sub_sequence_time_window_ends[k]
                confdict[msub_seq_section]["time_weight"] = \
                    topic_seqpropconf.master_sub_sequence_time_weights[k]

                for l, nname in enumerate(confdict[msub_seq_section]["nested_names"]):
                    nindex = index + l
                    nsub_seq_section = "nsubseq_{}".format(nname)
                    confdict[nsub_seq_section] = {}
                    num_nested_sub_sequence_filters = \
                        topic_seqpropconf.num_nested_sub_sequence_filters[nindex]
                    last_index = findex + num_nested_sub_sequence_filters
                    confdict[nsub_seq_section]["filters"] = nested_sub_sequence_filters[findex:last_index]
                    confdict[nsub_seq_section]["visits_per_filter"] = \
                        topic_seqpropconf.num_nested_sub_sequence_filter_visits[findex:last_index]
                    findex += num_nested_sub_sequence_filters
                    confdict[nsub_seq_section]["num_events"] = \
                        topic_seqpropconf.num_nested_sub_sequence_events[nindex]
                    confdict[nsub_seq_section]["num_max_missed"] = \
                        topic_seqpropconf.num_nested_sub_sequence_max_missed[nindex]
                    confdict[nsub_seq_section]["time_interval"] = \
                        topic_seqpropconf.nested_sub_sequence_time_intervals[nindex]
                    confdict[nsub_seq_section]["time_window_start"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_starts[nindex]
                    confdict[nsub_seq_section]["time_window_max"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_maximums[nindex]
                    confdict[nsub_seq_section]["time_window_end"] = \
                        topic_seqpropconf.nested_sub_sequence_time_window_ends[nindex]
                    confdict[nsub_seq_section]["time_weight"] = \
                        topic_seqpropconf.nested_sub_sequence_time_weights[nindex]

                index += num_nested_sub_sequences

        num_filters = topic_seqpropconf.numFilters
        filter_names = topic_seqpropconf.filterNames
        filter_list = filter_names.split(",")
        exp_index = 0
        for k in range(num_filters):
            filter_section = "filter_%s" % filter_list[k]
            confdict[filter_section] = {}
            confdict[filter_section]["min_brig"] = \
                topic_seqpropconf.brightLimit[k]
            confdict[filter_section]["max_brig"] = topic_seqpropconf.darkLimit[k]
            confdict[filter_section]["max_seeing"] = topic_seqpropconf.maxSeeing[k]
            num_exp = topic_seqpropconf.numFilterExposures[k]
            exp_times_list = []
            for n in range(num_exp):
                exp_times_list.append(topic_seqpropconf.exposures[exp_index])
                exp_index += 1
            confdict[filter_section]["exp_times"] = exp_times_list

        confdict["scheduling"] = {}
        max_num_targets = topic_seqpropconf.maxNumTargets
        accept_serendipity = topic_seqpropconf.acceptSerendipity
        accept_consecutive_visits = topic_seqpropconf.acceptConsecutiveVisits
        confdict["scheduling"]["max_num_targets"] = max_num_targets
        confdict["scheduling"]["accept_serendipity"] = accept_serendipity
        confdict["scheduling"]["accept_consecutive_visits"] = accept_consecutive_visits
        confdict["scheduling"]["restart_lost_sequences"] = topic_seqpropconf.restartLostSequences
        confdict["scheduling"]["restart_complete_sequences"] = topic_seqpropconf.restartCompleteSequences
        confdict["scheduling"]["max_visits_goal"] = topic_seqpropconf.maxVisitsGoal
        confdict["scheduling"]["airmass_bonus"] = topic_seqpropconf.airmassBonus
        confdict["scheduling"]["hour_angle_bonus"] = topic_seqpropconf.hourAngleBonus
        confdict["scheduling"]["hour_angle_max"] = topic_seqpropconf.hourAngleMax

        return confdict

    @staticmethod
    def wtopic_target(topic_target, target, sky):

        topic_target.targetId = target.targetid
        # topic_target.groupId = target.groupid
        # topic_target.fieldId = target.fieldid
        topic_target.filter = target.filter
        topic_target.requestTime = target.time
        topic_target.ra = target.ra
        topic_target.decl = target.dec
        topic_target.skyAngle = target.ang
        topic_target.numExposures = target.num_exp
        for i, exptime in enumerate(target.exp_times):
            topic_target.exposureTimes[i] = int(exptime)
        topic_target.airmass = target.airmass
        topic_target.skyBrightness = target.sky_brightness
        topic_target.cloud = target.cloud
        topic_target.seeing = target.seeing
        topic_target.slewTime = target.slewtime
        # topic_target.cost = target.cost
        # topic_target.rank = target.rank
        topic_target.numProposals = target.num_props
        for i, prop_id in enumerate(target.propid_list):
            topic_target.proposalId[i] = prop_id
        # for i, prop_value in enumerate(target.value_list):
        #     topic_target.proposal_values[i] = prop_value
        # for i, prop_need in enumerate(target.need_list):
        #     topic_target.proposal_needs[i] = prop_need
        # for i, prop_bonus in enumerate(target.bonus_list):
        #     topic_target.proposal_bonuses[i] = prop_bonus

        moon_sun = sky.get_moon_sun_info(numpy.array([target.ra_rad]), numpy.array([target.dec_rad]))
        if moon_sun["moonRA"] is not None:
            topic_target.moonRa = math.degrees(moon_sun["moonRA"])
            topic_target.moonDec = math.degrees(moon_sun["moonDec"])
            topic_target.moonAlt = math.degrees(moon_sun["moonAlt"])
            topic_target.moonAz = math.degrees(moon_sun["moonAz"])
            topic_target.moonPhase = moon_sun["moonPhase"]
            topic_target.moonDistance = math.degrees(moon_sun["moonDist"])
            topic_target.sunAlt = math.degrees(moon_sun["sunAlt"])
            topic_target.sunAz = math.degrees(moon_sun["sunAz"])
            topic_target.sunRa = math.degrees(moon_sun["sunRA"])
            topic_target.sunDec = math.degrees(moon_sun["sunDec"])
            topic_target.solarElong = math.degrees(moon_sun["solarElong"])

        topic_target.note = target.note

    @staticmethod
    def wtopic_scheduler_topology_config(topic, config):
        topic.numGeneralProps = len(config.science.general_proposals)

        general_props = ''
        for i, gen_prop in enumerate(config.science.general_proposals):
            general_props += gen_prop
            if i < topic.num_general_props-1:
                general_props += ','

        topic.generalPropos = general_props

        topic.numSeqProps = len(config.science.sequence_proposals)

        sequence_props = ''
        for i, seq_prop in enumerate(config.science.sequence_proposals):
            sequence_props += seq_prop
            if i < topic.num_seq_props-1:
                sequence_props += ','

        topic.sequencePropos = sequence_props

    @staticmethod
    def rtopic_observation(topic_observation):

        observation = Observation()

        observation.time = topic_observation.observationStartTime
        observation.observation_start_mjd = topic_observation.observationStartMjd
        observation.targetid = topic_observation.targetId
        observation.filter = topic_observation.filter
        observation.num_props = topic_observation.numProposals
        observation.propid_list = []
        for k in range(observation.num_props):
            observation.propid_list.append(topic_observation.proposalIds[k])
        observation.ra_rad = math.radians(topic_observation.ra)
        observation.dec_rad = math.radians(topic_observation.decl)
        observation.ang_rad = math.radians(topic_observation.angle)
        observation.num_exp = topic_observation.numExposures
        observation.exp_times = []
        for k in range(topic_observation.numExposures):
            observation.exp_times.append(topic_observation.exposureTimes[k])

        observation.airmass = topic_observation.airmass
        observation.seeing_fwhm_eff = topic_observation.seeing_fwhm_eff
        observation.seeing_fwhm_geom = topic_observation.seeing_fwhm_geom
        observation.sky_brightness = topic_observation.sky_brightness
        observation.night = topic_observation.night
        observation.five_sigma_depth = topic_observation.five_sigma_depth
        observation.alt_rad = topic_observation.altitude
        observation.az_rad = topic_observation.azimuth
        observation.cloud = topic_observation.cloud
        observation.moon_alt = topic_observation.moon_alt
        observation.sun_alt = topic_observation.sun_alt
        observation.slewtime = topic_observation.slew_time
        observation.note = topic_observation.note

        return observation

    @staticmethod
    def rtopic_observatory_state(topic_state):

        state = ObservatoryState()

        state.time = topic_state.timestamp
        state.ra_rad = math.radians(topic_state.pointingRa)
        state.dec_rad = math.radians(topic_state.pointingDec)
        state.ang_rad = math.radians(topic_state.pointingAngle)
        state.filter = topic_state.filterPosition
        state.tracking = topic_state.tracking
        state.alt_rad = math.radians(topic_state.pointingAltitude)
        state.az_rad = math.radians(topic_state.pointingAzimuth)
        state.pa_rad = math.radians(topic_state.pointingPa)
        state.rot_rad = math.radians(topic_state.pointingRot)
        state.telalt_rad = math.radians(topic_state.telescopeAltitude)
        state.telaz_rad = math.radians(topic_state.telescopeAzimuth)
        state.telrot_rad = math.radians(topic_state.telescopeRotator)
        state.domalt_rad = math.radians(topic_state.domeAltitude)
        state.domaz_rad = math.radians(topic_state.domeAzimuth)
        state.mountedfilters = topic_state.filterMounted.split(",")
        state.unmountedfilters = topic_state.filterUnmounted.split(",")

        return state

    @staticmethod
    def wtopic_interestedProposal(topic, targetId, target_list):

        topic.observationId = targetId
        topic.numProposals = len(target_list)
        propid_list = []
        need_list = []
        bonus_list = []
        value_list = []
        propboost_list = []
        for k in range(topic.numProposals):
            topic.proposalIds[k] = target_list[k].propid
            topic.proposalNeeds[k] = target_list[k].need
            topic.proposalBonuses[k] = target_list[k].bonus
            topic.proposalValues[k] = target_list[k].value
            topic.proposalBoosts[k] = target_list[k].propboost
            propid_list.append(target_list[k].propid)
            need_list.append(target_list[k].need)
            bonus_list.append(target_list[k].bonus)
            value_list.append(target_list[k].value)
            propboost_list.append(target_list[k].propboost)
        logstr = ("obsId=%i numprops=%i propid=%s need=%s bonus=%s value=%s propboost=%s" %
                  (targetId, topic.numProposals,
                   propid_list, need_list, bonus_list, value_list, propboost_list))
        return logstr
