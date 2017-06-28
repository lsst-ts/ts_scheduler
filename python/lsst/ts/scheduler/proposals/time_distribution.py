import math
import numpy

from operator import itemgetter

from lsst.ts.scheduler.setup import EXTENSIVE
from lsst.ts.scheduler.kernel import Field
from lsst.ts.scheduler.proposals import Proposal
from lsst.ts.scheduler.proposals.sequence import Sequence

class TimeDistributionProposalParameters(object):

    def __init__(self, confdict):

        self.sky_region = confdict["sky_region"]
        self.sky_exclusions = confdict["sky_exclusions"]
        self.sky_nightly_bounds = confdict["sky_nightly_bounds"]

        self.max_airmass = confdict["constraints"]["max_airmass"]
        self.max_cloud = confdict["constraints"]["max_cloud"]
        max_zd_rad = math.acos(1 / self.max_airmass)
        self.min_alt_rad = math.pi / 2 - max_zd_rad
        self.min_distance_moon_rad = math.radians(confdict["constraints"]["min_distance_moon"])
        self.exclude_planets = confdict["constraints"]["exclude_planets"]

        self.max_num_targets = int(confdict["scheduling"]["max_num_targets"])
        self.accept_serendipity = confdict["scheduling"]["accept_serendipity"]
        self.accept_consecutive_visits = confdict["scheduling"]["accept_consecutive_visits"]
        self.restart_lost_sequences = confdict["scheduling"]["restart_lost_sequences"]
        self.restart_complete_sequences = confdict["scheduling"]["restart_complete_sequences"]
        self.airmass_bonus = confdict["scheduling"]["airmass_bonus"]
        self.hour_angle_bonus = confdict["scheduling"]["hour_angle_bonus"]
        self.hour_angle_max_rad = math.radians(confdict["scheduling"]["hour_angle_max"] * 15.0)

        self.filter_list = []
        self.filter_min_brig_dict = {}
        self.filter_max_brig_dict = {}
        self.filter_max_seeing_dict = {}
        self.filter_num_exp_dict = {}
        self.filter_exp_times_dict = {}
        self.filters = ["u", "g", "r", "i", "z", "y"]
        for filter in self.filters:
            filter_section = "filter_%s" % filter
            if filter_section in confdict:
                self.filter_list.append(filter)
                self.filter_min_brig_dict[filter] = confdict[filter_section]["min_brig"]
                self.filter_max_brig_dict[filter] = confdict[filter_section]["max_brig"]
                self.filter_max_seeing_dict[filter] = confdict[filter_section]["max_seeing"]
                self.filter_exp_times_dict[filter] = confdict[filter_section]["exp_times"]
                self.filter_num_exp_dict[filter] = len(self.filter_exp_times_dict[filter])

        self.subsequence_filter_list = {}
        self.subsequence_visits_list = {}
        self.subsequence_num_events = {}
        self.subsequence_num_max_missed = {}
        self.subsequence_time_interval = {}
        self.subsequence_time_window_start = {}
        self.subsequence_time_window_max = {}
        self.subsequence_time_window_end = {}
        self.subsequence_name_list = confdict["subsequences"]["names"]
        for name in self.subsequence_name_list:
            sname = "subseq_" + name
            self.subsequence_num_events[name] = confdict[sname]["num_events"]
            self.subsequence_num_max_missed[name] = confdict[sname]["num_max_missed"]
            self.subsequence_time_interval[name] = confdict[sname]["time_interval"]
            self.subsequence_time_window_start[name] = confdict[sname]["time_window_start"]
            self.subsequence_time_window_max[name] = confdict[sname]["time_window_max"]
            self.subsequence_time_window_end[name] = confdict[sname]["time_window_end"]
            self.subsequence_filter_list[name] = confdict[sname]["filters"]
            self.subsequence_visits_list[name] = confdict[sname]["visits_per_filter"]

    @property
    def min_alt(self):
        return math.degrees(self.min_alt_rad)

