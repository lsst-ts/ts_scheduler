from schedulerDefinitions import RAD2DEG

class Target(object):
    def __init__(self,
                 targetid=0,
                 fieldid=0,
                 filter="",
                 ra_rad=0.0,
                 dec_rad=0.0,
                 ang_rad=0.0,
                 numexp=0,
                 exptimes=[]):

        self.targetid = targetid
        self.fieldid = fieldid
        self.filter = filter
        self.ra_rad = ra_rad
        self.dec_rad = dec_rad
        self.ang_rad = ang_rad
        self.numexp = numexp
        self.exptimes = list(exptimes)

        self.time = 0.0
        self.skybrightness = 0.0

        self.propIds = []
        self.propValues = []
        self.value = 0.0
        self.cost = 0.0

    def __str__(self):
        return ("ID=%d field=%d filter=%s ra=%.3f dec=%.3f time=%.1f skybrightness=%.3f" %
                (self.targetid, self.fieldid, self.filter, self.ra_rad * RAD2DEG, self.dec_rad * RAD2DEG,
                 self.time, self.skybrightness))
