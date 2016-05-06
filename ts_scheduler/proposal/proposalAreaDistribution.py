from ts_scheduler.schedulerDefinitions import RAD2DEG, DEG2RAD
from ts_scheduler.proposal import Proposal
from ts_scheduler.schedulerField import Field

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
        self.twilightBoundary = confdict["skyregion"]["twilight_boundary"]

class AreaDistributionProposal(Proposal):

    def __init__(self, configfilepath, skymodel):

        super(AreaDistributionProposal, self).__init__(configfilepath, skymodel)

        self.params = AreaDistributionProposalParameters(self.proposal_confdict)

        self.fields_tonight_list = []
        self.fields_tonight_dict = {}

    def start_night(self):

        super(AreaDistributionProposal, self).start_night()

    def build_night_target_list(self, timestamp):

        self.fields_tonight_list = []
        self.fields_tonight_dict = {}

        self.sky.update(timestamp)
        (sunset_timestamp, sunrise_timestamp) = self.sky.get_night_boundaries(self.params.twilightBoundary)

        self.sky.update(sunset_timestamp)
        sunset_lst_rad = self.sky.date_profile.lst_rad

        self.sky.update(sunrise_timestamp)
        sunrise_lst_rad = self.sky.date_profile.lst_rad

        # normalize RA absolute limits to the [0; 360] range
        min_abs_ra = self.sky.sun.normalize(self.params.minAbsRA)
        max_abs_ra = self.sky.sun.normalize(self.params.maxAbsRA)

        # compute RA relative min at sunset twilight
        min_rel_ra = sunset_lst_rad * RAD2DEG - self.params.deltaLST

        # compute RA relative max at sunrise twilight
        max_rel_ra = sunrise_lst_rad * RAD2DEG + self.params.deltaLST

        # normalize RA relative limits to the [0; 360] range
        min_rel_ra = self.sky.sun.normalize(min_rel_ra)
        max_rel_ra = self.sky.sun.normalize(max_rel_ra)

        # DEC absolute limits
        min_abs_dec = self.params.minAbsDec
        max_abs_dec = self.params.maxAbsDec

        # compute DEC relative min
        min_rel_dec = self.sky.date_profile.location.latitude - self.params.maxReach

        # compute DEC relative max
        max_rel_dec = self.sky.date_profile.location.latitude + self.params.maxReach

        sql = 'SELECT * from Field WHERE '

        # filter by absolute RA limits
        if max_abs_ra > min_abs_ra:
            sql += 'fieldRA BETWEEN %f AND %f AND ' % (min_abs_ra, max_abs_ra)
        else:
            sql += '(fieldRA BETWEEN %f AND 360 OR ' % (min_abs_ra)
            sql += 'fieldRA BETWEEN 0 AND %f) AND ' % (max_abs_ra)

        # filter by relative RA limits
        if max_rel_ra > min_rel_ra:
            sql += 'fieldRA BETWEEN %f AND %f AND ' % (min_rel_ra, max_rel_ra)
        else:
            sql += '(fieldRA BETWEEN %f AND 360 OR ' % (min_rel_ra)
            sql += 'fieldRA BETWEEN 0 AND %f) AND ' % (max_rel_ra)

        # filter by absolute DEC limits
        sql += 'fieldDec BETWEEN %f AND %f AND ' % (min_abs_dec, max_abs_dec)

        # filter by relative DEC limits
        sql += 'fieldDec BETWEEN %f AND %f ' % (min_rel_dec, max_rel_dec)

        # subtract galactic exclusion zone
        if (self.params.taperB != 0) & (self.params.taperL != 0):
            band = self.params.peakL - self.params.taperL
            sql += 'AND ((fieldGL < 180 AND abs(fieldGB) > (%f - (%f * abs(fieldGL)) / %f)) OR ' % \
                   (self.params.peakL, band, self.params.taperB)
            sql += '(fieldGL > 180 AND abs(fieldGB) > (%f - (%f * abs(fieldGL - 360)) / %f))) ' % \
                   (self.params.peakL, band, self.params.taperB)

        sql += 'order by fieldId'

        res = self.db.query(sql)

        for row in res:
            field = Field()
            fieldid = row[0]
            field.fieldid = fieldid
            field.fov_rad = row[1] * DEG2RAD
            field.ra_rad = row[2] * DEG2RAD
            field.dec_rad = row[3] * DEG2RAD
            field.gl_rad = row[4] * DEG2RAD
            field.gb_rad = row[5] * DEG2RAD
            field.el_rad = row[6] * DEG2RAD
            field.eb_rad = row[7] * DEG2RAD
            self.fields_tonight_list.append(fieldid)
            self.fields_tonight_dict[fieldid] = field

        return
