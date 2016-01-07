from schedulerDefinitions import RAD2DEG

class Field(object):

    def __init__(self,
                 fieldid=0,
                 ra_rad=0.0,
                 dec_rad=0.0,
                 gl_rad=0.0,
                 gb_rad=0.0,
                 el_rad=0.0,
                 eb_rad=0.0,
                 fov_rad=0.0):

        self.fieldid = fieldid
        self.ra_rad = ra_rad
        self.dec_rad = dec_rad
        self.gl_rad = gl_rad
        self.gb_rad = gb_rad
        self.el_rad = el_rad
        self.eb_rad = eb_rad
        self.fov_rad = fov_rad

    def __str__(self):
        return ("ID=%d ra=%.3f dec=%.3f gl=%.3f gb=%.3f el=%.3f eb=%.3f fov=%.3f" %
                (self.fieldid, self.ra_rad * RAD2DEG, self.dec_rad * RAD2DEG, self.gl_rad * RAD2DEG,
                 self.gb_rad * RAD2DEG, self.el_rad * RAD2DEG, self.eb_rad * RAD2DEG, self.fov_rad * RAD2DEG))
