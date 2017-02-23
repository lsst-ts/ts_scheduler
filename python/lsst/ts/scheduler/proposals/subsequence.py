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

        self.goal = self.num_events
        self.filters_goal_dict = {}

        filter = self.filter_list[0]
        self.filters_goal_dict[filter] = self.num_events

        self.target = Target()
        self.target.fieldid = field.fieldid
        self.target.filter = filter
        self.target.num_exp = self.filter_num_exp_dict[filter]
        self.target.exp_times = self.filter_exp_times_dict[filter]
        self.target.ra_rad = field.ra_rad
        self.target.dec_rad = field.dec_rad
        self.target.propid = self.propid
        self.target.goal = self.goal
        self.target.visits = 0
        self.target.progress = 0.0
        self.target.groupid = 1
        self.target.groupix = 1

        self.all_events_list = []
        self.obs_events_list = []
        self.mis_events_list = []

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

        self.target.filter = self.filter_list[0]
        self.target.num_exp = self.filter_num_exp_dict[self.target.filter]
        self.target.exp_times = self.filter_exp_times_dict[self.target.filter]

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

        self.all_events_list.append(time)
        self.mis_events_list.append(time)

        self.target.visits += 1
        self.target.progress = float(self.target.visits) / self.target.goal

        self.update_state()

    def register_observation(self, time):

        self.all_events_list.append(time)
        self.obs_events_list.append(time)

        self.target.visits += 1
        self.target.progress = float(self.target.visits) / self.target.goal

        self.update_state()
