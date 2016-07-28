import copy
import math

from operator import itemgetter

from ts_scheduler.proposal import Proposal
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target

class AreaDistributionProposalParameters(object):

    def __init__(self, confdict):

        self.sky_region = confdict["sky_region"]
        self.sky_exclusions = confdict["sky_exclusions"]
        self.sky_nightly_bounds = confdict["sky_nightly_bounds"]

        self.max_airmass = confdict["constraints"]["max_airmass"]
        max_zd_rad = math.acos(1 / self.max_airmass)
        self.min_alt_rad = math.pi / 2 - max_zd_rad

        self.max_num_targets = int(confdict["scheduling"]["max_num_targets"])
        self.accept_serendipity = confdict["scheduling"]["accept_serendipity"]
        self.accept_consecutive_visits = confdict["scheduling"]["accept_consecutive_visits"]

        self.filter_list = []
        self.filter_visits_dict = {}
        self.filter_min_brig_dict = {}
        self.filter_max_brig_dict = {}
        self.filter_max_seeing_dict = {}
        self.filter_num_exp_dict = {}
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
                self.filter_num_exp_dict[filter] = len(self.filter_exp_times_dict[filter])

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
        self.valued_targets_list = []

        self.last_observation = None
        self.last_observation_was_for_this_proposal = False

    def start_survey(self):

        super(AreaDistributionProposal, self).start_survey()

    def start_night(self, timestamp, filters_mounted_tonight_list):

        super(AreaDistributionProposal, self).start_night(timestamp, filters_mounted_tonight_list)

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
                    target.num_exp = self.params.filter_num_exp_dict[filter]
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

        sql = self.select_fields(timestamp, self.params.sky_region, self.params.sky_exclusions,
                                 self.params.sky_nightly_bounds)

        res = self.db.query(sql)

        for row in res:
            field = Field.from_db_row(row)
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
        airmass_dict = {}
        for field in fields_evaluation_list:
            # create coordinates arrays
            id_list.append(field.fieldid)
            ra_rad_list.append(field.ra_rad)
            dec_rad_list.append(field.dec_rad)
        if len(id_list) > 0:
            self.sky.update(timestamp)
            sky_mags = self.sky.get_sky_brightness(ra_rad_list, dec_rad_list)
            attrs = self.sky.sky_brightness.getComputedVals()
            for ix, fieldid in enumerate(id_list):
                mags_dict[fieldid] = {k: v[ix] for k, v in sky_mags.items()}
                airmass_dict[fieldid] = attrs["airmass"][ix]

        evaluated_fields = 0
        discarded_fields_airmass = 0
        discarded_targets_consecutive = 0
        discarded_targets_lowbrightness = 0
        discarded_targets_highbrightness = 0
        evaluated_targets = 0
        # compute target value
        for field in fields_evaluation_list:
            fieldid = field.fieldid

            # discard fields beyond airmass limit
            airmass = airmass_dict[fieldid]
            if airmass > self.params.max_airmass:
                discarded_fields_airmass += 1
                continue

            for filter in self.filters_tonight_list:
                target = self.targets_dict[fieldid][filter]
                target.time = timestamp
                target.airmass = airmass
                # discard target if consecutive
                if self.last_observation_was_for_this_proposal:
                    if (self.observation_fulfills_target(self.last_observation, target) and
                       not self.params.accept_consecutive_visits):
                        discarded_targets_consecutive += 1
                        continue

                # discard target beyond seeing limit
#                if seeing(filter) > self.params.max_seeing[filter]:
#                    continue

                # discard target beyond sky brightness limits
                sky_brightness = mags_dict[fieldid][filter]
                if sky_brightness < self.params.filter_min_brig_dict[filter]:
                    discarded_targets_lowbrightness += 1
                    continue

                if sky_brightness > self.params.filter_max_brig_dict[filter]:
                    discarded_targets_highbrightness += 1
                    continue

                # target is accepted
                # compute value for available targets
                target.sky_brightness = sky_brightness

                need_ratio = (1 - target.progress) / (1 - self.total_progress)

#                airmass_bonus = self.params.ka / airmass
#                brightness_bonus = self.params.kb / sky_brightness

                target.value = need_ratio

                self.add_evaluated_target(target)
                evaluated_targets += 1
            evaluated_fields += 1

        self.log.debug("suggest_targets: fields=%d, evaluated=%d, discarded airmass=%d" %
                       (len(id_list), evaluated_fields, discarded_fields_airmass))
        self.log.debug("suggest_targets: evaluated targets=%d, discarded lowbright=%d highbright=%d" %
                       (evaluated_targets, discarded_targets_lowbrightness, discarded_targets_highbrightness))

        return self.get_evaluated_target_list()

    def clear_evaluated_target_list(self):

        self.valued_targets_list = []

    def add_evaluated_target(self, target):

        self.valued_targets_list.append((-target.value, target))

    def get_evaluated_target_list(self):

        sorted_list = sorted(self.valued_targets_list, key=itemgetter(0))

        self.winners_list = []
        for ix in range(min(len(sorted_list), self.params.max_num_targets)):
            self.winners_list.append(sorted_list.pop(0)[1])

        self.losers_list = []
        for ix in range(min(len(sorted_list), self.params.max_num_targets)):
            self.losers_list.append(sorted_list.pop(0)[1])

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
