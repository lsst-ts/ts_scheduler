from lsst.ts.scheduler.kernel import Target

SEQ_IDLE = 0
SEQ_ACTIVE = 1
SEQ_COMPLETE = 2
SEQ_LOST = 3

class Subsequence(object):

    def __init__(self, propid, field, name, params):

        self.propid = propid
        self.field = field
        self.name = name

        self.num_events = params.subsequence_num_events[name]
        self.num_max_missed = params.subsequence_num_max_missed[name]
        self.time_interval = params.subsequence_time_interval[name]
        self.time_window_start = params.subsequence_time_window_start[name]
        self.time_window_max = params.subsequence_time_window_max[name]
        self.time_window_end = params.subsequence_time_window_end[name]
        self.filter_list = params.subsequence_filter_list[name]
        self.visits_list = params.subsequence_visits_list[name]
        self.filter_num_exp_dict = dict(params.filter_num_exp_dict)
        self.filter_exp_times_dict = dict(params.filter_exp_times_dict)

        self.num_visits_per_event = 0
        self.filters_goal_dict = {}

        self.dd_exposures = 0
        self.dd_exptime = 0.0
        self.num_subevents = len(self.filter_list)
        for ix, filter in enumerate(self.filter_list):
            if filter not in self.filters_goal_dict:
                self.filters_goal_dict[filter] = 0
            self.filters_goal_dict[filter] += self.num_events * self.visits_list[ix]
            self.num_visits_per_event += self.visits_list[ix]
            self.dd_exposures += self.visits_list[ix] * self.filter_num_exp_dict[filter]
            self.dd_exptime += self.visits_list[ix] * sum(self.filter_exp_times_dict[filter])
        self.goal = self.num_events * self.num_visits_per_event

        if (len(self.visits_list) > 1) or (self.visits_list[0] > 1):
            self.is_deep_drilling = True
            self.dd_visits = self.num_visits_per_event
            self.dd_filterchanges = max(len(self.filter_list) - 1, 0)
        else:
            self.is_deep_drilling = False
            self.dd_visits = 0
            self.dd_filterchanges = 0

        self.subevent_index = 0
        self.subevent_num_visits_left = self.visits_list[0]
        self.event_visits_list = []
        self.all_events_list = []
        self.obs_events_list = []
        self.mis_events_list = []

        self.target = Target()
        self.target.fieldid = field.fieldid
        self.target.filter = self.filter_list[self.subevent_index]
        self.target.num_exp = self.filter_num_exp_dict[self.target.filter]
        self.target.exp_times = self.filter_exp_times_dict[self.target.filter]
        self.target.ra_rad = field.ra_rad
        self.target.dec_rad = field.dec_rad
        self.target.propid = self.propid
        self.target.goal = self.goal
        self.target.visits = 0
        self.target.progress = 0.0

        self.target.sequenceid = self.field.fieldid
        self.target.subsequencename = self.name
        self.target.groupid = 1
        self.target.groupix = 1
        self.target.is_deep_drilling = self.is_deep_drilling
        self.target.is_dd_firstvisit = self.is_deep_drilling
        self.target.remaining_dd_visits = self.dd_visits
        self.target.dd_exposures = self.dd_exposures
        self.target.dd_filterchanges = self.dd_filterchanges
        self.target.dd_exptime = self.dd_exptime

        self.update_state()

    def update_state(self):

        self.num_all_events = len(self.all_events_list)
        self.num_obs_events = len(self.obs_events_list)
        self.num_mis_events = len(self.mis_events_list)

        if self.num_all_events == 0:
            self.state = SEQ_IDLE

        elif self.num_mis_events > self.num_max_missed:
            self.state = SEQ_LOST

        elif self.num_all_events >= self.num_events:
            self.state = SEQ_COMPLETE
        else:
            self.state = SEQ_ACTIVE

    def is_idle(self):

        return self.state == SEQ_IDLE

    def is_active(self):

        return self.state == SEQ_ACTIVE

    def is_idle_or_active(self):

        return (self.state == SEQ_IDLE) or (self.state == SEQ_ACTIVE)

    def is_complete(self):

        return self.state == SEQ_COMPLETE

    def is_lost(self):

        return self.state == SEQ_LOST

    def get_next_target(self):

        self.target.filter = self.filter_list[self.subevent_index]
        self.target.num_exp = self.filter_num_exp_dict[self.target.filter]
        self.target.exp_times = self.filter_exp_times_dict[self.target.filter]
        self.target.groupid = self.num_all_events + 1
        self.target.groupix = self.subevent_index + 1

        return self.target

    def time_window(self, time):

        if self.state == SEQ_IDLE:
            need = 0.1
        else:
            deltaT = time - self.all_events_list[-1]
            ndeltaT = deltaT / self.time_interval
            if ndeltaT < self.time_window_start:
                need = 0.0
            elif ndeltaT < self.time_window_max:
                need = (ndeltaT - self.time_window_start) /\
                       (self.time_window_max - self.time_window_start)
            elif ndeltaT < self.time_window_end:
                need = 1.0
            else:
                need = -1.0

        return need

    def miss_observation(self, time):

        # miss event
        self.all_events_list.append(time)
        self.mis_events_list.append(time)

        # update state
        self.update_state()
        if not self.is_lost():
            if self.is_deep_drilling:
                self.target.visits += self.target.remaining_dd_visits
            else:
                self.target.visits += 1
            self.target.progress = float(self.target.visits) / self.target.goal

        # reset to first subevent
        self.subevent_index = 0
        self.subevent_num_visits_left = self.visits_list[0]
        self.event_visits_list = []
        if self.is_deep_drilling:
            self.target.is_dd_firstvisit = True
            self.target.remaining_dd_visits = self.dd_visits

    def register_observation(self, time):

        self.event_visits_list.append(time)
        self.subevent_num_visits_left -= 1
        self.target.remaining_dd_visits -= 1
        self.target.is_dd_firstvisit = False
        self.target.visits += 1
        self.target.progress = float(self.target.visits) / self.target.goal
        if self.subevent_num_visits_left == 0:
            # subevent is complete
            if self.subevent_index == (self.num_subevents - 1):
                # event is complete
                # observation is recorded with first visit timestamp
                self.all_events_list.append(self.event_visits_list[0])
                self.obs_events_list.append(self.event_visits_list[0])
                # reset to first subevent
                self.subevent_index = 0
                self.subevent_num_visits_left = self.visits_list[0]
                self.event_visits_list = []
                if self.is_deep_drilling:
                    self.target.is_dd_firstvisit = True
                self.target.remaining_dd_visits = self.dd_visits
            else:
                # advance to next subevent
                self.subevent_index += 1
                self.subevent_num_visits_left = self.visits_list[self.subevent_index]

        self.update_state()
