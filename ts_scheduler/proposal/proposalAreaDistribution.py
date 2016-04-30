from ts_scheduler.proposal import Proposal
from ts_scheduler.sky_model import Sun

class AreaDistributionProposalParameters(object):

    def __init__(self, confdict):

        self.deltaLST = confdict["skyregion"]["delta_lst"]
        self.minAbsRA = confdict["skyregion"]["min_abs_ra"]
        self.maxAbsRA = confdict["skyregion"]["max_abs_ra"]
        self.minAbsDec = confdict["skyregion"]["min_abs_dec"]
        self.maxAbsDec = confdict["skyregion"]["max_abs_dec"]
        self.taperB = confdict["skyregion"]["taper_b"]
        self.taperL = confdict["skyregion"]["taper_l"]
        self.peakL = confdict["skyregion"]["peak_l"]
        self.maxReach = confdict["skyregion"]["max_reach"]

class AreaDistributionProposal(Proposal):

    def __init__(self, configfilepath, skymodel):

        super(AreaDistributionProposal, self).__init__(configfilepath, skymodel)

        self.param = AreaDistributionProposalParameters(self.proposal_confdict)

        self.sun = Sun()

    def start_night(self):

        super(AreaDistributionProposal, self).start_night()

    def build_night_target_list(self, timeprofile):

        sunrise_mjd = int(timeprofile.mjd) + (sunrise_hour / 24)
        sunset_mjd = int(timeprofile.mjd) + (sunset_hour / 24)

        # normalize RA absolute limits to the [0; 360] range
        raAbsMin = normalize(angle=self.param.minAbsRA, min=0, max=360, degrees=True)
        raAbsMax = normalize(angle=self.param.maxAbsRA, min=0, max=360, degrees=True)

        # compute RA relative min at sunset twilight
        raMin = (self.sun.gmst0(sunset_mjd) + self.location.longitude_RAD) * RAD2DEG - self.param.deltaLST

        # compute RA relative max at sunrise twilight
        raMax = (self.sun.gmst0(sunrise_mjd) + self.location.longitude_RAD) * RAD2DEG + self.param.deltaLST

        # normalize RA relative limits to the [0; 360] range
        raMin = self.sun.normalize(angle=raMin, min=0, max=360, degrees=True)
        raMax = self.sun.normalize(angle=raMax, min=0, max=360, degrees=True)

        # DEC absolute limits
        decAbsMin = self.param.minAbsDec
        decAbsMax = self.param.maxAbsDec

        # compute DEC relative min
        decMin = self.location.latitude_RAD * RAD2DEG - self.param.maxReach

        # compute DEC relative max
        decMax = self.location.latitude_RAD * RAD2DEG + self.param.maxReach

        sql = 'SELECT fieldID, fieldRA, fieldDec from Field WHERE '

        # filter by absolute RA limits
        if raAbsMax > raAbsMin:
            sql += 'fieldRA BETWEEN %f AND %f AND ' % (raAbsMin, raAbsMax)
        else:
            sql += '(fieldRA BETWEEN %f AND 360 OR ' % (raAbsMin)
            sql += 'fieldRA BETWEEN 0 AND %f) AND ' % (raAbsMax)

        # filter by relative RA limits
        if raMax > raMin:
            sql += 'fieldRA BETWEEN %f AND %f AND ' % (raMin, raMax)
        else:
            sql += '(fieldRA BETWEEN %f AND 360 OR ' % (raMin)
            sql += 'fieldRA BETWEEN 0 AND %f) AND ' % (raMax)

        # filter by absolute DEC limits
        sql += 'fieldDec BETWEEN %f AND % AND ' % (decAbsMin, decAbsMax)

        # filter by relative DEC limits
        sql += 'fieldDec BETWEEN %f AND % ' % (decMin, decMax)

        # subtract galactic exclusion zone
        if (self.param.taperB != 0) & (self.param.taperL != 0):
            band = self.param.peakL - self.param.taperL
            sql += 'AND ((fieldGL < 180 AND abs(fieldGB) > (%f - (%f * abs(fieldGL)) / %f)) OR ' % (self.param.peakL, band, self.param.taperB)
            sql += '(fieldGL > 180 AND abs(fieldGB) > (%f - (%f * abs(fieldGL - 360)) / %f))) ' % (self.param.peakL, band, taperB)

        sql += 'order by FieldID'

        res = self.db.query(sql)

        for line in res:
            (fieldId, fieldRa, fieldDec) = line
            field = Field(fieldId, fieldRa, fieldDec)
            self.fields_tonight[fieldId] = field

        return
