import math

from ts_scheduler.observatoryModel import ObservatoryPosition

class ObservatoryState(ObservatoryPosition):

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
                 rot_rad=0.0,
                 telalt_rad=1.5,
                 telaz_rad=0.0,
                 telrot_rad=0.0,
                 domalt_rad=1.5,
                 domaz_rad=0.0,
                 mountedfilters=['g', 'r', 'i', 'z', 'y'],
                 unmountedfilters=['u']):

        ObservatoryPosition.__init__(self, time, ra_rad, dec_rad, ang_rad, filter,
                                     tracking, alt_rad, az_rad, pa_rad, rot_rad)

        self.telalt_rad = telalt_rad
        self.telalt_peakspeed_rad = 0
        self.telaz_rad = telaz_rad
        self.telaz_peakspeed_rad = 0
        self.telrot_rad = telrot_rad
        self.telrot_peakspeed_rad = 0
        self.domalt_rad = domalt_rad
        self.domalt_peakspeed_rad = 0
        self.domaz_rad = domaz_rad
        self.domaz_peakspeed_rad = 0
        self.mountedfilters = list(mountedfilters)
        self.unmountedfilters = list(unmountedfilters)

    @property
    def domalt(self):
        return math.degrees(self.domalt_rad)

    @property
    def domaz(self):
        return math.degrees(self.domaz_rad)

    @property
    def telalt(self):
        return math.degrees(self.telalt_rad)

    @property
    def telaz(self):
        return math.degrees(self.telaz_rad)

    @property
    def telrot(self):
        return math.degrees(self.telrot_rad)

    @property
    def domalt_peakspeed(self):
        return math.degrees(self.domalt_peakspeed_rad)

    @property
    def domaz_peakspeed(self):
        return math.degrees(self.domaz_peakspeed_rad)

    @property
    def telalt_peakspeed(self):
        return math.degrees(self.telalt_peakspeed_rad)

    @property
    def telaz_peakspeed(self):
        return math.degrees(self.telaz_peakspeed_rad)

    @property
    def telrot_peakspeed(self):
        return math.degrees(self.telrot_peakspeed_rad)

    def __str__(self):
        return ("%s telaz=%.3f telrot=%.3f mounted=%s unmounted=%s" %
                (ObservatoryPosition.__str__(self),
                 self.telaz, self.telrot, self.mountedfilters, self.unmountedfilters))

    def set(self, newstate):

        self.time = newstate.time
        self.ra_rad = newstate.ra_rad
        self.dec_rad = newstate.dec_rad
        self.ang_rad = newstate.ang_rad
        self.filter = newstate.filter
        self.tracking = newstate.tracking
        self.alt_rad = newstate.alt_rad
        self.az_rad = newstate.az_rad
        self.pa_rad = newstate.pa_rad
        self.rot_rad = newstate.rot_rad

        self.telalt_rad = newstate.telalt_rad
        self.telalt_peakspeed_rad = newstate.telalt_peakspeed_rad
        self.telaz_rad = newstate.telaz_rad
        self.telaz_peakspeed_rad = newstate.telaz_peakspeed_rad
        self.telrot_rad = newstate.telrot_rad
        self.telrot_peakspeed_rad = newstate.telrot_peakspeed_rad
        self.domalt_rad = newstate.domalt_rad
        self.domalt_peakspeed_rad = newstate.domalt_peakspeed_rad
        self.domaz_rad = newstate.domaz_rad
        self.domaz_peakspeed_rad = newstate.domaz_peakspeed_rad
        self.mountedfilters = list(newstate.mountedfilters)
        self.unmountedfilters = list(newstate.unmountedfilters)

    def set_position(self, newposition):

        self.time = newposition.time
        self.ra_rad = newposition.ra_rad
        self.dec_rad = newposition.dec_rad
        self.ang_rad = newposition.ang_rad
        self.filter = newposition.filter
        self.tracking = newposition.tracking
        self.alt_rad = newposition.alt_rad
        self.az_rad = newposition.az_rad
        self.pa_rad = newposition.pa_rad
        self.rot_rad = newposition.rot_rad

        self.telalt_rad = newposition.alt_rad
        self.telalt_peakspeed_rad = 0
        self.telaz_rad = newposition.az_rad
        self.telaz_peakspeed_rad = 0
        self.telrot_rad = newposition.rot_rad
        self.telrot_peakspeed_rad = 0
        self.domalt_rad = newposition.alt_rad
        self.domalt_peakspeed_rad = 0
        self.domaz_rad = newposition.az_rad
        self.domaz_peakspeed_rad = 0

    def swap_filter(self, filter_to_mount, filter_to_unmount):

        self.mountedfilters.remove(filter_to_unmount)
        self.unmountedfilters.remove(filter_to_mount)
        self.mountedfilter.append(filter_to_mount)
        self.unmountedfilter.append(filter_to_unmount)
