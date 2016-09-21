import os
import math
import copy
import logging

from operator import itemgetter

from ts_scheduler.setup import EXTENSIVE, WORDY
from ts_scheduler.sky_model import AstronomicalSkyModel
from ts_scheduler.schedulerDefinitions import DEG2RAD, read_conf_file
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryModel
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.proposal import ScriptedProposal
from ts_scheduler.proposal import AreaDistributionProposal
from ts_scheduler.fields import FieldsDatabase

class DriverParameters(object):

    def __init__(self):

        self.coadd_values = False
        self.timebonus_dt = 0.0
        self.timebonus_db = 0.0
        self.timebonus_slope = 0.0
        self.night_boundary = 0.0
        self.ignore_sky_brightness = False
        self.ignore_airmass = False
        self.ignore_clouds = False
        self.ignore_seeing = False

    def configure(self, confdict):

        self.coadd_values = confdict["ranking"]["coadd_values"]

        tmax = confdict["ranking"]["timebonus_tmax"]
        bmax = confdict["ranking"]["timebonus_bmax"]
        slope = confdict["ranking"]["timebonus_slope"]
        self.timebonus_dt = (math.sqrt(tmax * tmax + 4 * slope * tmax / bmax) - tmax) / 2
        self.timebonus_db = slope / (tmax + self.timebonus_dt)
        self.timebonus_slope = slope

        self.night_boundary = confdict["constraints"]["night_boundary"]
        self.ignore_sky_brightness = confdict["constraints"]["ignore_sky_brightness"]
        self.ignore_airmass = confdict["constraints"]["ignore_airmass"]
        self.ignore_clouds = confdict["constraints"]["ignore_clouds"]
        self.ignore_seeing = confdict["constraints"]["ignore_seeing"]

