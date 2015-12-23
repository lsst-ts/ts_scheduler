import time

from schedulerTarget  import *
from observatoryModel import *
from schedulerField   import *
from schedulerScriptedProposal import *

class schedulerDriver (object):
    def __init__ (self, log):

        self.log = log
        self.scienceProposals = []

        self.observatoryModel = ObservatoryModel(self.log)
        self.buildFieldsDict()

        surveyConfigDict, pairs = readConfFile("../conf/survey/survey.conf")
        if (surveyConfigDict.has_key('scriptedPropConf')) :
            scriptedPropConf = surveyConfigDict["scriptedPropConf"]
            print("    scriptedPropConf:%s" % (scriptedPropConf))
        else:
            scriptedPropConf =  None
            print("    scriptedPropConf:%s default" % (scriptedPropConf))
        if (not isinstance(scriptedPropConf,list)):
            # turn it into a list with one entry
            saveConf = scriptedPropConf
            scriptedPropConf = []
            scriptedPropConf.append(saveConf)

        if ( scriptedPropConf[0] != None):
            for k in range(len(scriptedPropConf)):
                scriptedProp = schedulerScriptedProposal(self.log, "../conf/survey/%s" % scriptedPropConf[k])
                self.scienceProposals.append(scriptedProp)

        self.time = 0.0
        self.targetId = 0
        self.newTarget = schedulerTarget()

        return

    def buildFieldsDict(self):

        lines = file("../conf/system/tessellationFields").readlines()
        fieldId = 0
        self.fieldsDict = {}
        for line in lines:
            line = line.strip()
            if not line:			# skip blank line
                continue
            if line[0]=='#': 		# skip comment line
                continue
            fieldId += 1
            values = line.split()
            field = schedulerField()
            field.fieldId = fieldId
            field.ra_RAD  = eval(values[0])*DEG2RAD
            field.dec_RAD = eval(values[1])*DEG2RAD
            field.gl_RAD  = eval(values[2])*DEG2RAD
            field.gb_RAD  = eval(values[3])*DEG2RAD
            field.el_RAD  = eval(values[4])*DEG2RAD
            field.eb_RAD  = eval(values[5])*DEG2RAD
            field.fov_RAD = 3.5*DEG2RAD

            self.fieldsDict[fieldId] = field
            self.log.info("schedulerDriver.buildFieldsTable: %s" % (self.fieldsDict[fieldId]))

            if fieldId > 10:
                break

        self.log.log(INFOX, "schedulerDriver.buildFieldsTable: %d fields" % (len(self.fieldsDict)))

        return

    def getFieldsDict(self):

        return self.fieldsDict
        
    def startSurvey(self):

        for prop in self.scienceProposals:
            prop.startSurvey()

        self.log.log(INFOX, "schedulerDriver.startSurvey")

    	return

    def endSurvey(self):

        for prop in self.scienceProposals:
            prop.endSurvey()

    	return

    def startNight(self):

        for prop in self.scienceProposals:
            prop.startNight()

        return

    def endNight(self):

        for prop in self.scienceProposals:
            prop.endNight()

        return

    def swapFilterIn(self):
        return

    def swapFilterOut(self):
        return

    def updateInternalConditions(self, topicTime):

        self.time = topicTime.timestamp
        self.observatoryModel.updateState(self.time)

        return

    def updateExternalConditions(self, topicTime):
        return

    def selectNextTarget(self):

        targetsList = []
        nTargets = 0
        for prop in self.scienceProposals:
            propTargetsList = prop.suggestTargets()

            for target in propTargetsList:
                    targetsList.append(target)
                    nTargets += 1

        if nTargets > 0:
            winnerValue  = 0.0
            winnerTarget = None
            for target in targetsList:
                if target.value > winnerValue:
                    winnerTarget = target               

            self.targetId += 1
            self.newTarget.targetId = self.targetId
            self.newTarget.fieldId  = winnerTarget.fieldId
            self.newTarget.filter   = winnerTarget.filter
            self.newTarget.ra_RAD   = winnerTarget.ra_RAD
            self.newTarget.dec_RAD  = winnerTarget.dec_RAD
            self.newTarget.ang_RAD  = winnerTarget.ang_RAD
            self.newTarget.numexp   = winnerTarget.numexp

        return self.newTarget

    def registerObservation(self, topicObservation):

        self.observatoryModel.observe(topicObservation)

        return

