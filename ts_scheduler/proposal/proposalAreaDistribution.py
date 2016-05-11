import copy
import heapq

from ts_scheduler.schedulerDefinitions import RAD2DEG, DEG2RAD
from ts_scheduler.proposal import Proposal
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target

class AreaDistributionProposalParameters(object):

    def __init__(self, confdict):

        self.delta_lst = confdict["sky_region"]["delta_lst"]
        self.min_abs_ra = confdict["sky_region"]["min_abs_ra"]
        self.max_abs_ra = confdict["sky_region"]["max_abs_ra"]
        self.min_abs_dec = confdict["sky_region"]["min_abs_dec"]
        self.max_abs_dec = confdict["sky_region"]["max_abs_dec"]
        self.use_gal_exclusion = confdict["sky_region"]["use_gal_exclusion"]
        self.taperB = confdict["sky_region"]["taper_b"]
        self.taperL = confdict["sky_region"]["taper_l"]
        self.peakL = confdict["sky_region"]["peak_l"]
        self.maxReach = confdict["sky_region"]["max_reach"]
        self.twilight_boundary = confdict["sky_region"]["twilight_boundary"]

        self.filter_list = []
        self.filter_visits_dict = {}
        self.filter_min_brig_dict = {}
        self.filter_max_brig_dict = {}
        self.filter_max_seeing_dict = {}
        self.filter_exp_times_dict = {}
        filters = ["u", "g", "r", "i", "z", "y"]
        for filter in filters:
            filter_section = "filter_%s" % filter
            if filter_section in confdict:
                self.filter_list.append(filter)
                self.filter_visits_dict[filter] = confdict[filter_section]["visits"]
                self.filter_min_brig_dict[filter] = confdict[filter_section]["min_brig"]
                self.filter_max_brig_dict[filter] = confdict[filter_section]["max_brig"]
                self.filter_max_seeing_dict[filter] = confdict[filter_section]["max_seeing"]
                self.filter_exp_times_dict[filter] = confdict[filter_section]["exp_times"]

        self.max_num_targets = int(confdict["scheduling"]["max_num_targets"])
        self.accept_serendipity = confdict["scheduling"]["accept_serendipity"]
        self.accept_consecutive_visits = confdict["scheduling"]["accept_consecutive_visits"]

class AreaDistributionProposal(Proposal):

    def __init__(self, propid, configfilepath, skymodel):

        super(AreaDistributionProposal, self).__init__(propid, configfilepath, skymodel)

        self.params = AreaDistributionProposalParameters(self.proposal_confdict)

        self.fields_dict = {}
        self.targets_dict = {}

        self.filters_tonight_list = []
        self.fields_tonight_list = []
        self.total_goal = 0
        self.total_visits = 0
        self.total_progress = 0.0
        self.targets_heap = []

        self.last_observation = None
        self.last_observation_was_for_this_proposal = False

    def start_survey(self):

        super(AreaDistributionProposal, self).start_survey()

    def start_night(self, timestamp, filters_mounted_tonight_list):

        super(AreaDistributionProposal, self).start_night()

        self.filters_tonight_list = []
        for filter in self.params.filter_list:
            if filter in filters_mounted_tonight_list:
                self.filters_tonight_list.append(filter)
        self.build_fields_tonight_list(timestamp)

        # compute at start night
        self.total_goal = 0
        self.total_visits = 0
        for field in self.fields_tonight_list:
            fieldid = field.fieldid

            # remove fields too close to the moon
