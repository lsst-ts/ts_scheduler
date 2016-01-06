from schedulerDefinitions import DEG2RAD
from schedulerTarget import schedulerTarget
from schedulerProposal import schedulerProposal

class schedulerScriptedProposal(schedulerProposal):
    def __init__(self, log, configFilePath):

        super(schedulerScriptedProposal, self).__init__(log, configFilePath)

        self.scriptFile = self.propConfigDict["scriptFile"]

        self.readScript()

        self.targetId = 0

    def readScript(self):

        scriptFilePath = "../conf/survey/%s" % self.scriptFile
        lines = file(scriptFilePath).readlines()
        targetId = 0
        self.targetsList = []
        for line in lines:
            line = line.strip()
            if not line:			# skip blank line
                continue
            if line[0] == '#': 		# skip comment line
                continue
            targetId += 1
            values = line.split()
            target = schedulerTarget()
            target.fieldId = eval(values[0])
            target.filter = values[1]
            target.ra_RAD = eval(values[2]) * DEG2RAD
            target.dec_RAD = eval(values[3]) * DEG2RAD
            target.ang_RAD = eval(values[4]) * DEG2RAD
            target.numexp = eval(values[5])

            self.targetsList.append(target)
            print target

    def suggestTargets(self):

        super(schedulerScriptedProposal, self).suggestTargets()

        if self.targetId < len(self.targetsList):
            nextTarget = self.targetsList[self.targetId]
            nextTarget.value = 1.0
            self.targetId += 1
            return list([nextTarget])
        else:
            nextTarget = self.targetsList[-1]
            nextTarget.value = 1.0
            self.targetId += 1
            return list([nextTarget])
