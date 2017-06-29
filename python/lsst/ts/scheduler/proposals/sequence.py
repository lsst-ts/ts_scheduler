from builtins import object
from lsst.ts.scheduler.proposals.subsequence import Subsequence

SEQ_IDLE = 0
SEQ_ACTIVE = 1
SEQ_COMPLETE = 2
SEQ_LOST = 3

class Sequence(object):

    def __init__(self, propid, field, params):

        self.propid = propid
        self.field = field.get_copy()
        self.subsequence_dict = {}
        self.enabled_subsequences_list = []
        self.subsequence_name_list = list(params.subsequence_name_list)
        self.goal = 0
        self.visits = 0
        self.progress = 0.0
        self.filters_goal_dict = {}
        for name in self.subsequence_name_list:
            subsequence = Subsequence(self.propid, self.field, name, params)
            self.subsequence_dict[name] = subsequence
            self.enabled_subsequences_list.append(name)
            self.goal += subsequence.goal
            for filter in subsequence.filters_goal_dict:
                if filter not in self.filters_goal_dict:
                    self.filters_goal_dict[filter] = 0
                self.filters_goal_dict[filter] += subsequence.filters_goal_dict[filter]

        self.update_state()

    def restart(self):

        self.enabled_subsequences_list = []
        for name in self.subsequence_name_list:
            subsequence = self.subsequence_dict[name]
            subsequence.restart()
            self.enabled_subsequences_list.append(name)
            self.goal += subsequence.goal
            for filter in subsequence.filters_goal_dict:
                self.filters_goal_dict[filter] += subsequence.filters_goal_dict[filter]

        self.update_state()

    def update_state(self):

        all_idle = True
        all_complete = True
        any_lost = False
        for name in self.subsequence_name_list:
            subsequence = self.subsequence_dict[name]
            if not subsequence.is_idle():
                all_idle = False
            if not subsequence.is_complete():
                all_complete = False
            if subsequence.is_lost():
                any_lost = True

        if any_lost:
            self.state = SEQ_LOST
        elif all_complete:
            self.state = SEQ_COMPLETE
        elif all_idle:
            self.state = SEQ_IDLE
        else:
            self.state = SEQ_ACTIVE

    def is_idle(self):

        return self.state == SEQ_IDLE

    def is_active(self):

        return self.state == SEQ_ACTIVE

    def is_in_deep_drilling(self):

        in_deep_drilling = False
        for name in self.subsequence_name_list:
            subsequence = self.subsequence_dict[name]
            if subsequence.is_in_deep_drilling():
                in_deep_drilling = True
                break

        return in_deep_drilling

    def is_idle_or_active(self):

        return (self.state == SEQ_IDLE) or (self.state == SEQ_ACTIVE)

    def is_complete(self):

        return self.state == SEQ_COMPLETE

    def is_lost(self):

        return self.state == SEQ_LOST

    def get_next_target_subsequence(self, name):

        return self.subsequence_dict[name].get_next_target()

    def time_window_subsequence(self, name, time):

        return self.subsequence_dict[name].time_window(time)

    def miss_observation_subsequence(self, name, time):

        self.subsequence_dict[name].miss_observation(time)
        if not self.subsequence_dict[name].is_idle_or_active():
            self.disable_subsequence(name)

        self.update_state()

    def register_observation(self, observation):

        for name in self.enabled_subsequences_list:
            subsequence = self.subsequence_dict[name]
            expected_target = subsequence.get_next_target()
            if expected_target.filter == observation.filter:
                self.subsequence_dict[name].register_observation(observation.time)
                if not self.subsequence_dict[name].is_idle_or_active():
                    self.disable_subsequence(name)
        self.update_state()

    def register_observation_subsequence(self, name, time):

        self.subsequence_dict[name].register_observation(time)
        if not self.subsequence_dict[name].is_idle_or_active():
            self.disable_subsequence(name)

        self.update_state()

    def disable_subsequence(self, name):
        if name in self.enabled_subsequences_list:
            self.enabled_subsequences_list.remove(name)