#            if distance2moon(self.fields_dict[fieldid]) < self.params.min_distance_moon:
#                del self.fields_tonight_list[fieldid]
#                continue

            # add new fields to fields dictionary
            if fieldid not in self.fields_dict:
                self.fields_dict[fieldid] = copy.deepcopy(field)

            # add new fields to targets dictionary
            if fieldid not in self.targets_dict:
                self.targets_dict[fieldid] = {}
                for filter in self.params.filter_list:
                    target = Target()
                    target.fieldid = fieldid
                    target.filter = filter
                    target.exp_times = self.params.filter_exp_times_dict[filter]
                    target.ra_rad = field.ra_rad
                    target.dec_rad = field.dec_rad
                    target.goal = self.params.filter_visits_dict[filter]
                    target.visits = 0
                    target.progress = 0.0
                    self.targets_dict[fieldid][filter] = target

            # compute total goal for tonight
            for filter in self.filters_tonight_list:
                if filter in self.targets_dict[fieldid]:
                    target = self.targets_dict[fieldid][filter]
                    self.total_goal += target.goal
                    self.total_visits += target.visits

        self.total_progress = self.total_visits / self.total_goal

        self.last_observation = None
        self.last_observation_was_for_this_proposal = False

    def build_fields_tonight_list(self, timestamp):

        self.fields_tonight_list = []

        self.sky.update(timestamp)
        (sunset_timestamp, sunrise_timestamp) = self.sky.get_night_boundaries(self.params.twilight_boundary)

        self.sky.update(sunset_timestamp)
        sunset_lst_rad = self.sky.date_profile.lst_rad

        self.sky.update(sunrise_timestamp)
        sunrise_lst_rad = self.sky.date_profile.lst_rad

        # normalize RA absolute limits to the [0; 360] range
        min_abs_ra = self.sky.sun.normalize(self.params.min_abs_ra)
        max_abs_ra = self.sky.sun.normalize(self.params.max_abs_ra)

        # compute RA relative min at sunset twilight
        min_rel_ra = sunset_lst_rad * RAD2DEG - self.params.delta_lst

        # compute RA relative max at sunrise twilight
        max_rel_ra = sunrise_lst_rad * RAD2DEG + self.params.delta_lst

        # normalize RA relative limits to the [0; 360] range
        min_rel_ra = self.sky.sun.normalize(min_rel_ra)
        max_rel_ra = self.sky.sun.normalize(max_rel_ra)

        # DEC absolute limits
        min_abs_dec = self.params.min_abs_dec
        max_abs_dec = self.params.max_abs_dec

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
            field.fieldid = row[0]
            field.fov_rad = row[1] * DEG2RAD
            field.ra_rad = row[2] * DEG2RAD
            field.dec_rad = row[3] * DEG2RAD
            field.gl_rad = row[4] * DEG2RAD
            field.gb_rad = row[5] * DEG2RAD
            field.el_rad = row[6] * DEG2RAD
            field.eb_rad = row[7] * DEG2RAD
            self.fields_tonight_list.append(field)

        return

    def suggest_targets(self, timestamp):

        super(AreaDistributionProposal, self).suggest_targets(timestamp)

        self.clear_evaluated_target_list()

        fields_evaluation_list = self.fields_tonight_list

        # compute sky brightness for all targets
        id_list = []
        ra_rad_list = []
        dec_rad_list = []
        mags_dict = {}
        for field in fields_evaluation_list:
            # create coordinates arrays
            id_list.append(field.fieldid)
            ra_rad_list.append(field.ra_rad)
            dec_rad_list.append(field.dec_rad)
        if len(id_list) > 0:
            self.sky.update(timestamp)
            sky_mags = self.sky.get_sky_brightness(ra_rad_list, dec_rad_list)
            for ix, fieldid in enumerate(id_list):
                mags_dict[fieldid] = sky_mags[ix]

        # compute target value
        for field in fields_evaluation_list:
            fieldid = field.fieldid

            # discard fields beyond airmass limit
#            airmass = airmass(field)
#            if airmass > self.params.max_airmass:
#                continue

            for filter in self.filters_tonight_list:

                target = self.targets_dict[fieldid][filter]
                # discard target if consecutive
                if self.last_observation_was_for_this_proposal:
                    if (self.observation_fulfills_target(self.last_observation, target) and
                       not self.params.accept_consecutive_visits):
                        continue

                # discard target beyond seeing limit
#                if seeing(filter) > self.params.max_seeing[filter]:
#                    continue

                # discard target beyond sky brightness limit
                sky_brightness = mags_dict[fieldid][filter]
                if sky_brightness > self.params.filter_max_brig_dict[filter]:
                    continue

                # target is accepted
                # compute value for available targets
                target.sky_brightness = sky_brightness

                need_ratio = (1 - target.progress) / (1 - self.total_progress)

#                airmass_bonus = self.params.ka / airmass
#                brightness_bonus = self.params.kb / sky_brightness

                target.value = need_ratio

                self.add_evaluated_target(target)

        return self.get_evaluated_target_list()

    def clear_evaluated_target_list(self):

        self.targets_heap = []

    def add_evaluated_target(self, target):

        heapq.heappush(self.targets_heap, (-target.value, target))

    def get_evaluated_target_list(self):

        self.winners_list = []
        for ix in range(min(len(self.targets_heap), self.params.max_num_targets)):
            self.winners_list.append(heapq.heappop(self.targets_heap)[1])

        self.losers_list = []
        for ix in range(len(self.targets_heap)):
            self.losers_list.append(heapq.heappop(self.targets_heap)[1])

        return self.winners_list

    def register_observation(self, observation):

        self.last_observation = observation
        tfound = None
        for target in self.winners_list:
            if self.observation_fulfills_target(observation, target):
                tfound = target
                break
        if (tfound is None) and self.params.accept_serendipity:
            for target in self.losers_list:
                if self.observation_fulfills_target(observation, target):
                    tfound = target
                    break

        if tfound is not None:
            target = self.targets_dict[observation.fieldid][observation.filter]
            target.visits += 1
            target.progress = target.visits / target.goal
            self.total_visits += 1
            self.total_progress = self.total_visits / self.total_goal
            self.last_observation_was_for_this_proposal = True
        else:
            self.last_observation_was_for_this_proposal = False

    def observation_fulfills_target(self, observ, target):

        return (observ.fieldid == target.fieldid) and (observ.filter == target.filter)
