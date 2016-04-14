import copy
import logging

from ts_scheduler.sky_model import AstronomicalSkyModel
from ts_scheduler.schedulerDefinitions import INFOX, DEG2RAD, read_conf_file, conf_file_path
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryModel
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.proposal import ScriptedProposal
from ts_scheduler.proposal import AreaDistributionProposal

class Driver(object):
    def __init__(self):

        self.log = logging.getLogger("schedulerDriver.Driver")

        self.science_proposal_list = []

        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        self.location = ObservatoryLocation()
        self.location.configure(site_confdict)

        observatory_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                             "observatoryModel.conf"))
        self.observatoryModel = ObservatoryModel(self.location)
        self.observatoryModel.configure(observatory_confdict)

        self.skyModel = AstronomicalSkyModel(self.location)

        self.build_fields_dict()

        survey_confdict = read_conf_file(conf_file_path(__name__, "../conf", "survey", "survey.conf"))

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
        self.newTarget = Target()

    def build_fields_dict(self):

        lines = file(conf_file_path(__name__, "../conf", "system", "tessellationFields")).readlines()
        fieldid = 0
        self.fieldsDict = {}
        for line in lines:
            line = line.strip()
            if not line:			# skip blank line
                continue
            if line[0] == '#': 		# skip comment line
                continue
            fieldid += 1
            values = line.split()
            field = Field()
            field.fieldid = fieldid
            field.ra_rad = eval(values[0]) * DEG2RAD
            field.dec_rad = eval(values[1]) * DEG2RAD
            field.gl_rad = eval(values[2]) * DEG2RAD
            field.gb_rad = eval(values[3]) * DEG2RAD
            field.el_rad = eval(values[4]) * DEG2RAD
            field.eb_rad = eval(values[5]) * DEG2RAD
            field.fov_rad = 3.5 * DEG2RAD

            self.fieldsDict[fieldid] = field
            self.log.log(INFOX, "buildFieldsTable: %s" % (self.fieldsDict[fieldid]))

            if fieldid > 10:
                break

        self.log.info("buildFieldsTable: %d fields" % (len(self.fieldsDict)))

    def get_fields_dict(self):

        return self.fieldsDict

    def start_survey(self):

        for prop in self.science_proposal_list:
            prop.start_survey()

        self.log.info("StartSurvey")

    def end_survey(self):

        for prop in self.science_proposal_list:
            prop.end_survey()

    def start_night(self):

        for prop in self.science_proposal_list:
            prop.start_night()

    def end_night(self):

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

        target_list = []
        ntargets = 0
        for prop in self.science_proposal_list:
            proptarget_list = prop.suggest_targets(self.time)

            for target in proptarget_list:
                target.cost = self.observatoryModel.get_slew_delay(target)
                target_list.append(target)
                ntargets += 1

        if ntargets > 0:
            winnervalue = 0.0
            winnertarget = None
            for target in target_list:
                if target.value > winnervalue:
                    winnertarget = target

            self.targetid += 1
            self.newTarget = copy.deepcopy(winnertarget)
            self.newTarget.targetid = self.targetid

        return self.newTarget

    def register_observation(self, topic_observation):

        self.observatoryModel.observe(topic_observation)
