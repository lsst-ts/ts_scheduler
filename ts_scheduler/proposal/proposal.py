import os
import logging

from ts_scheduler.schedulerDefinitions import read_conf_file
from ts_scheduler.fields import FieldsDatabase

class Proposal(object):
    def __init__(self, propid, configfilepath, skymodel):

        self.propid = propid

        (path, name_ext) = os.path.split(configfilepath)
        (name, ext) = os.path.splitext(name_ext)
        self.name = name

        self.log = logging.getLogger("scheduler.proposal.%s" % self.name)

        self.proposal_confdict = read_conf_file(configfilepath)

        self.sky = skymodel

        self.db = FieldsDatabase()

    def start_survey(self):
        return

    def end_survey(self):
        return

    def start_night(self):
        return

    def end_night(self):
        return

    def suggest_targets(self, time):
        return []
