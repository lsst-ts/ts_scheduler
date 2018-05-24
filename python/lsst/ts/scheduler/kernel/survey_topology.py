from builtins import object
import time
import copy

__all__ = ["SurveyTopology"]


class SurveyTopology(object):

    def __init__(self):
        self.propid_counter = 0
        self.science_proposal_list = []
