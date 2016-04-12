import os
import logging

from ts_scheduler.schedulerDefinitions import read_conf_file

class Proposal(object):
    def __init__(self, configfilepath, skymodel):

        (path, name_ext) = os.path.split(configfilepath)
        (name, ext) = os.path.splitext(name_ext)
        self.name = name

        self.log = logging.getLogger("scheduler.proposal.%s" % self.name)

        self.proposal_confdict = read_conf_file(configfilepath)

        self.skyModel = skymodel

    def start_survey(self):
        return

    def end_survey(self):
        return

    def start_night(self):
        return

    def end_night(self):
        return

    def suggest_targets(self):
        return
