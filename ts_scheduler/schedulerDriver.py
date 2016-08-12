import os
import math
import copy
import logging

from operator import itemgetter

from ts_scheduler.setup import WORDY, EXTENSIVE
from ts_scheduler.sky_model import AstronomicalSkyModel
from ts_scheduler.schedulerDefinitions import DEG2RAD, read_conf_file, conf_file_path
from ts_scheduler.schedulerField import Field
from ts_scheduler.schedulerTarget import Target
from ts_scheduler.observatoryModel import ObservatoryModel
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.proposal import ScriptedProposal
from ts_scheduler.proposal import AreaDistributionProposal
from ts_scheduler.fields import FieldsDatabase

class DriverParameters(object):

    def __init__(self, confdict):

        self.coadd_values = confdict["ranking"]["coadd_values"]

        tmax = confdict["ranking"]["timebonus_tmax"]
        bmax = confdict["ranking"]["timebonus_bmax"]
        slope = confdict["ranking"]["timebonus_slope"]

        self.timebonus_dt = (math.sqrt(tmax * tmax + 4 * slope * tmax / bmax) - tmax) / 2
        self.timebonus_db = slope / (tmax + self.timebonus_dt)
        self.timebonus_slope = slope

        self.night_boundary = confdict["survey"]["night_boundary"]