class Driver(object):
    def __init__(self):

        self.log = logging.getLogger("schedulerDriver")

        self.params = DriverParameters()
        self.location = ObservatoryLocation()

        self.observatoryModel = ObservatoryModel(self.location)

        self.sky = AstronomicalSkyModel(self.location)

        self.db = FieldsDatabase()

        self.build_fields_dict()

        self.propid_counter = 0
        self.science_proposal_list = []

        self.start_time = 0.0
        self.time = 0.0
        self.targetid = 0
        self.survey_started = False
        self.isnight = False
        self.sunset_timestamp = 0.0
        self.sunrise_timestamp = 0.0
        self.survey_duration_DAYS = 0.0
        self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0

    def configure_survey(self, survey_conf_file):

        prop_conf_path = os.path.dirname(survey_conf_file)
        confdict = read_conf_file(survey_conf_file)

        self.survey_duration_DAYS = confdict["survey"]["survey_duration"]
        self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0

        self.propid_counter = 0
        self.science_proposal_list = []

        if 'scripted_propconf' in confdict["proposals"]:
            scripted_propconflist = confdict["proposals"]["scripted_propconf"]
        else:
            scripted_propconflist = []
        if not isinstance(scripted_propconflist, list):
            # turn it into a list with one entry
            propconf = scripted_propconflist
            scripted_propconflist = []
            scripted_propconflist.append(propconf)
        self.log.info("configure_survey: scripted proposals %s" % (scripted_propconflist))
        for k in range(len(scripted_propconflist)):
            self.propid_counter += 1
            scripted_prop = ScriptedProposal(self.propid_counter,
                                             os.path.join(prop_conf_path,
                                                          "{}".format(scripted_propconflist[k])),
                                             self.sky)
            self.science_proposal_list.append(scripted_prop)

        if 'areadistribution_propconf' in confdict["proposals"]:
            areadistribution_propconflist = confdict["proposals"]["areadistribution_propconf"]
        else:
            areadistribution_propconflist = []
            self.log.info("areadistributionPropConf:%s default" % (areadistribution_propconflist))
        if not isinstance(areadistribution_propconflist, list):
            # turn it into a list with one entry
            propconf = areadistribution_propconflist
            areadistribution_propconflist = []
            areadistribution_propconflist.append(propconf)
        self.log.info("init: areadistribution proposals %s" % (areadistribution_propconflist))
        for k in range(len(areadistribution_propconflist)):
            configfilepath = os.path.join(prop_conf_path, "{}".format(areadistribution_propconflist[k]))
            (path, name_ext) = os.path.split(configfilepath)
            (name, ext) = os.path.splitext(name_ext)
            proposal_confdict = read_conf_file(configfilepath)
            self.create_area_proposal(name, proposal_confdict)

        for prop in self.science_proposal_list:
            prop.configure_constraints(self.params)

    def configure_duration(self, survey_duration):

        self.survey_duration_DAYS = survey_duration
        self.survey_duration_SECS = survey_duration * 24 * 60 * 60.0

    def configure(self, confdict):

        self.params.configure(confdict)
        self.log.log(WORDY,
                     "configure: coadd_values=%s" % (self.params.coadd_values))
        self.log.log(WORDY,
                     "configure: timebonus_dt=%.3f" % (self.params.timebonus_dt))
        self.log.log(WORDY,
                     "configure: timebonus_db=%.3f" % (self.params.timebonus_db))
        self.log.log(WORDY,
                     "configure: timebonus_slope=%.3f" % (self.params.timebonus_slope))
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

        for prop in self.science_proposal_list:
            prop.configure_constraints(self.params)

    def configure_location(self, confdict):

        self.location.configure(confdict)
        self.observatoryModel.location.configure(confdict)
        self.sky.__init__(self.location)

    def configure_observatory(self, confdict):

        self.observatoryModel.configure(confdict)

    def configure_telescope(self, confdict):

        self.observatoryModel.configure_telescope(confdict)

    def configure_rotator(self, confdict):

        self.observatoryModel.configure_rotator(confdict)

    def configure_dome(self, confdict):

        self.observatoryModel.configure_dome(confdict)

    def configure_optics(self, confdict):

        self.observatoryModel.configure_optics(confdict)

    def configure_camera(self, confdict):

        self.observatoryModel.configure_camera(confdict)

    def configure_slew(self, confdict):

        self.observatoryModel.configure_slew(confdict)

    def configure_park(self, confdict):

        self.observatoryModel.configure_park(confdict)

    def create_area_proposal(self, name, config_dict):

        self.propid_counter += 1
        area_prop = AreaDistributionProposal(self.propid_counter, name, config_dict, self.sky)
        area_prop.configure_constraints(self.params)
        self.science_proposal_list.append(area_prop)

    #def configure_area_proposal(self,
    #                            prop_id,
    #                            name,
    #                            config_dict):

    #    area_prop = AreaDistributionProposal(prop_id, name, config_dict, self.sky)
    #    self.science_proposal_list.append(area_prop)

    def build_fields_dict(self):

        sql = "select * from Field"
        res = self.db.query(sql)

        self.fields_dict = {}
        for row in res:
            field = Field()
            fieldid = row[0]
            field.fieldid = fieldid
            field.fov_rad = row[1] * DEG2RAD
            field.ra_rad = row[2] * DEG2RAD
            field.dec_rad = row[3] * DEG2RAD
            field.gl_rad = row[4] * DEG2RAD
            field.gb_rad = row[5] * DEG2RAD
            field.el_rad = row[6] * DEG2RAD
            field.eb_rad = row[7] * DEG2RAD
            self.fields_dict[fieldid] = field
            self.log.log(EXTENSIVE, "buildFieldsTable: %s" % (self.fields_dict[fieldid]))
        self.log.info("buildFieldsTable: %d fields" % (len(self.fields_dict)))

    def get_fields_dict(self):

        return self.fields_dict

    def start_survey(self, timestamp):

        self.start_time = timestamp
        self.log.info("start_survey t=%.1f" % timestamp)

        self.survey_started = True
        for prop in self.science_proposal_list:
            prop.start_survey()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("start_survey sunset=%.1f sunrise=%.1f" % (sunset, sunrise))
        if sunset <= timestamp < sunrise:
            self.start_night(timestamp)

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def end_survey(self):

        self.log.info("end_survey")

        for prop in self.science_proposal_list:
            prop.end_survey()

    def start_night(self, timestamp):

        self.log.info("start_night t=%.1f" % timestamp)

        self.isnight = True

        for prop in self.science_proposal_list:
            prop.start_night(timestamp, self.observatoryModel.currentState.mountedfilters)

    def end_night(self, timestamp):

        self.log.info("end_night t=%.1f" % timestamp)

        self.isnight = False

        for prop in self.science_proposal_list:
            prop.end_night()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("end_night sunset=%.1f sunrise=%.1f" % (sunset, sunrise))

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def swap_filter_in(self):
        return

    def swap_filter_out(self):
        return

    def update_time(self, timestamp):

        self.time = timestamp
        self.observatoryModel.update_state(self.time)
        if not self.survey_started:
            self.start_survey(timestamp)

        if self.isnight:
            if timestamp >= self.sunrise_timestamp:
                self.end_night(timestamp)
        else:
            if timestamp >= self.sunset_timestamp:
                self.start_night(timestamp)

    def update_internal_conditions(self, observatory_state):

        self.time = observatory_state.time
        self.observatoryModel.set_state(observatory_state)

    def update_external_conditions(self, timestamp):
        return

    def select_next_target(self):

        targets_dict = {}
        ranked_targets_list = []
        propboost_dict = {}

        timeprogress = (self.time - self.start_time) / self.survey_duration_SECS
        for prop in self.science_proposal_list:

            progress = prop.get_progress()
            if progress > 0.0:
                if timeprogress < 1.0:
                    needindex = (1.0 - progress) / (1.0 - timeprogress)
                else:
                    needindex = 0.0
                if timeprogress > 0.0:
                    progressindex = progress / timeprogress
                else:
                    progressindex = 1.0
                propboost_dict[prop.propid] = needindex / progressindex
            else:
                propboost_dict[prop.propid] = 1.0

            proptarget_list = prop.suggest_targets(self.time)
            self.log.debug("select_next_target propid=%d name=%s targets=%d progress=%.6f propboost=%.3f" %
                           (prop.propid, prop.name, len(proptarget_list), progress,
                            propboost_dict[prop.propid]))

            for target in proptarget_list:
                target.num_props = 1
                target.propboost = propboost_dict[prop.propid]
                target.propid_list = [prop.propid]
                target.need_list = [target.need]
                target.bonus_list = [target.bonus]
                target.value_list = [target.value]
                target.propboost_list = [target.propboost]
                fieldfilter = (target.fieldid, target.filter)
                if fieldfilter in targets_dict:
                    if self.params.coadd_values:
                        targets_dict[fieldfilter][0].need += target.need
                        targets_dict[fieldfilter][0].bonus += target.bonus
                        targets_dict[fieldfilter][0].value += target.value
                        targets_dict[fieldfilter][0].propboost *= target.propboost
                        targets_dict[fieldfilter][0].num_props += 1
                        targets_dict[fieldfilter][0].propid_list.append(prop.propid)
                        targets_dict[fieldfilter][0].need_list.append(target.need)
                        targets_dict[fieldfilter][0].bonus_list.append(target.bonus)
                        targets_dict[fieldfilter][0].value_list.append(target.value)
                        targets_dict[fieldfilter][0].propboost_list.append(target.propboost)
                    else:
                        targets_dict[fieldfilter].append(copy.deepcopy(target))
                else:
                    targets_dict[fieldfilter] = [copy.deepcopy(target)]

        for fieldfilter in targets_dict:
            slewtime = self.observatoryModel.get_slew_delay(targets_dict[fieldfilter][0])
            if slewtime >= 0:
                cost_bonus = self.compute_slewtime_bonus(slewtime)
                for target in targets_dict[fieldfilter]:
                    target.slewtime = slewtime
                    target.cost_bonus = cost_bonus
                    target.rank = (target.value + cost_bonus) * target.propboost
                    ranked_targets_list.append((-target.rank, target))

        sorted_list = sorted(ranked_targets_list, key=itemgetter(0))
        try:
            winner_target = sorted_list.pop(0)[1]
            self.targetid += 1
            winner_target.targetid = self.targetid
            winner_target.time = self.time
        except:
            # if no target to suggest
            winner_target = Target()
            winner_target.num_exp = 2
            winner_target.targetid = -1

        return winner_target

    def register_observation(self, observation):

        if observation.targetid > 0:
            for prop in self.science_proposal_list:
                prop.register_observation(observation)

    def compute_slewtime_bonus(self, slewtime):

        bonus = self.params.timebonus_slope / (slewtime + self.params.timebonus_dt) - self.params.timebonus_db

        return bonus
