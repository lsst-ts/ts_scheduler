from observatoryModel import ObservatoryModel

from schedulerDefinitions import INFOX, DEG2RAD, read_conf_file
from schedulerField import Field
from schedulerTarget import Target
from schedulerScriptedProposal import ScriptedProposal

class Driver(object):
    def __init__(self, log):

        self.log = log
        self.science_proposal_list = []

        self.observatoryModel = ObservatoryModel(self.log)
        site_confdict = read_conf_file("../conf/system/site.conf")

        observatory_confdict = read_conf_file("../conf/system/observatoryModel.conf")
        observatory_confdict.update(site_confdict)

        self.observatoryModel.configure(observatory_confdict)

        self.build_fields_dict()

        survey_confdict = read_conf_file("../conf/survey/survey.conf")
	print survey_confdict
        if ('scripted_propconf' in survey_confdict["proposals"]):
            scriptedprop_conflist = survey_confdict["proposals"]["scripted_propconf"]
            print("    scriptedpropconf:%s" % (scriptedprop_conflist))
        else:
            scriptedprop_conflist = None
            print("    scriptedPropConf:%s default" % (scriptedprop_conflist))
        if (not isinstance(scriptedprop_conflist, list)):
            # turn it into a list with one entry
            propconf = scriptedprop_conflist
            scriptedprop_conflist = []
            scriptedprop_conflist.append(propconf)

        if (scriptedprop_conflist[0] is not None):
            for k in range(len(scriptedprop_conflist)):
                scriptedprop = ScriptedProposal(self.log, "../conf/survey/%s" % scriptedprop_conflist[k])
                self.science_proposal_list.append(scriptedprop)

        self.time = 0.0
        self.targetid = 0
        self.newTarget = Target()

    def build_fields_dict(self):

        lines = file("../conf/system/tessellationFields").readlines()
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
            self.log.info("schedulerDriver.buildFieldsTable: %s" % (self.fieldsDict[fieldid]))

            if fieldid > 10:
                break

        self.log.log(INFOX, "schedulerDriver.buildFieldsTable: %d fields" % (len(self.fieldsDict)))

    def get_fields_dict(self):

        return self.fieldsDict

    def start_survey(self):

        for prop in self.science_proposal_list:
            prop.start_survey()

        self.log.log(INFOX, "schedulerDriver.startSurvey")

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
            proptarget_list = prop.suggest_targets()

            for target in proptarget_list:
                    target_list.append(target)
                    ntargets += 1

        if ntargets > 0:
            winnervalue = 0.0
            winnertarget = None
            for target in target_list:
                if target.value > winnervalue:
                    winnertarget = target

            self.targetid += 1
            self.newTarget.targetid = self.targetid
            self.newTarget.fieldid = winnertarget.fieldid
            self.newTarget.filter = winnertarget.filter
            self.newTarget.ra_rad = winnertarget.ra_rad
            self.newTarget.dec_rad = winnertarget.dec_rad
            self.newTarget.ang_rad = winnertarget.ang_rad
            self.newTarget.numexp = winnertarget.numexp

        return self.newTarget

    def register_observation(self, topic_observation):

        self.observatoryModel.observe(topic_observation)
