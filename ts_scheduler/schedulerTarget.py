import math

from ts_scheduler.schedulerDefinitions import RAD2DEG

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

        self.time = 0.0
        self.airmass = 0.0
        self.sky_brightness = 0.0

        self.value = 0.0

        self.slewtime = 0.0
        self.cost_bonus = 0.0
        self.rank = 0.0

        self.num_props = 0
        self.propid_list = []
        self.propvalue_list = []

        #internal book-keeping
        self.goal = 0
        self.visits = 0
        self.progress = 0.0

    def __str__(self):
        return ("targetid=%d field=%d filter=%s exp_times=%s ra=%.3f dec=%.3f "
                "time=%.1f airmass=%.3f brightness=%.3f "
                "progress=%.3f value=%.3f slewtime=%.3f cost=%.3f rank=%.3f propid=%s" %
                (self.targetid, self.fieldid, self.filter, str(self.exp_times),
                 self.ra_rad * RAD2DEG, self.dec_rad * RAD2DEG,
                 self.time, self.airmass, self.sky_brightness,
                 self.progress, self.value, self.slewtime, self.cost_bonus, self.rank, self.propid_list))

    @classmethod
    def from_topic(cls, topic):
        """Alternate initializer.

        Parameters
        ----------
        topic : SALPY_scheduler.targetTestC
            The target topic instance.

        Returns
        -------
        schedulerTarget.Target
        """
        return cls(topic.targetId, topic.fieldId, topic.filter, math.radians(topic.ra),
                   math.radians(topic.dec), math.radians(topic.angle), topic.num_exposures,
                   topic.exposure_times)
