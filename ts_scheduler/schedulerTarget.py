import math

class Target(object):
    def __init__(self,
                 targetid=0,
                 fieldid=0,
                 filter="",
                 ra_rad=0.0,
                 dec_rad=0.0,
                 ang_rad=0.0,
                 num_exp=0,
                 exp_times=[]):

        self.targetid = targetid
        self.fieldid = fieldid
        self.filter = filter
        self.ra_rad = ra_rad
        self.dec_rad = dec_rad
        self.ang_rad = ang_rad
        self.num_exp = num_exp
        self.exp_times = list(exp_times)

        #conditions
        self.time = 0.0
        self.airmass = 0.0
        self.sky_brightness = 0.0

        #computed at proposal
        self.propid = 0
        self.need = 0.0
        self.bonus = 0.0
        self.value = 0.0
        #internal proposal book-keeping
        self.goal = 0
        self.visits = 0
        self.progress = 0.0

        #computed at driver
        self.propboost = 1.0
        self.slewtime = 0.0
        self.cost_bonus = 0.0
        self.rank = 0.0
        #assembled at driver
        self.num_props = 0
        self.propid_list = []
        self.need_list = []
        self.bonus_list = []
        self.value_list = []
        self.propboost_list = []

    def __str__(self):
        return ("targetid=%d field=%d filter=%s exp_times=%s ra=%.3f dec=%.3f "
                "time=%.1f airmass=%.3f brightness=%.3f "
                "visits=%i progress=%.3f "
                "need=%.3f bonus=%.3f value=%.3f "
                "propid=%s need=%s bonus=%s value=%s "
                "slewtime=%.3f costbonus=%.3f rank=%.3f" %
                (self.targetid, self.fieldid, self.filter, str(self.exp_times),
                 self.ra, self.dec,
                 self.time, self.airmass, self.sky_brightness,
                 self.visits, self.progress,
                 self.need, self.bonus, self.value,
                 self.propid_list, self.need_list, self.bonus_list, self.value_list,
                 self.slewtime, self.cost_bonus, self.rank))

    @property
    def ra(self):
        return math.degrees(self.ra_rad)

    @property
    def dec(self):
        return math.degrees(self.dec_rad)

    @property
    def ang(self):
        return math.degrees(self.ang_rad)

    @classmethod
    def from_topic(cls, topic):
        """Alternate initializer.

        Parameters
        ----------
        topic : SALPY_scheduler.targetC
            The target topic instance.

        Returns
        -------
        schedulerTarget.Target
        """
        return cls(topic.targetId, topic.fieldId, topic.filter, math.radians(topic.ra),
                   math.radians(topic.dec), math.radians(topic.angle), topic.num_exposures,
                   topic.exposure_times)
