from schedulerDefinitions import DEG2RAD
from schedulerTarget import Target
from schedulerProposal import Proposal

class ScriptedProposal(Proposal):
    def __init__(self, log, configfilepath):

        super(ScriptedProposal, self).__init__(log, configfilepath)

        self.script_file = self.proposal_confdict["scriptFile"]

        self.read_script()

        self.targetid = 0

    def read_script(self):

        scriptfilepath = "../conf/survey/%s" % self.script_file
        lines = file(scriptfilepath).readlines()
        targetid = 0
        self.targetsList = []
        for line in lines:
            line = line.strip()
            if not line:			# skip blank line
                continue
            if line[0] == '#': 		# skip comment line
                continue
            targetid += 1
            values = line.split()
            target = Target()
            target.fieldid = eval(values[0])
            target.filter = values[1]
            target.ra_rad = eval(values[2]) * DEG2RAD
            target.dec_rad = eval(values[3]) * DEG2RAD
            target.ang_rad = eval(values[4]) * DEG2RAD
            target.numexp = eval(values[5])

            self.targetsList.append(target)
            print target

    def suggest_targets(self):

        super(ScriptedProposal, self).suggest_targets()

        if self.targetid < len(self.targetsList):
            nexttarget = self.targetsList[self.targetid]
            nexttarget.value = 1.0
            self.targetid += 1
            return list([nexttarget])
        else:
            nexttarget = self.targetsList[-1]
            nexttarget.value = 1.0
            self.targetid += 1
            return list([nexttarget])