class Driver(object):
    def __init__(self, survey_conf_file="survey.conf"):

        self.log = logging.getLogger("schedulerDriver")

        driver_confdict = read_conf_file(conf_file_path(__name__, "../conf", "scheduler", "driver.conf"))
        self.params = DriverParameters(driver_confdict)

        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        self.location = ObservatoryLocation()
        self.location.configure(site_confdict)

        observatory_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system",
                                                             "observatoryModel.conf"))
        self.observatoryModel = ObservatoryModel(self.location)
        self.observatoryModel.configure(observatory_confdict)

        self.sky = AstronomicalSkyModel(self.location)

        self.db = FieldsDatabase()

        self.build_fields_dict()

        survey_confdict = read_conf_file(conf_file_path(__name__, "../conf", "survey", survey_conf_file))

        self.propid_counter = 0
        self.science_proposal_list = []

        if 'scripted_propconf' in survey_confdict["proposals"]:
            scripted_propconflist = survey_confdict["proposals"]["scripted_propconf"]
        else:
            scripted_propconflist = []
        if not isinstance(scripted_propconflist, list):
            # turn it into a list with one entry
            propconf = scripted_propconflist
            scripted_propconflist = []
            scripted_propconflist.append(propconf)
        self.log.info("init: scripted proposals %s" % (scripted_propconflist))

        for k in range(len(scripted_propconflist)):
            self.propid_counter += 1
            scripted_prop = ScriptedProposal(self.propid_counter,
                                             conf_file_path(__name__, "../conf", "survey",
                                                            "{}".format(scripted_propconflist[k])),
                                             self.sky)
            self.science_proposal_list.append(scripted_prop)

        if 'areadistribution_propconf' in survey_confdict["proposals"]:
            areadistribution_propconflist = survey_confdict["proposals"]["areadistribution_propconf"]
        else:
            areadistribution_propconflist = []
            self.log.info("areadistributionPropConf:%s default" % (areadistribution_propconflist))
        if not isinstance(areadistribution_propconflist, list):
            # turn it into a list with one entry
            propconf = areadistribution_propconflist
            areadistribution_propconflist = []
            areadistribution_propconflist.append(propconf)
        self.log.info("init: areadistribution proposals %s" % (areadistribution_propconflist))

        for k in range(len(areadistribution_propconflist)):
            configfilepath = conf_file_path(__name__,
                                            "../conf",
                                            "survey",
                                            "{}".format(areadistribution_propconflist[k]))
            (path, name_ext) = os.path.split(configfilepath)
            (name, ext) = os.path.splitext(name_ext)
            proposal_confdict = read_conf_file(configfilepath)
            self.create_area_proposal(name, proposal_confdict)

        self.time = 0.0
        self.targetid = 0
        self.survey_started = False
        self.isnight = False
        self.sunset_timestamp = 0.0
        self.sunrise_timestamp = 0.0

    def configure(self, driver_confdict):

        self.params = DriverParameters(driver_confdict)

    def create_area_proposal(self, name, config_dict):

        self.propid_counter += 1
        area_prop = AreaDistributionProposal(self.propid_counter, name, config_dict, self.sky)
        self.science_proposal_list.append(area_prop)

    def configure_location(self, latitude_rad, longitude_rad, height):

        self.location.reconfigure(latitude_rad, longitude_rad, height)
        self.observatoryModel.location.reconfigure(latitude_rad, longitude_rad, height)
        self.sky.__init__(self.location)

    def configure_telescope(self,
                            altitude_minpos_rad,
                            altitude_maxpos_rad,
                            azimuth_minpos_rad,
                            azimuth_maxpos_rad,
                            altitude_maxspeed_rad,
                            altitude_accel_rad,
                            altitude_decel_rad,
                            azimuth_maxspeed_rad,
                            azimuth_accel_rad,
                            azimuth_decel_rad,
                            settle_time):

        self.observatoryModel.configure_telescope(altitude_minpos_rad,
                                                  altitude_maxpos_rad,
                                                  azimuth_minpos_rad,
                                                  azimuth_maxpos_rad,
                                                  altitude_maxspeed_rad,
                                                  altitude_accel_rad,
                                                  altitude_decel_rad,
                                                  azimuth_maxspeed_rad,
                                                  azimuth_accel_rad,
                                                  azimuth_decel_rad,
                                                  settle_time)

    def configure_rotator(self,
                          minpos_rad,
                          maxpos_rad,
                          maxspeed_rad,
                          accel_rad,
                          decel_rad,
                          filterchangepos_rad,
                          follow_sky,
                          resume_angle):

        self.observatoryModel.configure_rotator(minpos_rad,
                                                maxpos_rad,
                                                maxspeed_rad,
                                                accel_rad,
                                                decel_rad,
                                                filterchangepos_rad,
                                                follow_sky,
                                                resume_angle)

    def configure_dome(self,
                       altitude_maxspeed_rad,
                       altitude_accel_rad,
                       altitude_decel_rad,
                       azimuth_maxspeed_rad,
                       azimuth_accel_rad,
                       azimuth_decel_rad,
                       settle_time):

        self.observatoryModel.configure_dome(altitude_maxspeed_rad,
                                             altitude_accel_rad,
                                             altitude_decel_rad,
                                             azimuth_maxspeed_rad,
                                             azimuth_accel_rad,
                                             azimuth_decel_rad,
                                             settle_time)

    def configure_camera(self,
                         readout_time,
                         shutter_time,
                         filter_change_time,
                         filter_removable):

        self.observatoryModel.configure_camera(readout_time,
                                               shutter_time,
                                               filter_change_time,
                                               filter_removable)

    def configure_slew(self, prereq_dict):

        self.observatoryModel.configure_slew(prereq_dict)

    def configure_optics(self,
                         tel_optics_ol_slope,
                         tel_optics_cl_alt_limit,
                         tel_optics_cl_delay):

        self.observatoryModel.configure_optics(tel_optics_ol_slope,
                                               tel_optics_cl_alt_limit,
                                               tel_optics_cl_delay)

    def configure_park(self,
                       telescope_altitude,
                       telescope_azimuth,
                       telescope_rotator,
                       dome_altitude,
                       dome_azimuth,
                       filter_position):

        self.observatoryModel.configure_park(telescope_altitude,
                                             telescope_azimuth,
                                             telescope_rotator,
                                             dome_altitude,
                                             dome_azimuth,
                                             filter_position)

    def configure_area_proposal(self,
                                prop_id,
                                name,
                                config_dict):

        area_prop = AreaDistributionProposal(prop_id, name, config_dict, self.sky)
        self.science_proposal_list.append(area_prop)

    def build_fields_dict(self):

        sql = "select * from Field"
        res = self.db.query(sql)

        self.fields_dict = {}
        for row in res:
            field = Field()
            fieldid = row[0]
            field.fieldid = fieldid
            field.fov_rad = row[1] * DEG2RAD
            field.ra_rad = row[2] * DEG2RAD
            field.dec_rad = row[3] * DEG2RAD
            field.gl_rad = row[4] * DEG2RAD
            field.gb_rad = row[5] * DEG2RAD
            field.el_rad = row[6] * DEG2RAD
            field.eb_rad = row[7] * DEG2RAD
            self.fields_dict[fieldid] = field
            self.log.log(EXTENSIVE, "buildFieldsTable: %s" % (self.fields_dict[fieldid]))
        self.log.info("buildFieldsTable: %d fields" % (len(self.fields_dict)))

    def get_fields_dict(self):

        return self.fields_dict

    def start_survey(self, timestamp):

        self.log.info("start_survey t=%.1f" % timestamp)

        self.survey_started = True
        for prop in self.science_proposal_list:
            prop.start_survey()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("start_survey sunset=%.1f sunrise=%.1f" % (sunset, sunrise))
        if sunset <= timestamp < sunrise:
            self.start_night(timestamp)

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def end_survey(self):

        self.log.info("end_survey")

        for prop in self.science_proposal_list:
            prop.end_survey()

    def start_night(self, timestamp):

        self.log.log(WORDY, "start_night t=%.1f" % timestamp)

        self.isnight = True

        for prop in self.science_proposal_list:
            prop.start_night(timestamp, self.observatoryModel.currentState.mountedfilters)

    def end_night(self, timestamp):

        self.log.log(WORDY, "end_night t=%.1f" % timestamp)

        self.isnight = False

        for prop in self.science_proposal_list:
            prop.end_night()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("end_night sunset=%.1f sunrise=%.1f" % (sunset, sunrise))

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def swap_filter_in(self):
        return

    def swap_filter_out(self):
        return

    def update_time(self, timestamp):

        self.time = timestamp
        self.observatoryModel.update_state(self.time)
        if not self.survey_started:
            self.start_survey(timestamp)

        if self.isnight:
            if timestamp >= self.sunrise_timestamp:
                self.end_night(timestamp)
        else:
            if timestamp >= self.sunset_timestamp:
                self.start_night(timestamp)

    def update_internal_conditions(self, observatory_state):

        self.time = observatory_state.time
        self.observatoryModel.set_state(observatory_state)

    def update_external_conditions(self, timestamp):
        return

    def select_next_target(self):

        targets_dict = {}
        ranked_targets_list = []

        for prop in self.science_proposal_list:
            proptarget_list = prop.suggest_targets(self.time)
            self.log.debug("select_next_target propid=%d name=%s targets=%d" %
                           (prop.propid, prop.name, len(proptarget_list)))

            for target in proptarget_list:
                target.num_props = 1
                target.propid_list = [prop.propid]
                target.value_list = [target.value]
                fieldfilter = (target.fieldid, target.filter)
                if fieldfilter in targets_dict:
                    if self.params.coadd_values:
                        targets_dict[fieldfilter][0].value += target.value
                        targets_dict[fieldfilter][0].num_props += 1
                        targets_dict[fieldfilter][0].propid_list.append(prop.propid)
                        targets_dict[fieldfilter][0].propvalue_list.append(target.value)
                    else:
                        targets_dict[fieldfilter].append(copy.deepcopy(target))
                else:
                    targets_dict[fieldfilter] = [copy.deepcopy(target)]

        for fieldfilter in targets_dict:
            slewtime = self.observatoryModel.get_slew_delay(targets_dict[fieldfilter][0])
            if slewtime >= 0:
                cost_bonus = self.compute_slewtime_bonus(slewtime)
                for target in targets_dict[fieldfilter]:
                    target.slewtime = slewtime
                    target.cost_bonus = cost_bonus
                    target.rank = target.value + cost_bonus
                    ranked_targets_list.append((-target.rank, target))

        sorted_list = sorted(ranked_targets_list, key=itemgetter(0))
        try:
            winner_target = sorted_list.pop(0)[1]
            self.targetid += 1
            winner_target.targetid = self.targetid
            winner_target.time = self.time
        except:
            # if no target to suggest
            winner_target = Target()
            winner_target.num_exp = 2
            winner_target.targetid = -1

        return winner_target

    def register_observation(self, observation):

        if observation.targetid > 0:
            for prop in self.science_proposal_list:
                prop.register_observation(observation)

    def compute_slewtime_bonus(self, slewtime):

        bonus = self.params.timebonus_slope / (slewtime + self.params.timebonus_dt) - self.params.timebonus_db

        return bonus
