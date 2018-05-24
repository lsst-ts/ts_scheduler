from builtins import object
from builtins import range
from builtins import str
import os
import math
import numpy
import logging
from operator import itemgetter

from lsst.ts.dateloc import DateProfile
from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.setup import EXTENSIVE, WORDY
from lsst.ts.scheduler.kernel import read_conf_file
from lsst.ts.scheduler.kernel import Field, SurveyTopology, Telemetry
from lsst.ts.scheduler.proposals import ScriptedProposal
from lsst.ts.scheduler.proposals import AreaDistributionProposal, TimeDistributionProposal
from lsst.ts.scheduler.fields import FieldsDatabase
from lsst.ts.scheduler.lookahead import Lookahead

__all__ = ["Driver"]


class DriverParameters(object):

    def __init__(self):
        self.coadd_values = False
        self.timecost_weight = 0.0
        self.timecost_dc = 0.0
        self.timecost_dt = 0.0
        self.timecost_k = 0.0
        self.night_boundary = 0.0
        self.ignore_sky_brightness = False
        self.ignore_airmass = False
        self.ignore_clouds = False
        self.ignore_seeing = False
        self.new_moon_phase_threshold = 0.0

    def configure(self, confdict):
        self.coadd_values = confdict["ranking"]["coadd_values"]
        self.time_balancing = confdict["ranking"]["time_balancing"]

        tmax = confdict["ranking"]["timecost_time_max"]
        tref = confdict["ranking"]["timecost_time_ref"]
        cref = float(confdict["ranking"]["timecost_cost_ref"])

        self.timecost_tmax = tmax
        self.timecost_tref = tref
        self.timecost_cref = cref

        self.timecost_dc = cref * (tmax - tref) / (tref - cref * tmax)
        self.timecost_dt = -tmax * (self.timecost_dc + 1.0)
        self.timecost_k = self.timecost_dc * self.timecost_dt
        self.timecost_weight = confdict["ranking"]["timecost_weight"]
        self.filtercost_weight = confdict["ranking"]["filtercost_weight"]
        self.propboost_weight = confdict["ranking"]["propboost_weight"]
        self.lookahead_window_size = confdict['ranking']['lookahead_window_size']
        self.lookahead_bonus_weight = confdict["ranking"]["lookahead_bonus_weight"]

        self.night_boundary = confdict["constraints"]["night_boundary"]
        self.ignore_sky_brightness = confdict["constraints"]["ignore_sky_brightness"]
        self.ignore_airmass = confdict["constraints"]["ignore_airmass"]
        self.ignore_clouds = confdict["constraints"]["ignore_clouds"]
        self.ignore_seeing = confdict["constraints"]["ignore_seeing"]
        self.new_moon_phase_threshold = confdict["darktime"]["new_moon_phase_threshold"]


