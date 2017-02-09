import math

__all__ = ["Field"]

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

    @property
    def ra(self):
        return math.degrees(self.ra_rad)

    @property
    def dec(self):
        return math.degrees(self.dec_rad)

    @property
    def gl(self):
        return math.degrees(self.gl_rad)

    @property
    def gb(self):
        return math.degrees(self.gb_rad)

    @property
    def el(self):
        return math.degrees(self.el_rad)

    @property
    def eb(self):
        return math.degrees(self.eb_rad)

    @property
    def fov(self):
        return math.degrees(self.fov_rad)

    def get_copy(self):

        newfield = Field(self.fieldid,
                         self.ra_rad,
                         self.dec_rad,
                         self.gl_rad,
                         self.gb_rad,
                         self.el_rad,
                         self.eb_rad,
                         self.fov_rad)
        return newfield

    def __str__(self):
        return ("ID=%d ra=%.3f dec=%.3f gl=%.3f gb=%.3f el=%.3f eb=%.3f fov=%.3f" %
                (self.fieldid, self.ra, self.dec, self.gl,
                 self.gb, self.el, self.eb, self.fov))

    @classmethod
    def from_db_row(cls, row):
        """Create instance from a database table row.

        Parameters
        ----------
        row : list[str]
            The database row information to create the instance from.

        Returns
        -------
        :class:`.Field`
            The instance containing the database row information.
        """
        return cls(row[0], math.radians(row[2]), math.radians(row[3]), math.radians(row[4]),
                   math.radians(row[5]), math.radians(row[6]), math.radians(row[7]), math.radians(row[1]))
