import math

class ObservatoryLocation(object):

    def __init__(self,
                 latitude_rad=0.0,
                 longitude_rad=0.0,
                 height=0.0):
        # meters
        self.height = height

        # radians
        self.latitude_rad = latitude_rad
        self.longitude_rad = longitude_rad

    @property
    def latitude(self):
        return math.degrees(self.latitude_rad)

    @property
    def longitude(self):
        return math.degrees(self.longitude_rad)

    def configure(self, location_confdict):

        self.latitude_rad = math.radians(location_confdict["obs_site"]["latitude"])
        self.longitude_rad = math.radians(location_confdict["obs_site"]["longitude"])
        self.height = location_confdict["obs_site"]["height"]