class Driver(object):
    def __init__(self, models=None, telemetry_stream=None):

        self.log = logging.getLogger("schedulerDriver")

        self.params = DriverParameters()
        self.models = dict()
        if models is None:
            # Configuring basic models
            self.models['location'] = ObservatoryLocation()
            self.models['dateprofile'] = DateProfile(0, self.models['location'])
            self.models['observatoryState'] = ObservatoryState()
            # Only the main model carries the observatory state. Secondary model is detached.
            self.models['observatoryModel'] = ObservatoryModel(location=self.models['location'],
                                                               dateprofile=self.models['dateprofile'],
                                                               state=self.models['observatoryState'],
                                                               log_level=WORDY)
            self.models['observatoryModel2'] = ObservatoryModel(location=self.models['location'], log_level=WORDY)
            self.models['sky'] = AstronomicalSkyModel(self.models['dateprofile'])
        else:
            self.models = models

        if telemetry_stream is None:
            self.telemetry_stream = dict()
            from SALPY_scheduler import scheduler_timeHandlerC
            from SALPY_scheduler import scheduler_observatoryStateC
            from SALPY_scheduler import scheduler_cloudC
            from SALPY_scheduler import scheduler_seeingC

            self.telemetry_stream['time'] = {'telemetry': Telemetry(scheduler_timeHandlerC),
                                             'callback': [self.models['observatoryModel'].update_time]}
            self.telemetry_stream['seeing'] = {'telemetry': Telemetry(scheduler_seeingC),
                                               'callback': []}
            self.telemetry_stream['cloud'] = {'telemetry': Telemetry(scheduler_cloudC),
                                              'callback': []}
            self.telemetry_stream['observatoryState'] = {'telemetry': Telemetry(scheduler_observatoryStateC),
                                                         'callback': [self.update_internal_conditions]}

        else:
            self.telemetry_stream = telemetry_stream
        # self.location = ObservatoryLocation()
        #
        # self.observatoryModel = ObservatoryModel(self.location, WORDY)
        # self.observatoryModel2 = ObservatoryModel(self.location, WORDY)
        # self.observatoryState = ObservatoryState()
        #
        # self.sky = AstronomicalSkyModel(self.location)

        # self.db = FieldsDatabase()
        #
        # self.build_fields_dict()

        self.survey_topology = SurveyTopology()
        # self.propid_counter = 0
        # self.science_proposal_list = []

        self.start_time = 0.0
        self.time = 0.0
        self.targetid = 0
        self.survey_started = False
        self.isnight = False
        self.sunset_timestamp = 0.0
        self.sunrise_timestamp = 0.0
        self.survey_duration_DAYS = 0.0
        self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0
        self.darktime = False
        self.mounted_filter = ""
        self.unmounted_filter = ""
        self.midnight_moonphase = 0.0

        self.nulltarget = Target()
        self.nulltarget.targetid = -1
        self.nulltarget.num_exp = 1
        self.nulltarget.exp_times = [0.0]
        self.nulltarget.num_props = 1
        self.nulltarget.propid_list = [0]
        self.nulltarget.need_list = [0.0]
        self.nulltarget.bonus_list = [0.0]
        self.nulltarget.value_list = [0.0]
        self.nulltarget.propboost_list = [1.0]

        self.last_winner_target = self.nulltarget.get_copy()

        self.need_filter_swap = False
        self.filter_to_unmount = ""
        self.filter_to_mount = ""


        # self.cloud = 0.0
        # self.seeing = 0.0

        # self.lookahead = Lookahead()

    # def configure_survey(self, survey_conf_file):
    #
    #     prop_conf_path = os.path.dirname(survey_conf_file)
    #     confdict = read_conf_file(survey_conf_file)
    #
    #     self.survey_duration_DAYS = confdict["survey"]["survey_duration"]
    #     self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0
    #
    #     self.propid_counter = 0
    #     self.science_proposal_list = []
    #
    #     if 'scripted_propconf' in confdict["proposals"]:
    #         scripted_propconflist = confdict["proposals"]["scripted_propconf"]
    #     else:
    #         scripted_propconflist = []
    #     if not isinstance(scripted_propconflist, list):
    #         # turn it into a list with one entry
    #         propconf = scripted_propconflist
    #         scripted_propconflist = []
    #         scripted_propconflist.append(propconf)
    #     self.log.info("configure_survey: scripted proposals %s" % (scripted_propconflist))
    #     for k in range(len(scripted_propconflist)):
    #         self.propid_counter += 1
    #         scripted_prop = ScriptedProposal(self.propid_counter,
    #                                          os.path.join(prop_conf_path,
    #                                                       "{}".format(scripted_propconflist[k])),
    #                                          self.sky)
    #         self.science_proposal_list.append(scripted_prop)
    #
    #     if 'areadistribution_propconf' in confdict["proposals"]:
    #         areadistribution_propconflist = confdict["proposals"]["areadistribution_propconf"]
    #     else:
    #         areadistribution_propconflist = []
    #         self.log.info("areadistributionPropConf:%s default" % (areadistribution_propconflist))
    #     if not isinstance(areadistribution_propconflist, list):
    #         # turn it into a list with one entry
    #         propconf = areadistribution_propconflist
    #         areadistribution_propconflist = []
    #         areadistribution_propconflist.append(propconf)
    #     self.log.info("init: areadistribution proposals %s" % (areadistribution_propconflist))
    #     for k in range(len(areadistribution_propconflist)):
    #         self.propid_counter += 1
    #         configfilepath = os.path.join(prop_conf_path, "{}".format(areadistribution_propconflist[k]))
    #         (path, name_ext) = os.path.split(configfilepath)
    #         (name, ext) = os.path.splitext(name_ext)
    #         proposal_confdict = read_conf_file(configfilepath)
    #         self.create_area_proposal(self.propid_counter, name, proposal_confdict)
    #
    #     for prop in self.science_proposal_list:
    #         prop.configure_constraints(self.params)

    def configure_duration(self, survey_duration):

        self.survey_duration_DAYS = survey_duration
        self.survey_duration_SECS = survey_duration * 24 * 60 * 60.0

    def configure(self, confdict):

        self.params.configure(confdict)
        self.log.log(WORDY,
                     "configure: coadd_values=%s" % (self.params.coadd_values))
        self.log.log(WORDY,
                     "configure: time_balancing=%s" % (self.params.time_balancing))
        self.log.log(WORDY,
                     "configure: timecost_dc=%.3f" % (self.params.timecost_dc))
        self.log.log(WORDY,
                     "configure: timecost_dt=%.3f" % (self.params.timecost_dt))
        self.log.log(WORDY,
                     "configure: timecost_k=%.3f" % (self.params.timecost_k))
        self.log.log(WORDY,
                     "configure: timecost_weight=%.3f" % (self.params.timecost_weight))
        self.log.log(WORDY,
                     "configure: night_boundary=%.1f" % (self.params.night_boundary))
        self.log.log(WORDY,
                     "configure: ignore_sky_brightness=%s" % (self.params.ignore_sky_brightness))
        self.log.log(WORDY,
                     "configure: ignore_airmass=%s" % (self.params.ignore_airmass))
        self.log.log(WORDY,
                     "configure: ignore_clouds=%s" % (self.params.ignore_clouds))
        self.log.log(WORDY,
                     "configure: ignore_seeing=%s" % (self.params.ignore_seeing))
        self.log.log(WORDY,
                     "configure: new_moon_phase_threshold=%.2f" % (self.params.new_moon_phase_threshold))

        for prop in self.science_proposal_list:
            prop.configure_constraints(self.params)

        self.lookahead.window_size = self.params.lookahead_window_size
        self.lookahead.bonus_weight = self.params.lookahead_bonus_weight

    def configure_location(self, confdict):

        self.models['location'].configure(confdict)
        self.models['observatoryModel'].location.configure(confdict)
        self.models['observatoryModel2'].location.configure(confdict)
        self.models['sky'].update_location(self.location)

    def configure_observatory(self, confdict):

        self.models['observatoryModel'].configure(confdict)
        self.models['observatoryModel2'].configure(confdict)

    def configure_telescope(self, confdict):

        self.models['observatoryModel'].configure_telescope(confdict)
        self.models['observatoryModel2'].configure_telescope(confdict)

    def configure_rotator(self, confdict):

        self.models['observatoryModel'].configure_rotator(confdict)
        self.models['observatoryModel2'].configure_rotator(confdict)

    def configure_dome(self, confdict):

        self.models['observatoryModel'].configure_dome(confdict)
        self.models['observatoryModel2'].configure_dome(confdict)

    def configure_optics(self, confdict):

        self.models['observatoryModel'].configure_optics(confdict)
        self.models['observatoryModel2'].configure_optics(confdict)

    def configure_camera(self, confdict):

        self.models['observatoryModel'].configure_camera(confdict)
        self.models['observatoryModel2'].configure_camera(confdict)

    def configure_slew(self, confdict):

        self.models['observatoryModel'].configure_slew(confdict)
        self.models['observatoryModel2'].configure_slew(confdict)

    def configure_park(self, confdict):

        self.models['observatoryModel'].configure_park(confdict)
        self.models['observatoryModel2'].configure_park(confdict)

    # def create_area_proposal(self, propid, name, config_dict):
    #
    #     self.propid_counter += 1
    #     area_prop = AreaDistributionProposal(propid, name, config_dict, self.sky)
    #     area_prop.configure_constraints(self.params)
    #     self.science_proposal_list.append(area_prop)
    #
    # def create_sequence_proposal(self, propid, name, config_dict):
    #
    #     self.propid_counter += 1
    #     seq_prop = TimeDistributionProposal(propid, name, config_dict, self.sky)
    #     seq_prop.configure_constraints(self.params)
    #     self.science_proposal_list.append(seq_prop)

    # def build_fields_dict(self):
    #
    #     sql = "select * from Field"
    #     res = self.db.query(sql)
    #
    #     self.fields_dict = {}
    #     for row in res:
    #         field = Field()
    #         fieldid = row[0]
    #         field.fieldid = fieldid
    #         field.fov_rad = math.radians(row[1])
    #         field.ra_rad = math.radians(row[2])
    #         field.dec_rad = math.radians(row[3])
    #         field.gl_rad = math.radians(row[4])
    #         field.gb_rad = math.radians(row[5])
    #         field.el_rad = math.radians(row[6])
    #         field.eb_rad = math.radians(row[7])
    #         self.fields_dict[fieldid] = field
    #         self.log.log(EXTENSIVE, "buildFieldsTable: %s" % (self.fields_dict[fieldid]))
    #     self.log.info("buildFieldsTable: %d fields" % (len(self.fields_dict)))

    # def get_fields_dict(self):
    #
    #     return self.fields_dict

    def start_survey(self, timestamp, night):

        self.start_time = timestamp

        self.log.info("start_survey t=%.6f" % timestamp)

        self.survey_started = True
        # for prop in self.science_proposal_list:
        #     prop.start_survey()

        self.models['sky'].update(timestamp)
        (sunset, sunrise) = self.models['sky'].get_night_boundaries(self.params.night_boundary)
        self.log.debug("start_survey sunset=%.6f sunrise=%.6f" % (sunset, sunrise))
        # if round(sunset) <= round(timestamp) < round(sunrise):
        if sunset <= timestamp < sunrise:
            self.start_night(timestamp, night)

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def end_survey(self):

        self.log.info("end_survey")

        # for prop in self.science_proposal_list:
        #     prop.end_survey()

    def start_night(self, timestamp, night):

        timeprogress = (timestamp - self.start_time) / self.survey_duration_SECS
        self.log.info("start_night t=%.6f, night=%d timeprogress=%.2f%%" %
                      (timestamp, night, 100 * timeprogress))

        self.isnight = True

        # for prop in self.science_proposal_list:
        #     prop.start_night(timestamp, self.models['observatoryModel'].current_state.mountedfilters, night)

    def end_night(self, timestamp, night):

        # self.lookahead.end_night()

        timeprogress = (timestamp - self.start_time) / self.survey_duration_SECS
        self.log.info("end_night t=%.6f, night=%d timeprogress=%.2f%%" %
                      (timestamp, night, 100 * timeprogress))

        self.isnight = False

        self.last_winner_target = self.nulltarget
        # self.deep_drilling_target = None

        # total_filter_visits_dict = {}
        # total_filter_goal_dict = {}
        # total_filter_progress_dict = {}
        # for prop in self.science_proposal_list:
        #     prop.end_night(timestamp)
        #     filter_visits_dict = {}
        #     filter_goal_dict = {}
        #     filter_progress_dict = {}
        #     for filter in self.observatoryModel.filters:
        #         if filter not in total_filter_visits_dict:
        #             total_filter_visits_dict[filter] = 0
        #             total_filter_goal_dict[filter] = 0
        #         filter_visits_dict[filter] = prop.get_filter_visits(filter)
        #         filter_goal_dict[filter] = prop.get_filter_goal(filter)
        #         filter_progress_dict[filter] = prop.get_filter_progress(filter)
        #         total_filter_visits_dict[filter] += filter_visits_dict[filter]
        #         total_filter_goal_dict[filter] += filter_goal_dict[filter]
        #         self.log.debug("end_night propid=%d name=%s filter=%s progress=%.2f%%" %
        #                        (prop.propid, prop.name, filter, 100 * filter_progress_dict[filter]))
        # for filter in self.observatoryModel.filters:
        #     if total_filter_goal_dict[filter] > 0:
        #         total_filter_progress_dict[filter] = \
        #             float(total_filter_visits_dict[filter]) / total_filter_goal_dict[filter]
        #     else:
        #         total_filter_progress_dict[filter] = 0.0
        #     self.log.info("end_night filter=%s progress=%.2f%%" %
        #                   (filter, 100 * total_filter_progress_dict[filter]))

        previous_midnight_moonphase = self.midnight_moonphase
        self.models['sky'].update(timestamp)
        (sunset, sunrise) = self.models['sky'].get_night_boundaries(self.params.night_boundary)
        self.log.debug("end_night sunset=%.6f sunrise=%.6f" % (sunset, sunrise))

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise
        next_midnight = (sunset + sunrise) / 2
        self.models['sky'].update(next_midnight)
        info = self.models['sky'].get_moon_sun_info(numpy.array([0.0]), numpy.array([0.0]))
        self.midnight_moonphase = info["moonPhase"]
        self.log.info("end_night next moonphase=%.2f%%" % (self.midnight_moonphase))

        self.need_filter_swap = False
        self.filter_to_mount = ""
        self.filter_to_unmount = ""
        if self.darktime:
            if self.midnight_moonphase > previous_midnight_moonphase:
                self.log.info("end_night dark time waxing")
                if self.midnight_moonphase > self.params.new_moon_phase_threshold:
                    self.need_filter_swap = True
                    self.filter_to_mount = self.unmounted_filter
                    self.filter_to_unmount = self.mounted_filter
                    self.darktime = False
            else:
                self.log.info("end_night dark time waning")
        else:
            if self.midnight_moonphase < previous_midnight_moonphase:
                self.log.info("end_night bright time waning")
                if self.midnight_moonphase < self.params.new_moon_phase_threshold:
                    self.need_filter_swap = True
                    self.filter_to_mount = self.models['observatoryModel'].params.filter_darktime
                    self.filter_to_unmount = self.get_filter_to_unmount()
                    self.darktime = True
            else:
                self.log.info("end_night bright time waxing")

        if self.need_filter_swap:
            self.log.debug("end_night filter swap %s=>cam=>%s" %
                           (self.filter_to_mount, self.filter_to_unmount))

    def swap_filter(self, filter_to_unmount, filter_to_mount):

        self.log.info("swap_filter swap %s=>cam=>%s" % (filter_to_mount, filter_to_unmount))

        self.models['observatoryModel'].swap_filter(filter_to_unmount)

        self.unmounted_filter = filter_to_unmount
        self.mounted_filter = filter_to_mount

        return

    def get_filter_to_unmount(self):

        return self.models['observatoryModel'].params.filter_removable_list[0]

    def get_need_filter_swap(self):

        return self.need_filter_swap, self.filter_to_unmount, self.filter_to_mount

    def update_telemetry(self, telemetry_list):

        for telemetry in telemetry_list:
            self.telemetry_stream[telemetry.name]['telemetry'].update(telemetry)
            for callback in self.telemetry_stream[telemetry.name]['callback']:
                callback(self.telemetry_stream[telemetry.name]['telemetry'])

    # def update_time(self, time):
    #
    #     timestamp = time.timestamp
    #     night = time.night
    #
    #     self.time = timestamp
    #     self.models['observatoryModel'].update_state(self.time)
    #     if not self.survey_started:
    #         raise Exception('Start survey!')
    #         self.start_survey(timestamp, night)
    #
    #     if self.isnight:
    #         if timestamp >= self.sunrise_timestamp:
    #             self.end_night(timestamp, night)
    #     else:
    #         if timestamp >= self.sunset_timestamp:
    #             self.start_night(timestamp, night)
    #
    #     return self.isnight

    def update_internal_conditions(self, observatory_state):

        if observatory_state.unmountedfilters != self.models['observatoryModel'].current_state.unmountedfilters:
            unmount = observatory_state.unmountedfilters[0]
            mount = self.models['observatoryModel'].current_state.unmountedfilters[0]
            self.swap_filter(unmount, mount)

        self.models['observatoryModel'].set_state(observatory_state)
        self.models['observatoryState'].set(observatory_state)

    def select_next_target(self, obs_time):

        self.last_winner_target = self.nulltarget

        return self.last_winner_target

    def register_observation(self, observation):

        target_list = []

        return target_list

    @staticmethod
    def observation_fulfills_target(observ, target):

        return (observ.fieldid == target.fieldid) and (observ.filter == target.filter)
