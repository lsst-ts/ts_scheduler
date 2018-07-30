from builtins import object
from builtins import range
from builtins import str
import os
import math
import numpy
import logging
from operator import itemgetter

from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.observatory.model import ObservatoryModel
from lsst.ts.observatory.model import ObservatoryState
from lsst.ts.observatory.model import Target
from lsst.ts.scheduler.setup import EXTENSIVE, WORDY
from lsst.ts.scheduler.kernel import read_conf_file
from lsst.ts.scheduler.kernel import Field, SurveyTopology
from lsst.ts.scheduler.fields import FieldsDatabase
from lsst.ts.scheduler.lookahead import Lookahead

__all__ = ["Driver"]


class DriverParameters(object):

    def __init__(self):
        self.night_boundary = 0.0
        self.new_moon_phase_threshold = 0.0

    def configure(self, confdict):
        self.lookahead_window_size = confdict['ranking']['lookahead_window_size']
        self.lookahead_bonus_weight = confdict["ranking"]["lookahead_bonus_weight"]
        self.night_boundary = confdict["constraints"]["night_boundary"]
        self.new_moon_phase_threshold = confdict["darktime"]["new_moon_phase_threshold"]


class Driver(object):
    def __init__(self):

        self.log = logging.getLogger("schedulerDriver")

        self.params = DriverParameters()
        self.location = ObservatoryLocation()

        self.observatoryModel = ObservatoryModel(self.location, WORDY)
        self.observatoryModel2 = ObservatoryModel(self.location, WORDY)
        self.observatoryState = ObservatoryState()

        self.sky = AstronomicalSkyModel(self.location)

        self.db = FieldsDatabase()

        self.build_fields_dict()

        self.propid_counter = 0

        self.start_time = 0.0
        self.time = 0.0
        self.targetid = 0
        self.survey_started = False
        self.isnight = False
        self.sunset_timestamp = 0.0
        self.sunrise_timestamp = 0.0
        self.survey_duration_DAYS = 0.0
        self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0
        self.darktime = False
        self.mounted_filter = ""
        self.unmounted_filter = ""
        self.midnight_moonphase = 0.0

        self.nulltarget = Target()
        self.nulltarget.targetid = -1
        self.nulltarget.num_exp = 1
        self.nulltarget.exp_times = [0.0]

        self.nulltarget.need_list = [0.0]
        self.nulltarget.bonus_list = [0.0]
        self.nulltarget.value_list = [0.0]
        self.last_winner_target = self.nulltarget.get_copy()
        self.deep_drilling_target = None

        self.need_filter_swap = False
        self.filter_to_unmount = ""
        self.filter_to_mount = ""

        self.cloud = 0.0
        self.seeing = 0.0

        self.lookahead = Lookahead()

    def configure_scheduler(self, **kwargs):
        pass

    def configure_duration(self, survey_duration):

        self.survey_duration_DAYS = survey_duration
        self.survey_duration_SECS = survey_duration * 24 * 60 * 60.0

    def configure(self, confdict):
        self.params.configure(confdict) 
        self.log.log(WORDY,
                     "configure: night_boundary=%.1f" % (self.params.night_boundary))
        self.lookahead.window_size = self.params.lookahead_window_size
        self.lookahead.bonus_weight = self.params.lookahead_bonus_weight

    def configure_location(self, confdict):

        self.location.configure(confdict)
        self.observatoryModel.location.configure(confdict)
        self.observatoryModel2.location.configure(confdict)
        self.sky.update_location(self.location)

    def configure_observatory(self, confdict):
        '''
        Input Arguments: confdict : dict() 
        Output: N/A
        Description: This method calls the configure()method in ObservatoryModel class, 
        which configures all its submodules. When initializing one can issue a call to this method with a complete set of parameters on confdict.
        '''

        self.observatoryModel.configure(confdict)
        self.observatoryModel2.configure(confdict)

    def configure_telescope(self, confdict):

        self.observatoryModel.configure_telescope(confdict)
        self.observatoryModel2.configure_telescope(confdict)

    def configure_rotator(self, confdict):

        self.observatoryModel.configure_rotator(confdict)
        self.observatoryModel2.configure_rotator(confdict)

    def configure_dome(self, confdict):

        self.observatoryModel.configure_dome(confdict)
        self.observatoryModel2.configure_dome(confdict)

    def configure_optics(self, confdict):

        self.observatoryModel.configure_optics(confdict)
        self.observatoryModel2.configure_optics(confdict)

    def configure_camera(self, confdict):

        self.observatoryModel.configure_camera(confdict)
        self.observatoryModel2.configure_camera(confdict)

    def configure_slew(self, confdict):

        self.observatoryModel.configure_slew(confdict)
        self.observatoryModel2.configure_slew(confdict)

    def configure_park(self, confdict):

        self.observatoryModel.configure_park(confdict)
        self.observatoryModel2.configure_park(confdict)


    def build_fields_dict(self):

        sql = "select * from Field"
        res = self.db.query(sql)

        self.fields_dict = {}
        for row in res:
            field = Field()
            fieldid = row[0]
            field.fieldid = fieldid
            field.fov_rad = math.radians(row[1])
            field.ra_rad = math.radians(row[2])
            field.dec_rad = math.radians(row[3])
            field.gl_rad = math.radians(row[4])
            field.gb_rad = math.radians(row[5])
            field.el_rad = math.radians(row[6])
            field.eb_rad = math.radians(row[7])
            self.fields_dict[fieldid] = field
            self.log.log(EXTENSIVE, "buildFieldsTable: %s" % (self.fields_dict[fieldid]))
        self.log.info("buildFieldsTable: %d fields" % (len(self.fields_dict)))

    def get_fields_dict(self):

        return self.fields_dict

    def start_survey(self, timestamp, night):
        '''
        Input Arguments: float timestamp, int night
        Output: N/A
        Description: Begins the survey
        '''

        self.start_time = timestamp

        self.log.info("start_survey t=%.6f" % timestamp)

        self.survey_started = True
        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("start_survey sunset=%.6f sunrise=%.6f" % (sunset, sunrise))
        # if round(sunset) <= round(timestamp) < round(sunrise):
        if sunset <= timestamp < sunrise:
            self.start_night(timestamp, night)

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def end_survey(self):
        '''
        Input Arguments: N/A
        Output: N/A
        Description: Ends the survey
        '''
        self.log.info("end_survey")


    def start_night(self, timestamp, night):
        '''
        Input Arguments: float timestamp, int night
        Output: N/A
        This method is called once per night before observations begin. 
        It is not called if the observatory is undergoing downtime.
        '''
        timeprogress = (timestamp - self.start_time) / self.survey_duration_SECS
        self.log.info("start_night t=%.6f, night=%d timeprogress=%.2f%%" %
                      (timestamp, night, 100 * timeprogress))

        self.isnight = True

    def end_night(self, timestamp, night):
        '''
        Input Arguments: float timestamp, int night
        Output: N/A
        Description: This method is called once per night after observing completes.
        '''
        pass

    def swap_filter(self, filter_to_unmount, filter_to_mount):

        self.log.info("swap_filter swap %s=>cam=>%s" % (filter_to_mount, filter_to_unmount))

        self.observatoryModel.swap_filter(filter_to_unmount)

        self.unmounted_filter = filter_to_unmount
        self.mounted_filter = filter_to_mount

        return

    def update_time(self, timestamp, night):
        pass

    def get_need_filter_swap(self):
        '''
        Input Arguments: NA
        Output: Python Tuple (bool need_filter_swap, string filter_to_unmount, string filter_to_mount)
        Description: When scheduler determines that a filter swap is needed, 
        this shall return a tuple where the first element is a TRUE value, 
        and the second and third elements are single-character strings identifying
        which filter to remove from the carousel, and which filter to add, respectively. 
        '''

        return (self.need_filter_swap, self.filter_to_unmount, self.filter_to_mount)

    def update_internal_conditions(self, observatory_state, night):

        if observatory_state.unmountedfilters != self.observatoryModel.current_state.unmountedfilters:
            unmount = observatory_state.unmountedfilters[0]
            mount = self.observatoryModel.current_state.unmountedfilters[0]
            self.swap_filter(unmount, mount)
        self.time = observatory_state.time
        self.observatoryModel.set_state(observatory_state)
        self.observatoryState.set(observatory_state)

    def update_external_conditions(self, cloud, seeing):

        self.cloud = cloud
        self.seeing = seeing

        return

    def cold_start(self, obs_list=None):
       """Rebuilds the state of the scheduler from a list of observations"""
       raise NotImplemented

    def select_next_target(self):
        '''
        Input Arguments: None
        Output: Target Object
        Description: Picks a target and returns it as a target object.
        '''

        raise NotImplemented

    def register_observation(self, observation):
        '''
        Input Arguments: Observation, or python list of observations.
        Output: list of observations
        Description: Validates observation and returns a list of successfully completed observations. 
        '''

        raise NotImplemented