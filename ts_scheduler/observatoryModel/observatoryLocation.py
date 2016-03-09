class ObservatoryLocation(object):

    def __init__(self,
                 latitude_rad=0.0,
                 longitude_rad=0.0,
                 height=0.0):
        # meters
        self.Height = height

        # radians
        self.latitude_rad = latitude_rad
        self.longitude_rad = longitude_rad
