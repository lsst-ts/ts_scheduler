from schedulerDefinitions import read_conf_file

class Proposal(object):
    def __init__(self, log, configfilepath):

        self.log = log

        self.proposal_confdict = read_conf_file(configfilepath)

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
