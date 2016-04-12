from proposal import Proposal

class AreaDistributionProposal(Proposal):
    def __init__(self, configfilepath, skymodel):

        super(AreaDistributionProposal, self).__init__(configfilepath, skymodel)

        self.deltaLST = self.proposal_confdict["skyregion"]["delta_lst"]
        self.minAbsRA = self.proposal_confdict["skyregion"]["min_abs_ra"]
        self.maxAbsRA = self.proposal_confdict["skyregion"]["max_abs_ra"]
        self.minAbsDec = self.proposal_confdict["skyregion"]["min_abs_dec"]
        self.maxAbsDec = self.proposal_confdict["skyregion"]["max_abs_dec"]
        self.taperB = self.proposal_confdict["skyregion"]["taper_b"]
        self.taperL = self.proposal_confdict["skyregion"]["taper_l"]
        self.peakL = self.proposal_confdict["skyregion"]["peak_l"]
        self.maxReach = self.proposal_confdict["skyregion"]["max_reach"]

    def start_night(self):

        super(AreaDistributionProposal, self).start_night()

    def build_night_target_list(self, dateprofile):

        return
