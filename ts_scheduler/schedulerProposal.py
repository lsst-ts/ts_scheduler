import logging

from schedulerDefinitions import read_conf_file

class Proposal(object):
    def __init__(self, configfilepath, skymodel):

        self.log = logging.getLogger("scheduler")

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
