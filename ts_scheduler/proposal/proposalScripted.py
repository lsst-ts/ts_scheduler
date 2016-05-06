import logging
import os

from ts_scheduler.schedulerDefinitions import DEG2RAD
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.proposal import Proposal

class ScriptedProposal(Proposal):
    def __init__(self, configfilepath, skymodel):

        super(ScriptedProposal, self).__init__(configfilepath, skymodel)
        self.log = logging.getLogger("proposalScripted.ScriptedProposal")

        resource_path = os.path.dirname(configfilepath)
        self.script_file = os.path.join(resource_path, self.proposal_confdict["script"]["scriptfile"])

        self.read_script()

        self.targetid = 0

    def read_script(self):

        scriptfilepath = self.script_file
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
            target.exptimes = [int(x) for x in values[6].split(',')]

            self.targetsList.append(target)
        self.log.info("%d targets" % len(self.targetsList))

    def suggest_targets(self, time):

        super(ScriptedProposal, self).suggest_targets(time)

        if self.targetid < len(self.targetsList):
            nexttarget = self.targetsList[self.targetid]
        else:
            nexttarget = self.targetsList[-1]
        nexttarget.targetid = self.targetid
        nexttarget.value = 1.0
        nexttarget.time = time

        target_list = list([nexttarget])

        ra_list = []
        dec_list = []
        filter_list = []
        for target in target_list:
            ra_list.append(target.ra_rad)
            dec_list.append(target.dec_rad)
            filter_list.append(target.filter)
        sky_mags = self.sky.get_sky_brightness_timeblock(time, 1, 1, ra_list, dec_list)

        for ix, filter in enumerate(filter_list):
            if filter == "u":
                target_list[ix].skybrightness = sky_mags[0][ix].u
            elif filter == "g":
                target_list[ix].skybrightness = sky_mags[0][ix].g
            elif filter == "r":
                target_list[ix].skybrightness = sky_mags[0][ix].r
            elif filter == "i":
                target_list[ix].skybrightness = sky_mags[0][ix].i
            elif filter == "z":
                target_list[ix].skybrightness = sky_mags[0][ix].z
            elif filter == "y":
                target_list[ix].skybrightness = sky_mags[0][ix].y
            else:
                target_list[ix].skybrightness = 0.0

        self.targetid += 1

        return target_list
