import time

from schedulerTarget  import *
from observatoryModel import *
from schedulerField   import *

class schedulerDriver (object):
    def __init__ (self, log):

        self.log = log

        self.observatoryModel = ObservatoryModel(self.log)
        self.buildFieldsTable()

        self.time = 0.0
        self.targetId = 0
        self.newTarget = schedulerTarget()

        return

    def buildFieldsTable(self):

        lines = file("../conf/system/tessellationFields").readlines()
        fieldID = 0
        fieldsTable = {}
        for line in lines:
            line = line.strip()
            if not line:			# skip blank line
                continue
            if line[0]=='#': 		# skip comment line
                continue
            fieldID += 1
            values = line.split()
            field = schedulerField()
            field.fieldID = fieldID
            field.ra_RAD  = eval(values[0])*DEG2RAD
            field.dec_RAD = eval(values[1])*DEG2RAD
            field.gl_RAD  = eval(values[2])*DEG2RAD
            field.gb_RAD  = eval(values[3])*DEG2RAD
            field.el_RAD  = eval(values[4])*DEG2RAD
            field.eb_RAD  = eval(values[5])*DEG2RAD

            fieldsTable[fieldID] = field
            print fieldsTable[fieldID]

        return

    def startSurvey(self):
    	return

    def endSurvey(self):
    	return

    def startNight(self):
        return

    def endNight(self):
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

        self.targetId += 1

        self.newTarget.targetId = self.targetId
        self.newTarget.fieldId  = 1234
        self.newTarget.filter   = "z"
        self.newTarget.ra       = 10.0
        self.newTarget.dec      = 30.0
        self.newTarget.angle    = 45.0
        self.newTarget.num_exposures = 2

        return self.newTarget

    def registerObservation(self, topicObservation):

        self.observatoryModel.observe(topicObservation)

        return

