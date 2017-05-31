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
from lsst.ts.scheduler.kernel import Field
from lsst.ts.scheduler.proposals import ScriptedProposal
from lsst.ts.scheduler.proposals import AreaDistributionProposal, TimeDistributionProposal
from lsst.ts.scheduler.fields import FieldsDatabase

__all__ = ["Driver"]

class DriverParameters(object):

    def __init__(self):

        self.coadd_values = False
        self.timecost_weight = 0.0
        self.timecost_dc = 0.0
        self.timecost_dt = 0.0
        self.timecost_k = 0.0
        self.night_boundary = 0.0
        self.ignore_sky_brightness = False
        self.ignore_airmass = False
        self.ignore_clouds = False
        self.ignore_seeing = False
        self.new_moon_phase_threshold = 0.0

    def configure(self, confdict):

        self.coadd_values = confdict["ranking"]["coadd_values"]
        self.time_balancing = confdict["ranking"]["time_balancing"]

        tmax = confdict["ranking"]["timecost_time_max"]
        tref = confdict["ranking"]["timecost_time_ref"]
        cref = float(confdict["ranking"]["timecost_cost_ref"])

        self.timecost_tmax = tmax
        self.timecost_tref = tref
        self.timecost_cref = cref

        self.timecost_dc = cref * (tmax - tref) / (tref - cref * tmax)
        self.timecost_dt = -tmax * (self.timecost_dc + 1.0)
        self.timecost_k = self.timecost_dc * self.timecost_dt
        self.timecost_weight = confdict["ranking"]["timecost_weight"]
        self.filtercost_weight = confdict["ranking"]["filtercost_weight"]

        self.night_boundary = confdict["constraints"]["night_boundary"]
        self.ignore_sky_brightness = confdict["constraints"]["ignore_sky_brightness"]
        self.ignore_airmass = confdict["constraints"]["ignore_airmass"]
        self.ignore_clouds = confdict["constraints"]["ignore_clouds"]
        self.ignore_seeing = confdict["constraints"]["ignore_seeing"]
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
        self.science_proposal_list = []

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
        self.nulltarget.num_props = 1
        self.nulltarget.propid_list = [0]
        self.nulltarget.need_list = [0.0]
        self.nulltarget.bonus_list = [0.0]
        self.nulltarget.value_list = [0.0]
        self.nulltarget.propboost_list = [1.0]
        self.last_winner_target = self.nulltarget.get_copy()
        self.deep_drilling_target = None

        self.need_filter_swap = False
        self.filter_to_unmount = ""
        self.filter_to_mount = ""

        self.cloud = 0.0
        self.seeing = 0.0

    def configure_survey(self, survey_conf_file):

        prop_conf_path = os.path.dirname(survey_conf_file)
        confdict = read_conf_file(survey_conf_file)

        self.survey_duration_DAYS = confdict["survey"]["survey_duration"]
        self.survey_duration_SECS = self.survey_duration_DAYS * 24 * 60 * 60.0

        self.propid_counter = 0
        self.science_proposal_list = []

        if 'scripted_propconf' in confdict["proposals"]:
            scripted_propconflist = confdict["proposals"]["scripted_propconf"]
        else:
            scripted_propconflist = []
        if not isinstance(scripted_propconflist, list):
            # turn it into a list with one entry
            propconf = scripted_propconflist
            scripted_propconflist = []
            scripted_propconflist.append(propconf)
        self.log.info("configure_survey: scripted proposals %s" % (scripted_propconflist))
        for k in range(len(scripted_propconflist)):
            self.propid_counter += 1
            scripted_prop = ScriptedProposal(self.propid_counter,
                                             os.path.join(prop_conf_path,
                                                          "{}".format(scripted_propconflist[k])),
                                             self.sky)
            self.science_proposal_list.append(scripted_prop)

        if 'areadistribution_propconf' in confdict["proposals"]:
            areadistribution_propconflist = confdict["proposals"]["areadistribution_propconf"]
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
            self.propid_counter += 1
            configfilepath = os.path.join(prop_conf_path, "{}".format(areadistribution_propconflist[k]))
            (path, name_ext) = os.path.split(configfilepath)
            (name, ext) = os.path.splitext(name_ext)
            proposal_confdict = read_conf_file(configfilepath)
            self.create_area_proposal(self.propid_counter, name, proposal_confdict)

        for prop in self.science_proposal_list:
            prop.configure_constraints(self.params)

    def configure_duration(self, survey_duration):

        self.survey_duration_DAYS = survey_duration
        self.survey_duration_SECS = survey_duration * 24 * 60 * 60.0

    def configure(self, confdict):

        self.params.configure(confdict)
        self.log.log(WORDY,
                     "configure: coadd_values=%s" % (self.params.coadd_values))
        self.log.log(WORDY,
                     "configure: time_balancing=%s" % (self.params.time_balancing))
        self.log.log(WORDY,
                     "configure: timecost_dc=%.3f" % (self.params.timecost_dc))
        self.log.log(WORDY,
                     "configure: timecost_dt=%.3f" % (self.params.timecost_dt))
        self.log.log(WORDY,
                     "configure: timecost_k=%.3f" % (self.params.timecost_k))
        self.log.log(WORDY,
                     "configure: timecost_weight=%.3f" % (self.params.timecost_weight))
        self.log.log(WORDY,
                     "configure: night_boundary=%.1f" % (self.params.night_boundary))
        self.log.log(WORDY,
                     "configure: ignore_sky_brightness=%s" % (self.params.ignore_sky_brightness))
        self.log.log(WORDY,
                     "configure: ignore_airmass=%s" % (self.params.ignore_airmass))
        self.log.log(WORDY,
                     "configure: ignore_clouds=%s" % (self.params.ignore_clouds))
        self.log.log(WORDY,
                     "configure: ignore_seeing=%s" % (self.params.ignore_seeing))
        self.log.log(WORDY,
                     "configure: new_moon_phase_threshold=%.2f" % (self.params.new_moon_phase_threshold))

        for prop in self.science_proposal_list:
            prop.configure_constraints(self.params)

    def configure_location(self, confdict):

        self.location.configure(confdict)
        self.observatoryModel.location.configure(confdict)
        self.observatoryModel2.location.configure(confdict)
        self.sky.update_location(self.location)

    def configure_observatory(self, confdict):

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

    def create_area_proposal(self, propid, name, config_dict):

        self.propid_counter += 1
        area_prop = AreaDistributionProposal(propid, name, config_dict, self.sky)
        area_prop.configure_constraints(self.params)
        self.science_proposal_list.append(area_prop)

    def create_sequence_proposal(self, propid, name, config_dict):

        self.propid_counter += 1
        seq_prop = TimeDistributionProposal(propid, name, config_dict, self.sky)
        seq_prop.configure_constraints(self.params)
        self.science_proposal_list.append(seq_prop)

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

        self.start_time = timestamp
        self.log.info("start_survey t=%.6f" % timestamp)

        self.survey_started = True
        for prop in self.science_proposal_list:
            prop.start_survey()

        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("start_survey sunset=%.6f sunrise=%.6f" % (sunset, sunrise))
        # if round(sunset) <= round(timestamp) < round(sunrise):
        if sunset <= timestamp < sunrise:
            self.start_night(timestamp, night)

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise

    def end_survey(self):

        self.log.info("end_survey")

        for prop in self.science_proposal_list:
            prop.end_survey()

    def start_night(self, timestamp, night):

        timeprogress = (timestamp - self.start_time) / self.survey_duration_SECS
        self.log.info("start_night t=%.6f, night=%d timeprogress=%.2f%%" %
                      (timestamp, night, 100 * timeprogress))

        self.isnight = True

        for prop in self.science_proposal_list:
            prop.start_night(timestamp, self.observatoryModel.current_state.mountedfilters, night)

    def end_night(self, timestamp, night):

        timeprogress = (timestamp - self.start_time) / self.survey_duration_SECS
        self.log.info("end_night t=%.6f, night=%d timeprogress=%.2f%%" %
                      (timestamp, night, 100 * timeprogress))

        self.isnight = False

        self.last_winner_target = self.nulltarget
        self.deep_drilling_target = None

        total_filter_visits_dict = {}
        total_filter_goal_dict = {}
        total_filter_progress_dict = {}
        for prop in self.science_proposal_list:
            prop.end_night(timestamp)
            filter_visits_dict = {}
            filter_goal_dict = {}
            filter_progress_dict = {}
            for filter in self.observatoryModel.filters:
                if filter not in total_filter_visits_dict:
                    total_filter_visits_dict[filter] = 0
                    total_filter_goal_dict[filter] = 0
                filter_visits_dict[filter] = prop.get_filter_visits(filter)
                filter_goal_dict[filter] = prop.get_filter_goal(filter)
                filter_progress_dict[filter] = prop.get_filter_progress(filter)
                total_filter_visits_dict[filter] += filter_visits_dict[filter]
                total_filter_goal_dict[filter] += filter_goal_dict[filter]
                self.log.debug("end_night propid=%d name=%s filter=%s progress=%.2f%%" %
                               (prop.propid, prop.name, filter, 100 * filter_progress_dict[filter]))
        for filter in self.observatoryModel.filters:
            if total_filter_goal_dict[filter] > 0:
                total_filter_progress_dict[filter] = \
                    float(total_filter_visits_dict[filter]) / total_filter_goal_dict[filter]
            else:
                total_filter_progress_dict[filter] = 0.0
            self.log.info("end_night filter=%s progress=%.2f%%" %
                          (filter, 100 * total_filter_progress_dict[filter]))

        previous_midnight_moonphase = self.midnight_moonphase
        self.sky.update(timestamp)
        (sunset, sunrise) = self.sky.get_night_boundaries(self.params.night_boundary)
        self.log.debug("end_night sunset=%.6f sunrise=%.6f" % (sunset, sunrise))

        self.sunset_timestamp = sunset
        self.sunrise_timestamp = sunrise
        next_midnight = (sunset + sunrise) / 2
        self.sky.update(next_midnight)
        info = self.sky.get_moon_sun_info(numpy.array([0.0]), numpy.array([0.0]))
        self.midnight_moonphase = info["moonPhase"]
        self.log.info("end_night next moonphase=%.2f%%" % (self.midnight_moonphase))

        self.need_filter_swap = False
        self.filter_to_mount = ""
        self.filter_to_unmount = ""
        if self.darktime:
            if self.midnight_moonphase > previous_midnight_moonphase:
                self.log.info("end_night dark time waxing")
                if self.midnight_moonphase > self.params.new_moon_phase_threshold:
                    self.need_filter_swap = True
                    self.filter_to_mount = self.unmounted_filter
                    self.filter_to_unmount = self.mounted_filter
                    self.darktime = False
            else:
                self.log.info("end_night dark time waning")
        else:
            if self.midnight_moonphase < previous_midnight_moonphase:
                self.log.info("end_night bright time waning")
                if self.midnight_moonphase < self.params.new_moon_phase_threshold:
                    self.need_filter_swap = True
                    self.filter_to_mount = self.observatoryModel.params.filter_darktime
                    max_progress = -1.0
                    for filter in self.observatoryModel.params.filter_removable_list:
                        if total_filter_progress_dict[filter] > max_progress:
                            self.filter_to_unmount = filter
                            max_progress = total_filter_progress_dict[filter]
                    self.darktime = True
            else:
                self.log.info("end_night bright time waxing")

        if self.need_filter_swap:
            self.log.debug("end_night filter swap %s=>cam=>%s" %
                           (self.filter_to_mount, self.filter_to_unmount))

    def swap_filter(self, filter_to_unmount, filter_to_mount):

        self.log.info("swap_filter swap %s=>cam=>%s" % (filter_to_mount, filter_to_unmount))

        self.observatoryModel.swap_filter(filter_to_unmount)

        self.unmounted_filter = filter_to_unmount
        self.mounted_filter = filter_to_mount

        return

    def update_time(self, timestamp, night):

        self.time = timestamp
        self.observatoryModel.update_state(self.time)
        if not self.survey_started:
            self.start_survey(timestamp, night)

        if self.isnight:
            # if round(timestamp) >= round(self.sunrise_timestamp):
            if timestamp >= self.sunrise_timestamp:
                self.end_night(timestamp, night)
        else:
            # if round(timestamp) >= round(self.sunset_timestamp):
            if timestamp >= self.sunset_timestamp:
                self.start_night(timestamp, night)

        return self.isnight

    def get_need_filter_swap(self):

        return (self.need_filter_swap, self.filter_to_unmount, self.filter_to_mount)

    def update_internal_conditions(self, observatory_state, night):

        if observatory_state.unmountedfilters != self.observatoryModel.current_state.unmountedfilters:
            unmount = observatory_state.unmountedfilters[0]
            mount = self.observatoryModel.current_state.unmountedfilters[0]
            self.swap_filter(unmount, mount)
            for prop in self.science_proposal_list:
                prop.start_night(observatory_state.time, observatory_state.mountedfilters, night)

        self.time = observatory_state.time
        self.observatoryModel.set_state(observatory_state)
        self.observatoryState.set(observatory_state)

    def update_external_conditions(self, cloud, seeing):

        self.cloud = cloud
        self.seeing = seeing

        return

    def select_next_target(self):

        if not self.isnight:
            return self.nulltarget

        targets_dict = {}
        ranked_targets_list = []
        propboost_dict = {}
        sumboost = 0.0

        timeprogress = (self.time - self.start_time) / self.survey_duration_SECS
        for prop in self.science_proposal_list:

            progress = prop.get_progress()
            if self.params.time_balancing:
                if progress > 0.0:
                    if timeprogress < 1.0:
                        needindex = (1.0 - progress) / (1.0 - timeprogress)
                    else:
                        needindex = 0.0
                    if timeprogress > 0.0:
                        progressindex = progress / timeprogress
                    else:
                        progressindex = 1.0
                    propboost_dict[prop.propid] = needindex / progressindex
                else:
                    propboost_dict[prop.propid] = 1.0
            else:
                propboost_dict[prop.propid] = 1.0
            sumboost += propboost_dict[prop.propid]

        if self.deep_drilling_target is not None:
            self.log.debug("select_next_target: in deep drilling %s" % str(self.deep_drilling_target))

        if self.observatoryModel.is_filter_change_allowed():
            constrained_filter = None
        else:
            constrained_filter = self.observatoryModel.current_state.filter
        num_filter_changes = self.observatoryModel.get_number_filter_changes()
        delta_burst = self.observatoryModel.get_delta_filter_burst()
        delta_avg = self.observatoryModel.get_delta_filter_avg()
        self.log.debug("select_next_target: filter changes num=%i tburst=%.1f tavg=%.1f constrained=%s" %
                       (num_filter_changes, delta_burst, delta_avg, constrained_filter))

        for prop in self.science_proposal_list:
            propboost_dict[prop.propid] = \
                propboost_dict[prop.propid] * len(self.science_proposal_list) / sumboost

            proptarget_list = prop.suggest_targets(self.time,
                                                   self.deep_drilling_target, constrained_filter,
                                                   self.cloud, self.seeing)
            self.log.log(EXTENSIVE, "select_next_target propid=%d name=%s "
                         "targets=%d progress=%.2f%% propboost=%.3f" %
                         (prop.propid, prop.name,
                          len(proptarget_list), 100 * progress, propboost_dict[prop.propid]))

            for target in proptarget_list:
                target.num_props = 1
                target.propboost = propboost_dict[prop.propid]
                target.propid_list = [prop.propid]
                target.need_list = [target.need]
                target.bonus_list = [target.bonus]
                target.value_list = [target.value]
                target.propboost_list = [target.propboost]
                target.sequenceid_list = [target.sequenceid]
                target.subsequencename_list = [target.subsequencename]
                target.groupid_list = [target.groupid]
                target.groupix_list = [target.groupix]
                target.is_deep_drilling_list = [target.is_deep_drilling]
                target.is_dd_firstvisit_list = [target.is_dd_firstvisit]
                target.remaining_dd_visits_list = [target.remaining_dd_visits]
                target.dd_exposures_list = [target.dd_exposures]
                target.dd_filterchanges_list = [target.dd_filterchanges]
                target.dd_exptime_list = [target.dd_exptime]

                fieldfilter = (target.fieldid, target.filter)
                if fieldfilter in targets_dict:
                    if self.params.coadd_values:
                        targets_dict[fieldfilter][0] = targets_dict[fieldfilter][0].get_copy()
                        targets_dict[fieldfilter][0].need += target.need
                        targets_dict[fieldfilter][0].bonus += target.bonus
                        targets_dict[fieldfilter][0].value += target.value
                        targets_dict[fieldfilter][0].propboost += target.propboost
                        if target.is_deep_drilling:
                            # overrides to make the coadded target a consistent deep drilling
                            targets_dict[fieldfilter][0].is_deep_drilling = target.is_deep_drilling
                            targets_dict[fieldfilter][0].is_dd_firstvisit = target.is_dd_firstvisit
                            targets_dict[fieldfilter][0].remaining_dd_visits = target.remaining_dd_visits
                            targets_dict[fieldfilter][0].dd_exposures = target.dd_exposures
                            targets_dict[fieldfilter][0].dd_filterchanges = target.dd_filterchanges
                            targets_dict[fieldfilter][0].dd_exptime = target.dd_exptime
                            targets_dict[fieldfilter][0].sequenceid = target.sequenceid
                            targets_dict[fieldfilter][0].subsequencename = target.subsequencename
                            targets_dict[fieldfilter][0].groupid = target.groupid
                            targets_dict[fieldfilter][0].groupix = target.groupix
                        else:
                            # new target to coadd is not deep drilling
                            if not targets_dict[fieldfilter][0].is_deep_drilling:
                                # coadded target is not deep drilling
                                # overrides with new sequence information
                                targets_dict[fieldfilter][0].sequenceid = target.sequenceid
                                targets_dict[fieldfilter][0].subsequencename = target.subsequencename
                                targets_dict[fieldfilter][0].groupid = target.groupid
                                targets_dict[fieldfilter][0].groupix = target.groupix
                            # if coadded target is already deep drilling, don't override
                        targets_dict[fieldfilter][0].num_props += 1
                        targets_dict[fieldfilter][0].propid_list.append(prop.propid)
                        targets_dict[fieldfilter][0].need_list.append(target.need)
                        targets_dict[fieldfilter][0].bonus_list.append(target.bonus)
                        targets_dict[fieldfilter][0].value_list.append(target.value)
                        targets_dict[fieldfilter][0].propboost_list.append(target.propboost)
                        targets_dict[fieldfilter][0].sequenceid_list.append(target.sequenceid)
                        targets_dict[fieldfilter][0].subsequencename_list.append(target.subsequencename)
                        targets_dict[fieldfilter][0].groupid_list.append(target.groupid)
                        targets_dict[fieldfilter][0].groupix_list.append(target.groupix)
                        targets_dict[fieldfilter][0].is_deep_drilling_list.append(target.is_deep_drilling)
                        targets_dict[fieldfilter][0].is_dd_firstvisit_list.append(target.is_dd_firstvisit)
                        targets_dict[fieldfilter][0].remaining_dd_visits_list.append(target.remaining_dd_visits)
                        targets_dict[fieldfilter][0].dd_exposures_list.append(target.dd_exposures)
                        targets_dict[fieldfilter][0].dd_filterchanges_list.append(target.dd_filterchanges)
                        targets_dict[fieldfilter][0].dd_exptime_list.append(target.dd_exptime)
                    else:
                        targets_dict[fieldfilter].append(target)
                else:
                    targets_dict[fieldfilter] = [target]

        filtercost = self.compute_filterchange_cost() * self.params.filtercost_weight
        for fieldfilter in targets_dict:
            slewtime = self.observatoryModel.get_slew_delay(targets_dict[fieldfilter][0])
            if slewtime >= 0:
                timecost = self.compute_slewtime_cost(slewtime) * self.params.timecost_weight
                for target in targets_dict[fieldfilter]:
                    target.slewtime = slewtime
                    if target.filter != self.observatoryModel.current_state.filter:
                        target.cost = timecost + filtercost
                    else:
                        target.cost = timecost
                    target.rank = (target.value * target.propboost) - target.cost
                    ranked_targets_list.append((-target.rank, target))

        sorted_list = sorted(ranked_targets_list, key=itemgetter(0))

        winner_found = False
        while len(sorted_list) > 0 and not winner_found:
            winner_target = sorted_list.pop(0)[1]

            self.observatoryModel2.set_state(self.observatoryState)
            self.observatoryModel2.observe(winner_target)
            if winner_target.is_dd_firstvisit:
                ttime = self.observatoryModel2.get_deep_drilling_time(winner_target)
            else:
                ttime = 30.0
            self.observatoryModel2.update_state(self.observatoryModel2.current_state.time + ttime)
            if self.observatoryModel2.current_state.tracking:
                self.targetid += 1
                winner_target.targetid = self.targetid
                winner_target.time = self.time
                winner_found = True
            else:
                self.log.debug("select_next_target: target rejected ttime=%.1f %s" %
                               (ttime, str(winner_target)))
                self.log.debug("select_next_target: state rejected %s" %
                               str(self.observatoryModel2.current_state))

        if winner_found:
            if not self.params.coadd_values:
                first_target = targets_dict[(winner_target.fieldid, winner_target.filter)][0]
                if first_target.propid != winner_target.propid:
                    winner_target.copy_driver_state(first_target)
            self.last_winner_target = winner_target.get_copy()
        else:
            self.last_winner_target = self.nulltarget

        return self.last_winner_target

    def register_observation(self, observation):

        target_list = []
        if observation.targetid > 0:
            if self.observation_fulfills_target(observation, self.last_winner_target):
                observation = self.last_winner_target
            else:
                self.log.info("register_observation: unexpected observation %s" % str(observation))

            for prop in self.science_proposal_list:
                target = prop.register_observation(observation)
                if target is not None:
                    target_list.append(target)

        self.last_observation = observation.get_copy()
        if self.last_observation.is_deep_drilling and (self.last_observation.remaining_dd_visits > 1):
            self.deep_drilling_target = self.last_observation
        else:
            self.deep_drilling_target = None

        return target_list

    def compute_slewtime_cost(self, slewtime):

        cost = (self.params.timecost_k / (slewtime + self.params.timecost_dt) - self.params.timecost_dc - self.params.timecost_cref) / (1.0 - self.params.timecost_cref)
        #cost = self.params.timecost_k / (slewtime + self.params.timecost_dt) - self.params.timecost_dc

        return cost

    def compute_filterchange_cost(self):

        t = self.observatoryModel.get_delta_last_filterchange()
        T = self.observatoryModel.params.filter_max_changes_avg_interval
        if t < T:
            cost = 1.0 - t / T
        else:
            cost = 0.0

        return cost

    def observation_fulfills_target(self, observ, target):

        return (observ.fieldid == target.fieldid) and (observ.filter == target.filter)