class TimeDistributionProposal(Proposal):

    def __init__(self, propid, name, confdict, skymodel):

        Proposal.__init__(self, propid, name, confdict, skymodel)

        self.params = TimeDistributionProposalParameters(self.proposal_confdict)
        self.sky.configure(self.params.exclude_planets)

        # cummulative data for the survey
        self.survey_fields = 0
        self.survey_fields_dict = {}
        self.survey_sequences = 0
        self.survey_sequences_dict = {}
        self.survey_targets_goal = 0
        self.survey_targets_visits = 0
        self.survey_targets_progress = 0.0
        self.survey_filters_goal_dict = {}
        self.survey_filters_visits_dict = {}
        self.survey_filters_progress_dict = {}
        for filter in self.params.filter_list:
            self.survey_filters_goal_dict[filter] = 0
            self.survey_filters_visits_dict[filter] = 0
            self.survey_filters_progress_dict[filter] = 0.0

        # cummulative data for one night
        self.tonight_filters_list = []
        self.tonight_fields = 0
        self.tonight_fields_list = []
        self.tonight_fieldid_list = []
        self.tonight_sequences = 0
        self.tonight_sequences_dict = {}

        # data for one visit
        self.valued_targets_list = []
        self.last_observation = None
        self.last_observation_was_for_this_proposal = False
        self.in_deep_drilling = False

    def start_survey(self):

        Proposal.start_survey(self)

    def start_night(self, timestamp, filters_mounted_tonight_list, night):

        Proposal.start_night(self, timestamp, filters_mounted_tonight_list, night)

        self.tonight_filters_list = []
        self.tonight_targets = 0
        self.tonight_sequences_dict = {}
        for filter in filters_mounted_tonight_list:
            self.tonight_filters_list.append(filter)
        self.build_tonight_fields_list(timestamp, night)
        self.tonight_fields = len(self.tonight_fields_list)

        # compute at start night
        for field in self.tonight_fields_list:
            fieldid = field.fieldid

            # add new fields to fields dictionary
            if fieldid not in self.survey_fields_dict:
                self.survey_fields_dict[fieldid] = field.get_copy()
                self.survey_fields += 1

            # add new fields to sequences dictionary
            if fieldid not in self.survey_sequences_dict:
                sequence = self.create_sequence(field)
                self.survey_sequences_dict[fieldid] = sequence
                self.survey_sequences += 1
                self.survey_targets_goal += sequence.goal
                for filter in sequence.filters_goal_dict:
                    self.survey_filters_goal_dict[filter] += sequence.filters_goal_dict[filter]
            else:
                sequence = self.survey_sequences_dict[fieldid]
            if sequence.is_idle_or_active():
                self.tonight_sequences_dict[fieldid] = sequence
                self.tonight_sequences += 1

        for filter in self.params.filter_list:
            if self.survey_filters_goal_dict[filter] > 0:
                self.survey_filters_progress_dict[filter] = \
                    float(self.survey_filters_visits_dict[filter]) / self.survey_filters_goal_dict[filter]
            else:
                self.survey_filters_progress_dict[filter] = 0.0

        if self.survey_targets_goal > 0:
            self.survey_targets_progress = float(self.survey_targets_visits) / self.survey_targets_goal
        else:
            self.survey_targets_progress = 0.0

        self.log.debug("start_night tonight fields=%i sequences=%i" %
                       (self.tonight_fields, self.tonight_sequences))

        self.last_observation = None
        self.last_observation_was_for_this_proposal = False
        self.in_deep_drilling = False

    def end_night(self, timestamp):

        Proposal.end_night(self, timestamp)

        if self.in_deep_drilling:
            fieldid = self.last_observation.fieldid
            sequence = self.tonight_sequences_dict[fieldid]
            ssname = self.last_observation.subsequencename
            sequence.miss_observation_subsequence(ssname, timestamp)
            self.log.debug("end_night: miss observation field=%i, ssname=%s" % (fieldid, ssname))
            self.evaluate_sequence_continuation(fieldid, "end of night")
            self.in_deep_drilling = False

        self.log.info("end_night survey fields=%i sequences=%i goal=%i visits=%i progress=%.2f%%" %
                      (self.survey_fields, self.survey_sequences,
                       self.survey_targets_goal, self.survey_targets_visits,
                       100 * self.survey_targets_progress))

    def build_tonight_fields_list(self, timestamp, night):

        self.tonight_fields_list = []
        self.tonight_fieldid_list = []

        sql = self.select_fields(timestamp, night, self.params.sky_region, self.params.sky_exclusions,
                                 self.params.sky_nightly_bounds)

        res = self.db.query(sql)

        for row in res:
            field = Field.from_db_row(row)
            self.tonight_fields_list.append(field)
            self.tonight_fieldid_list.append(field.fieldid)

        return

    def get_progress(self):

        return self.survey_targets_progress

    def get_filter_visits(self, filter):

        if filter in self.survey_filters_visits_dict:
            return self.survey_filters_visits_dict[filter]
        else:
            return 0

    def get_filter_goal(self, filter):

        if filter in self.survey_filters_goal_dict:
            return self.survey_filters_goal_dict[filter]
        else:
            return 0

    def get_filter_progress(self, filter):

        if filter in self.survey_filters_progress_dict:
            return self.survey_filters_progress_dict[filter]
        else:
            return 0.0

    def suggest_targets(self, timestamp, deepdrilling_target, constrained_filter, cloud, seeing):

        Proposal.suggest_targets(self, timestamp)

        if self.ignore_clouds:
            cloud = 0.0
        if self.ignore_seeing:
            seeing = 0.0

        if cloud > self.params.max_cloud:
            self.log.debug("suggest_targets: cloud=%.2f > max_cloud=%.2f" % (cloud, self.params.max_cloud))
            return []

        self.clear_evaluated_target_list()

        # evaluates previous deep drilling state with new target
        if self.in_deep_drilling:
            if deepdrilling_target is None:
                # deep drilling event interrupted
                fieldid = self.last_observation.fieldid
                sequence = self.tonight_sequences_dict[fieldid]
                ssname = self.last_observation.subsequencename
                sequence.miss_observation_subsequence(ssname, timestamp)
                self.log.debug("suggest_observation: miss observation field=%i, ssname=%s" %
                               (fieldid, ssname))
                self.evaluate_sequence_continuation(fieldid, "interrupted")
                fields_evaluation_list = self.tonight_fields_list
                num_targets_to_propose = self.params.max_num_targets
                self.in_deep_drilling = False
            else:
                if self.observation_fulfills_target(deepdrilling_target, self.last_observation):
                    # deep drilling event continues
                    fields_evaluation_list = [self.survey_fields_dict[deepdrilling_target.fieldid]]
                    num_targets_to_propose = 1
                else:
                    # deep drilling event is not for this proposal
                    # deep drilling event interrupted
                    fieldid = self.last_observation.fieldid
                    sequence = self.tonight_sequences_dict[fieldid]
                    ssname = self.last_observation.subsequencename
                    sequence.miss_observation_subsequence(ssname, timestamp)
                    self.log.debug("suggest_observation: miss observation field=%i, ssname=%s" %
                                   (fieldid, ssname))
                    self.evaluate_sequence_continuation(fieldid, "interrupted")
                    fields_evaluation_list = self.tonight_fields_list
                    num_targets_to_propose = self.params.max_num_targets
                    self.in_deep_drilling = False
        else:
            if deepdrilling_target is None:
                fields_evaluation_list = self.tonight_fields_list
                num_targets_to_propose = self.params.max_num_targets
            else:
                if deepdrilling_target.fieldid in self.tonight_fieldid_list:
                    fields_evaluation_list = [self.survey_fields_dict[deepdrilling_target.fieldid]]
                    if self.propid in deepdrilling_target.propid_list:
                        # deep drilling event starts
                        num_targets_to_propose = 1
                        self.in_deep_drilling = True
                    else:
                        #  deep drilling event is not for this proposal
                        num_targets_to_propose = 0
                else:
                    fields_evaluation_list = []
                    num_targets_to_propose = 0

        if constrained_filter is None:
            filters_evaluation_list = self.tonight_filters_list
        else:
            filters_evaluation_list = [constrained_filter]

        # compute sky brightness for all targets
        id_list = []
        ra_rad_list = []
        dec_rad_list = []
        mags_dict = {}
        airmass_dict = {}
        hour_angle_dict = {}
        moon_distance_dict = {}
        for field in fields_evaluation_list:
            # create coordinates arrays
            id_list.append(field.fieldid)
            ra_rad_list.append(field.ra_rad)
            dec_rad_list.append(field.dec_rad)
        if (len(id_list) > 0) and (not self.ignore_sky_brightness or not self.ignore_airmass):
            self.sky.update(timestamp)
            sky_mags = self.sky.get_sky_brightness(numpy.array(id_list))
            airmass = self.sky.get_airmass(numpy.array(id_list))
            nra = numpy.array(ra_rad_list)
            moon_distance = self.sky.get_separation("moon", nra,
                                                    numpy.array(dec_rad_list))
            hour_angle = self.sky.get_hour_angle(nra)
            for ix, fieldid in enumerate(id_list):
                mags_dict[fieldid] = {k: v[ix] for k, v in sky_mags.items()}
                airmass_dict[fieldid] = airmass[ix]
                moon_distance_dict[fieldid] = moon_distance[ix]
                hour_angle_dict[fieldid] = hour_angle[ix]

        if self.in_deep_drilling:
            fieldid = deepdrilling_target.fieldid
            sequence = self.tonight_sequences_dict[fieldid]
            target = sequence.get_next_target_subsequence(deepdrilling_target.subsequencename)
            filter = target.filter

            if self.ignore_airmass:
                airmass = 1.0
            else:
                airmass = airmass_dict[fieldid]
            if self.ignore_sky_brightness:
                sky_brightness = 0.0
            else:
                sky_brightness = mags_dict[fieldid][filter]
                if math.isnan(sky_brightness):
                    sky_brightness = 0.0

            target.time = timestamp
            target.airmass = airmass
            target.sky_brightness = sky_brightness
            target.cloud = cloud
            target.seeing = seeing

            target.need = 1.0
            target.bonus = 0.0
            target.value = target.need + target.bonus
            self.add_evaluated_target(target)

            self.log.log(EXTENSIVE, "suggest_targets: in deep drilling")

            return self.get_evaluated_target_list(1)

        evaluated_fields = 0
        discarded_fields_airmass = 0
        discarded_fields_notargets = 0
        discarded_targets_consecutive = 0
        discarded_targets_nanbrightness = 0
        discarded_targets_lowbrightness = 0
        discarded_targets_highbrightness = 0
        discarded_targets_seeing = 0
        discarded_moon_distance = 0
        evaluated_targets = 0
        missed_subsequences_list = []

        # compute target value
        for field in fields_evaluation_list:
            fieldid = field.fieldid

            # discard fields with no more targets tonight
            if fieldid not in self.tonight_sequences_dict:
                discarded_fields_notargets += 1
                continue

            sequence = self.tonight_sequences_dict[fieldid]

            # discard fields beyond airmass limit
            if self.ignore_airmass:
                airmass = 1.0
            else:
                airmass = airmass_dict[fieldid]
                if airmass > self.params.max_airmass:
                    discarded_fields_airmass += 1
                    continue

            moon_distance = moon_distance_dict[fieldid]
            if moon_distance < self.params.min_distance_moon_rad:
                discarded_moon_distance += 1
                continue

            airmass_rank = self.params.airmass_bonus * \
                (self.params.max_airmass - airmass) / (self.params.max_airmass - 1.0)

            hour_angle_rank = self.params.hour_angle_bonus * \
                (1.0 - numpy.abs(hour_angle_dict[fieldid]) / self.params.hour_angle_max_rad)

            for name in sequence.enabled_subsequences_list:
                target = sequence.get_next_target_subsequence(name)
                filter = target.filter

                if filter not in filters_evaluation_list:
                    continue

                # discard target beyond seeing limit
                if seeing > self.params.filter_max_seeing_dict[filter]:
                    discarded_targets_seeing += 1
                    continue

                target.time = timestamp
                target.airmass = airmass
                # discard target if consecutive
                if self.last_observation_was_for_this_proposal:
                    if (self.observation_fulfills_target(self.last_observation, target) and
                            not self.params.accept_consecutive_visits):
                        discarded_targets_consecutive += 1
                        continue

                if self.ignore_sky_brightness:
                    sky_brightness = 0.0
                else:
                    # discard target beyond sky brightness limits
                    sky_brightness = mags_dict[fieldid][filter]
                    if math.isnan(sky_brightness):
                        discarded_targets_nanbrightness += 1
                        continue

                    if sky_brightness < self.params.filter_min_brig_dict[filter]:
                        discarded_targets_lowbrightness += 1
                        continue

                    if sky_brightness > self.params.filter_max_brig_dict[filter]:
                        discarded_targets_highbrightness += 1
                        continue

                # target is accepted
                # compute value for available targets
                target.sky_brightness = sky_brightness
                target.cloud = cloud
                target.seeing = seeing

                time_rank = sequence.time_window_subsequence(name, timestamp)
                need_ratio = time_rank

                if need_ratio > 0.0:
                    # target is needed
                    target.need = need_ratio
                    target.bonus = airmass_rank + hour_angle_rank
                    target.value = target.need + target.bonus

                    self.add_evaluated_target(target)
                elif need_ratio < 0.0:
                    # subsequence event missed
                    missed_subsequences_list.append((fieldid, name))

                evaluated_targets += 1
            evaluated_fields += 1

        for (fieldid, name) in missed_subsequences_list:
            self.survey_sequences_dict[fieldid].miss_observation_subsequence(name, timestamp)
            self.log.debug("suggest_targets: miss observation field=%i, ssname=%s" % (fieldid, name))
            self.evaluate_sequence_continuation(fieldid, "missed observation")

        self.log.log(EXTENSIVE, "suggest_targets: fields=%i, evaluated=%i, "
                     "discarded airmass=%i notargets=%i" %
                     (len(id_list), evaluated_fields,
                      discarded_fields_airmass, discarded_fields_notargets))
        self.log.log(EXTENSIVE, "suggest_targets: evaluated targets=%i, discarded consecutive=%i "
                     "seeing=%i "
                     "lowbright=%i highbright=%i nanbright=%i moondistance=%i" %
                     (evaluated_targets, discarded_targets_consecutive,
                      discarded_targets_seeing,
                      discarded_targets_lowbrightness, discarded_targets_highbrightness,
                      discarded_targets_nanbrightness, discarded_moon_distance))

        return self.get_evaluated_target_list(num_targets_to_propose)

    def clear_evaluated_target_list(self):

        self.valued_targets_list = []

    def add_evaluated_target(self, target):

        self.valued_targets_list.append((-target.value, target))

    def get_evaluated_target_list(self, num_targets_to_propose):

        sorted_list = sorted(self.valued_targets_list, key=itemgetter(0))

        self.winners_list = []
        for ix in range(min(len(sorted_list), num_targets_to_propose)):
            self.winners_list.append(sorted_list.pop(0)[1])

        self.losers_list = []
        for ix in range(len(sorted_list)):
            self.losers_list.append(sorted_list.pop(0)[1])

        return self.winners_list

    def register_observation(self, observation):

        self.last_observation = observation.get_copy()
        self.last_observation_was_for_this_proposal = False

        if self.propid not in observation.propid_list and not self.params.accept_serendipity:
            return None

        fieldid = observation.fieldid
        filter = observation.filter

        tfound = None
        for target in self.winners_list:
            if self.observation_fulfills_target(observation, target):
                tfound = target
                break
        if tfound is None:
            for target in self.losers_list:
                if self.observation_fulfills_target(observation, target):
                    tfound = target
                    break

        if tfound is not None:
            self.log.log(EXTENSIVE, "register_observation: %s" % (target))

            self.survey_sequences_dict[fieldid].register_observation(observation)
            self.evaluate_sequence_continuation(fieldid, "new observation")
            self.in_deep_drilling = self.survey_sequences_dict[fieldid].is_in_deep_drilling()

            self.survey_targets_visits += 1
            if self.survey_targets_goal > 0:
                self.survey_targets_progress = float(self.survey_targets_visits) / self.survey_targets_goal
            else:
                self.survey_targets_progress = 0.0
            self.survey_filters_visits_dict[filter] += 1
            if self.survey_filters_goal_dict[filter] > 0:
                self.survey_filters_progress_dict[filter] = \
                    float(self.survey_filters_visits_dict[filter]) / self.survey_filters_goal_dict[filter]
            else:
                self.survey_filters_progress_dict[filter] = 0.0

            self.last_observation_was_for_this_proposal = True

        return tfound

    def observation_fulfills_target(self, observ, target):

        return (observ.fieldid == target.fieldid) and (observ.filter == target.filter)

    def evaluate_sequence_continuation(self, fieldid, text):

        previous_goal = self.survey_sequences_dict[fieldid].goal
        if self.survey_sequences_dict[fieldid].is_lost():
            self.log.debug("evaluate_sequence_continuation: sequence LOST field=%i %s" % (fieldid, text))
            if self.params.restart_lost_sequences:
                self.survey_sequences_dict[fieldid].restart()
                self.log.debug("evaluate_sequence_continuation: sequence RESTARTED field=%i" % (fieldid))
            else:
                self.remove_sequence(fieldid)
        elif self.survey_sequences_dict[fieldid].is_complete():
            self.log.debug("evaluate_sequence_continuation: sequence COMPLETE field=%i %s" % (fieldid, text))
            if self.params.restart_complete_sequences:
                self.survey_sequences_dict[fieldid].restart()
                self.log.debug("evaluate_sequence_continuation: sequence RESTARTED field=%i" % (fieldid))
            else:
                self.remove_sequence(fieldid)
        delta_goal = self.survey_sequences_dict[fieldid].goal - previous_goal

        if delta_goal > 0:
            # sequence was restarted and new goal of visits has increased
            self.survey_targets_goal += delta_goal
            self.survey_targets_progress = float(self.survey_targets_visits) / self.survey_targets_goal

    def remove_sequence(self, fieldid):

        del self.tonight_sequences_dict[fieldid]
        self.tonight_sequences -= 1
        for field in self.tonight_fields_list:
            if field.fieldid == fieldid:
                self.tonight_fields_list.remove(field)
                break
        self.tonight_fieldid_list.remove(fieldid)

    def create_sequence(self, field):

        sequence = Sequence(self.propid, field, self.params)

        return sequence
