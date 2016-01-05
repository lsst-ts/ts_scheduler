from schedulerDefinitions import RAD2DEG

class schedulerTarget(object):
    def __init__(self,
                 targetId=0,
                 fieldId=0,
                 filter="",
                 ra_RAD=0.0,
                 dec_RAD=0.0,
                 ang_RAD=0.0,
                 numexp=0,
                 exptimes=[]):

        self.targetId = targetId
        self.fieldId = fieldId
        self.ra_RAD = ra_RAD
        self.dec_RAD = dec_RAD
        self.ang_RAD = ang_RAD
        self.numexp = numexp
        self.exptimes = list(exptimes)

        self.propIds = []
        self.propValues = []
        self.value = 0.0

        return

    def __str__(self):
        return ("ID=%d field=%d ra=%.3f dec=%.3f" %
                (self.targetId, self.fieldId, self.ra_RAD * RAD2DEG, self.dec_RAD * RAD2DEG))
