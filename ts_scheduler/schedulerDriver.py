import math
import copy
import logging
import heapq

from ts_scheduler.sky_model import AstronomicalSkyModel
from ts_scheduler.schedulerDefinitions import INFOX, DEG2RAD, read_conf_file, conf_file_path
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryModel
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.proposal import ScriptedProposal
from ts_scheduler.proposal import AreaDistributionProposal
from ts_scheduler.fields import FieldsDatabase

class DriverParameters(object):

    def __init__(self, confdict):

        self.coadd_values = confdict["ranking"]["coadd_values"]

        tmax = confdict["ranking"]["timebonus_tmax"]
        bmax = confdict["ranking"]["timebonus_bmax"]
        slope = confdict["ranking"]["timebonus_slope"]

        self.timebonus_dt = (math.sqrt(tmax * tmax + 4 * slope * tmax / bmax) - tmax) / 2
        self.timebonus_db = slope / (tmax + self.timebonus_dt)
        self.timebonus_slope = slope

class Driver(object):
    def __init__(self):

        self.log = logging.getLogger("schedulerDriver")

        driver_confdict = read_conf_file(conf_file_path(__name__, "../conf", "scheduler", "driver.conf"))
        self.params = DriverParameters(driver_confdict)

        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        self.location = ObservatoryLocation()
        self.location.configure(site_confdict)

        observatory_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                             "observatoryModel.conf"))
        self.observatoryModel = ObservatoryModel(self.location)
        self.observatoryModel.configure(observatory_confdict)

        self.sky = AstronomicalSkyModel(self.location)

        self.db = FieldsDatabase()

        self.build_fields_dict()

        survey_confdict = read_conf_file(conf_file_path(__name__, "../conf", "survey", "survey.conf"))

        self.propid_counter = 0
        self.science_proposal_list = []

        if 'scripted_propconf' in survey_confdict["proposals"]:
            scripted_propconflist = survey_confdict["proposals"]["scripted_propconf"]
        else:
            scripted_propconflist = []
        if not isinstance(scripted_propconflist, list):
            # turn it into a list with one entry
            propconf = scripted_propconflist
            scripted_propconflist = []
            scripted_propconflist.append(propconf)
        self.log.info("init: scripted proposals %s" % (scripted_propconflist))

        for k in range(len(scripted_propconflist)):
            self.propid_counter += 1
            scripted_prop = ScriptedProposal(self.propid_counter,
                                             conf_file_path(__name__, "../conf", "survey",
                                                            "{}".format(scripted_propconflist[k])),
                                             self.sky)
            self.science_proposal_list.append(scripted_prop)

        if 'areadistribution_propconf' in survey_confdict["proposals"]:
            areadistribution_propconflist = survey_confdict["proposals"]["areadistribution_propconf"]
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
            self.propid_counter += 1
            configfilepath = conf_file_path(__name__,
                                            "../conf",
                                            "survey",
                                            "{}".format(areadistribution_propconflist[k]))
            area_prop = AreaDistributionProposal(self.propid_counter,
                                                 configfilepath,
                                                 self.sky)
            self.science_proposal_list.append(area_prop)

        self.time = 0.0
        self.targetid = 0
        self.survey_started = False
        self.isnight = False
        self.sunset_timestamp = 0.0
        self.sunrise_timestamp = 0.0

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
            self.log.debug("buildFieldsTable: %s" % (self.fields_dict[fieldid]))
        self.log.info("buildFieldsTable: %d fields" % (len(self.fields_dict)))

    def get_fields_dict(self):

        return self.fields_dict

    def start_survey(self, timestamp):

        self.log.info("start_survey t=%.1f" % timestamp)

        self.survey_started = True
        for prop in self.science_proposal_list:
            prop.start_survey()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(-12.0)
        self.log.info("start_survey sunset=%.1f sunrise=%.1f" % (sunset, sunrise))
        if sunset < timestamp < sunrise:
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
        (sunset, sunrise) = self.sky.get_night_boundaries(-12.0)
        self.log.info("end_night sunset=%.1f sunrise=%.1f" % (sunset, sunrise))

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
            if timestamp > self.sunrise_timestamp:
                self.end_night(timestamp)
        else:
            if timestamp > self.sunset_timestamp:
                self.start_night(timestamp)

    def update_internal_conditions(self, observatory_state):

        self.time = observatory_state.time
        self.observatoryModel.set_state(observatory_state)

    def update_external_conditions(self, timestamp):
        return

    def select_next_target(self):

        targets_dict = {}
        targets_heap = []

        for prop in self.science_proposal_list:
            proptarget_list = prop.suggest_targets(self.time)
            self.log.log(INFOX, "select_next_target propid=%d name=%s targets=%d" %
                         (prop.propid, prop.name, len(proptarget_list)))

            for target in proptarget_list:
                target.propid_list = [prop.propid]
                target.value_list = [target.value]
                fieldfilter = (target.fieldid, target.filter)
                if fieldfilter in targets_dict:
                    if self.params.coadd_values:
                        targets_dict[fieldfilter][0].value += target.value
                        targets_dict[fieldfilter][0].propid_list.append(prop.propid)
                        targets_dict[fieldfilter][0].propvalue_list.append(target.value)
                    else:
                        targets_dict[fieldfilter].append(copy.deepcopy(target))
                else:
                    targets_dict[fieldfilter] = [copy.deepcopy(target)]

        for fieldfilter in targets_dict:
            slewtime = self.observatoryModel.get_slew_delay(targets_dict[fieldfilter][0])
            if slewtime >= 0:
                slewtimebonus = self.compute_slewtime_bonus(slewtime)
                for target in targets_dict[fieldfilter]:
                    target.cost = slewtime
                    target.rank = target.value + slewtimebonus
                    heapq.heappush(targets_heap, (-target.rank, target))

        try:
            winner_target = heapq.heappop(targets_heap)[1]
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
