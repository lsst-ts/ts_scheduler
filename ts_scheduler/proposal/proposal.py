import logging
import math
import os

from ts_scheduler.schedulerDefinitions import read_conf_file
from ts_scheduler.fields import CUT_TYPEMAP, FieldsDatabase, FieldSelection

class Proposal(object):
    def __init__(self, propid, configfilepath, skymodel):

        self.propid = propid

        (path, name_ext) = os.path.split(configfilepath)
        (name, ext) = os.path.splitext(name_ext)
        self.name = name

        self.log = logging.getLogger("scheduler.proposal.%s" % self.name)

        self.proposal_confdict = read_conf_file(configfilepath)

        self.sky = skymodel

        self.db = FieldsDatabase()

        self.field_select = FieldSelection()

    def start_survey(self):
        return

    def end_survey(self):
        return

    def start_night(self, timestamp, filters_mounted_tonight_list):
        return

    def end_night(self):
        return

    def suggest_targets(self, time):
        return []

    def select_fields(self, timestamp, sky_region, sky_exclusions, nightly_sky_bounds):
        query_list = []

        delta_lst = nightly_sky_bounds["delta_lst"]
        max_reach = sky_exclusions["max_reach"]

        self.sky.update(timestamp)
        (sunset_timestamp, sunrise_timestamp) = \
            self.sky.get_night_boundaries(self.params.nightly_sky_bounds["twilight_boundary"])

        self.sky.update(sunset_timestamp)
        sunset_lst_rad = self.sky.date_profile.lst_rad

        self.sky.update(sunrise_timestamp)
        sunrise_lst_rad = self.sky.date_profile.lst_rad

        # compute RA relative min at sunset twilight
        min_rel_ra = math.degrees(sunset_lst_rad) - delta_lst

        # compute RA relative max at sunrise twilight
        max_rel_ra = math.degrees(sunrise_lst_rad) + delta_lst

        # normalize RA relative limits to the [0; 360] range
        min_rel_ra = self.sky.sun.normalize(min_rel_ra)
        max_rel_ra = self.sky.sun.normalize(max_rel_ra)

        # compute DEC relative min
        min_rel_dec = self.sky.date_profile.location.latitude - max_reach

        # compute DEC relative max
        max_rel_dec = self.sky.date_profile.location.latitude + max_reach

        # Handle delta LST and max reach
        query_list.append(self.field_select.select_region("fieldRA", min_rel_ra, max_rel_ra))
        query_list.append(self.field_select.select_region("fieldDec", min_rel_dec, max_rel_dec))

        combine_list = ["and"]

        # Handle the sky region selections
        for cut in sky_region["cuts"]:
            cut_type = cut[0]
            if cut_type != "gp":
                query_list.append(self.field_select.select_region(CUT_TYPEMAP[cut_type], cut[1], cut[2]))
            else:
                query_list.append(self.field_select.galactic_region(cut[1], cut[2], cut[3], exclusion=False))

        current_num_queries = len(query_list)
        if current_num_queries > 2:
            combine_list.append("and")
        try:
            combine_list.extend(sky_region["combiners"])
        except KeyError:
            pass

        # Handle the sky exclusion selections
        try:
            for cut in sky_exclusions["cuts"]:
                cut_type = cut[0]
                if cut_type == "gp":
                    query_list.append(self.field_select.galactic_region(cut[1], cut[2], cut[3]))
                else:
                    self.log.warn("Do not know how to handle cuts for {}".format(cut_type))

            if len(query_list) > current_num_queries:
                combine_list.append("and")
        except KeyError:
            # No exclusion region(s) given.
            pass

        return self.field_select.combine_queries(combine_list, *query_list)
