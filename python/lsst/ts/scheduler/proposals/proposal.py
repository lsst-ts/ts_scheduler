from builtins import object
import logging
import math
import copy

from lsst.ts.scheduler.fields import FieldsDatabase, FieldSelection

__all__ = ["Proposal"]

class Proposal(object):
    def __init__(self, propid, name, confdict, skymodel):

        self.propid = propid
        self.name = name
        self.log = logging.getLogger("scheduler.proposals.%s" % self.name)
        self.proposal_confdict = copy.deepcopy(confdict)
        self.sky = skymodel
        self.db = FieldsDatabase()
        self.field_select = FieldSelection()

        self.night_boundary = 0.0
        self.ignore_sky_brightness = False
        self.ignore_airmass = False
        self.ignore_clouds = False
        self.ignore_seeing = False

    def configure_constraints(self, params):

        self.night_boundary = params.night_boundary
        self.ignore_sky_brightness = params.ignore_sky_brightness
        self.ignore_airmass = params.ignore_airmass
        self.ignore_clouds = params.ignore_clouds
        self.ignore_seeing = params.ignore_seeing

    def start_survey(self):
        return

    def end_survey(self):
        return

    def start_night(self, timestamp, filters_mounted_tonight_list, night):
        return

    def end_night(self, timestamp):
        return

    def suggest_targets(self, time, mjdstamp = None):
        return []

    def select_fields(self, timestamp, night, sky_region, sky_exclusions, sky_nightly_bounds):
        query_list = []

        delta_lst = sky_nightly_bounds["delta_lst"]
        dec_window = sky_exclusions["dec_window"]

        self.sky.update(timestamp)
        (sunset_timestamp, sunrise_timestamp) = \
            self.sky.get_night_boundaries(self.params.sky_nightly_bounds["twilight_boundary"])

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
        min_rel_dec = self.sky.date_profile.location.latitude - dec_window

        # compute DEC relative max
        max_rel_dec = self.sky.date_profile.location.latitude + dec_window

        # Handle delta LST and max reach
        query_list.append(self.field_select.select_region("RA", min_rel_ra, max_rel_ra))
        query_list.append(self.field_select.select_region("Dec", min_rel_dec, max_rel_dec))

        combine_list = ["and"]

        if "user_regions" in sky_region:
            # Handle user regions as a list of field ids
            query_list.append(self.field_select.user_regions(sky_region["user_regions"]))
            combine_list.append("and")

        else:
            # Handle any time dependent cuts
            try:
                time_ranges = sky_region["time_ranges"]
                index = 0
                for i, time_range in enumerate(time_ranges):
                    if night >= time_range[0] and night <= time_range[1]:
                        index = i
                        break
                # Mappings are float arrays when read from file
                mapping = [int(x) for x in sky_region["selection_mappings"][index]]
                region_cuts = sky_region["cuts"][mapping[0]:mapping[-1] + 1]
            except KeyError:
                region_cuts = sky_region["cuts"]

            # Handle the sky region selections
            for cut in region_cuts:
                cut_type = cut[0]
                if cut_type != "GP":
                    query_list.append(self.field_select.select_region(cut_type, cut[1], cut[2]))
                else:
                    query_list.append(self.field_select.galactic_region(cut[2], cut[1], cut[3],
                                                                        exclusion=False))

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
                    if cut_type == "GP":
                        query_list.append(self.field_select.galactic_region(cut[2], cut[1], cut[3]))
                    else:
                        self.log.warn("Do not know how to handle cuts for {}".format(cut_type))

                if len(query_list) > current_num_queries:
                    combine_list.append("and")
            except KeyError:
                # No exclusion region(s) given.
                pass

        return self.field_select.combine_queries(combine_list, *query_list)
