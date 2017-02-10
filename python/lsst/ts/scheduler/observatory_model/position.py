import math

__all__ = ["ObservatoryPosition"]

class ObservatoryPosition(object):

    def __init__(self,
                 time=0.0,
                 ra_rad=0.0,
                 dec_rad=0.0,
                 ang_rad=0.0,
                 filter='r',
                 tracking=False,
                 alt_rad=1.5,
                 az_rad=0.0,
                 pa_rad=0.0,
                 rot_rad=0.0):

        self.time = time
        self.ra_rad = ra_rad
        self.dec_rad = dec_rad
        self.ang_rad = ang_rad
        self.filter = filter
        self.tracking = tracking
        self.alt_rad = alt_rad
        self.az_rad = az_rad
        self.pa_rad = pa_rad
        self.rot_rad = rot_rad

    @property
    def ra(self):
        return math.degrees(self.ra_rad)

    @property
    def dec(self):
        return math.degrees(self.dec_rad)

    @property
    def ang(self):
        return math.degrees(self.ang_rad)

    @property
    def alt(self):
        return math.degrees(self.alt_rad)

    @property
    def az(self):
        return math.degrees(self.az_rad)

    @property
    def pa(self):
        return math.degrees(self.pa_rad)

    @property
    def rot(self):
        return math.degrees(self.rot_rad)

    def __str__(self):
        return ("t=%.1f ra=%.3f dec=%.3f ang=%.3f filter=%s track=%s alt=%.3f az=%.3f pa=%.3f rot=%.3f" %
                (self.time, self.ra, self.dec, self.ang, self.filter, self.tracking,
                 self.alt, self.az, self.pa, self.rot))
