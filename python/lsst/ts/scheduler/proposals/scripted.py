import math
import numpy

from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.proposals import Proposal

__all__ = ["ScriptedProposal"]

class ScriptedProposal(Proposal):
    def __init__(self, propid, name, confdict, scriptfile, skymodel):

        Proposal.__init__(self, propid, name, confdict, skymodel)

        self.script_file = scriptfile
        self.read_script()

        self.targetid = 0

    def read_script(self):

        scriptfilepath = self.script_file
        lines = open(scriptfilepath).readlines()
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
            target.ra_rad = math.radians(eval(values[2]))
            target.dec_rad = math.radians(eval(values[3]))
            target.ang_rad = math.radians(eval(values[4]))
            target.num_exp = eval(values[5])
            target.exp_times = [int(x) for x in values[6].split(',')]

            self.targetsList.append(target)
        self.log.info("%d targets" % len(self.targetsList))

    def suggest_targets(self, time):

        Proposal.suggest_targets(self, time)

        if self.targetid < len(self.targetsList):
            nexttarget = self.targetsList[self.targetid]
        else:
            nexttarget = self.targetsList[-1]
        nexttarget.targetid = self.targetid
        nexttarget.time = time
        nexttarget.value = 1.0

        target_list = list([nexttarget])

        id_list = []
        ra_list = []
        dec_list = []
        filter_list = []
        for target in target_list:
            id_list.append(target.fieldid)
            ra_list.append(target.ra_rad)
            dec_list.append(target.dec_rad)
            filter_list.append(target.filter)
        self.sky.update(time)
        sky_mags = self.sky.get_sky_brightness(numpy.array(id_list))

        target_list[0].sky_brightness = sky_mags[target.filter][0]

        self.targetid += 1

        return target_list

    def register_observation(self, observation):
        pass
