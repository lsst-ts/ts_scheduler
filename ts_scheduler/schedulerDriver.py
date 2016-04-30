import copy
import logging
import sqlite3
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

class Driver(object):
    def __init__(self):

        self.log = logging.getLogger("schedulerDriver.Driver")

        driver_confdict = read_conf_file(conf_file_path(__name__, "../conf", "scheduler", "driver.conf"))
        self.params = DriverParameters(driver_confdict)

        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        self.location = ObservatoryLocation()
        self.location.configure(site_confdict)

        observatory_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                             "observatoryModel.conf"))
        self.observatoryModel = ObservatoryModel(self.location)
        self.observatoryModel.configure(observatory_confdict)

        self.skyModel = AstronomicalSkyModel(self.location)

        self.db = FieldsDatabase()

        self.build_fields_dict()

        survey_confdict = read_conf_file(conf_file_path(__name__, "../conf", "survey", "survey.conf"))

        self.science_proposal_list = []

        if 'scripted_propconf' in survey_confdict["proposals"]:
            scripted_propconflist = survey_confdict["proposals"]["scripted_propconf"]
            self.log.info("scripted_propconf:%s" % (scripted_propconflist))
        else:
            scripted_propconflist = None
            self.log.info("scriptedPropConf:%s default" % (scripted_propconflist))
        if not isinstance(scripted_propconflist, list):
            # turn it into a list with one entry
            propconf = scripted_propconflist
            scripted_propconflist = []
            scripted_propconflist.append(propconf)

        if scripted_propconflist[0] is not None:
            for k in range(len(scripted_propconflist)):
                scripted_prop = ScriptedProposal(conf_file_path(__name__, "../conf", "survey",
                                                 "{}".format(scripted_propconflist[k])), self.skyModel)
                self.science_proposal_list.append(scripted_prop)

        if 'areadistribution_propconf' in survey_confdict["proposals"]:
            areadistribution_propconflist = survey_confdict["proposals"]["areadistribution_propconf"]
            self.log.info("areadistribution_propconf:%s" % (areadistribution_propconflist))
        else:
            areadistribution_propconflist = None
            self.log.info("areadistributionPropConf:%s default" % (areadistribution_propconflist))
        if not isinstance(areadistribution_propconflist, list):
            # turn it into a list with one entry
            propconf = areadistribution_propconflist
            areadistribution_propconflist = []
            areadistribution_propconflist.append(propconf)

        if areadistribution_propconflist[0] is not None:
            for k in range(len(areadistribution_propconflist)):
                area_prop = AreaDistributionProposal(conf_file_path(__name__, "../conf", "survey",
                                                     "{}".format(areadistribution_propconflist[k])),
                                                     self.skyModel)
                self.science_proposal_list.append(area_prop)

        self.time = 0.0
        self.targetid = 0

    def build_fields_dict(self):

        sql = "select * from Field"
        res = self.db.query(sql)

        self.fieldsDict = {}
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
            self.fieldsDict[fieldid] = field
            self.log.log(INFOX, "buildFieldsTable: %s" % (self.fieldsDict[fieldid]))
        self.log.info("buildFieldsTable: %d fields" % (len(self.fieldsDict)))

    def get_fields_dict(self):

        return self.fieldsDict

    def start_survey(self):

        self.log.info("start survey")

        for prop in self.science_proposal_list:
            prop.start_survey()

    def end_survey(self):

        self.log.info("end survey")

        for prop in self.science_proposal_list:
            prop.end_survey()

    def start_night(self):

        self.log.info("start night")

        for prop in self.science_proposal_list:
            prop.start_night()

    def end_night(self):

        self.log.info("end night")

        for prop in self.science_proposal_list:
            prop.end_night()

    def swap_filter_in(self):
        return

    def swap_filter_out(self):
        return

    def update_internal_conditions(self, topic_time):

        self.time = topic_time.timestamp
        self.observatoryModel.update_state(self.time)

    def update_external_conditions(self, topic_time):
        return

    def select_next_target(self):

        targets_dict = {}
        targets_heap = []

        for prop in self.science_proposal_list:
            proptarget_list = prop.suggest_targets(self.time)

            for target in proptarget_list:
                fieldfilter = (target.fieldid, target.filter)
                if fieldfilter in targets_dict:
                    if self.params.coadd_values:
                        targets_dict[fieldfilter].value += target.value
                        targets_dict[fieldfilter].propIds.append(prop.propid)
                        targets_dict[fieldfilter].propValues.append(target.value)
                    else:
                        targets_dict[fieldfilter].append(copy.deepcopy(target))
                else:
                    targets_dict[fieldfilter] = [copy.deepcopy(target)]

        for fieldfilter in targets_dict:
            cost = self.observatoryModel.get_slew_delay(targets_dict[fieldfilter][0])
            if cost >= 0:
                for target in targets_dict[fieldfilter]:
                    target.cost = cost
                    target.rank = target.value - target.cost
                    heapq.heappush(targets_heap, (-target.rank, target))

        winner_target = heapq.heappop(targets_heap)[1]
        self.targetid += 1
        winner_target.targetid = self.targetid
        winner_target.time = self.time

        return winner_target

    def register_observation(self, topic_observation):

        self.observatoryModel.observe(topic_observation)
