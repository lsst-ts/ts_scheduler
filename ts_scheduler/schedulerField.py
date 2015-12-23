from schedulerDefinitions import *

class schedulerField(object):

    def __init__(self,
                fieldId = 0,
                ra_RAD  = 0.0,
                dec_RAD = 0.0,
                gl_RAD  = 0.0,
                gb_RAD  = 0.0,
                el_RAD  = 0.0,
                eb_RAD  = 0.0,
		fov_RAD = 0.0):

        self.fieldId = fieldId
        self.ra_RAD  = ra_RAD
        self.dec_RAD = dec_RAD
        self.gl_RAD  = gl_RAD
        self.gb_RAD  = gb_RAD
        self.el_RAD  = el_RAD
        self.eb_RAD  = eb_RAD
	self.fov_RAD = fov_RAD

        return

    def __str__(self):
        return "ID=%d ra=%.3f dec=%.3f gl=%.3f gb=%.3f el=%.3f eb=%.3f" % (self.fieldId, self.ra_RAD*RAD2DEG, self.dec_RAD*RAD2DEG, self.gl_RAD*RAD2DEG, self.gb_RAD*RAD2DEG, self.el_RAD*RAD2DEG, self.eb_RAD*RAD2DEG)

