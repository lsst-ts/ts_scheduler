import numpy as np
from time import time
import logging
import os


class Lookahead(object):
    """The lookahead object stores the lookahead tables and calculates bonus scores to be applied
    based on future visibility. We assume that dates will always increment forward in time. 
    """

    def __init__(self, mjd=59853, window_size=8000, healpix=False, nSides=32):

        self.log = logging.getLogger("schedulerLookahead")
        self.window_size = window_size
        self.window = {}  # dict of lookahead windows, which are a view of the full lookahead array
        self.current_sky = {}  # the summed up totals over the lookahead window.
        self.date = mjd
        self.loaded_segment = 0
        self.lookahead = {}
        self.prev_idx = -5
        self.lookahead_mjds = np.array([])
        self.keys = [u'airmass', u'g', u'i', u'moonangle', u'r', u'u', u'y', u'z']
        self.filters = [u'g', u'i', u'r', u'u', u'y', u'z']
        self.healpixmode = healpix
        self.nSides = nSides
        self.bonus_weight = 1.0
        self.night_started = False

    def calculate_bonus(self, normalize=True):
        """calculates the bonus to be applied at the current date by summing the full lookahead window"""
        # do nothing if lookahead is "turned off" by a 0 window size.
        if self.window_size == 0:
            return None
        idx = self.__dateindex(self.date)
        self.populate_lookahead_window()

        # don't calculate unless we're in a new time slice.
        if idx != self.prev_idx:
            # sum up the window, ignoring the last index
            for k in self.keys:
                self.current_sky[k] = np.sum(self.window[k][0:-2], axis=0) / self.window_size

            # build lookup table for each filter, composed with moonangle and airmass
            max = 0
            for f in self.filters:
                score = self.current_sky[f] * self.current_sky[u'airmass'] \
                        * self.current_sky[u'moonangle']

                self.current_sky[f] = score
                localmax = self.current_sky[f].max()
                if localmax > max:
                    max = localmax

            # normalize values
            if normalize:
                for f in self.filters:
                    self.current_sky[f] = self.current_sky[f] / max

            # update the tables
            for f in self.filters:
                inverted = 1 - self.current_sky[f]
                self.current_sky[f] = inverted

        self.prev_idx = self.__dateindex(self.date)

    def calculate_bonus_fast(self):
        """instead of summing up the whole window every time interval, we should be able 
        to make the bonus calculation much quicker by keeping a running total, and then 
        adding the incoming value and subtracting the outgoing one. But it doesn't produce
        matching results, so for now this method only called by tests. """

        idx = self.__dateindex(self.date)
        gap = idx - self.prev_idx

        if gap == 0:
            pass  # don't calculate anything unless we're in a new time window.
        elif gap == 1:
            # if the gap is one, we take our quick shortcut.
            self.populate_lookahead_window()
            new_sky = {}
            # subtract the first index and add the new one.
            for k in self.keys:
                new_sky[k] = self.current_sky[k] - self.window[k][0]
                new_sky[k] = new_sky[k] + self.lookahead[k][-1]
                self.current_sky[k] = new_sky[k]
        else:
            # if the gap is anything other than 0 or 1, recalculate the whole window.
            self.populate_lookahead_window()
            for k in self.keys:
                self.current_sky[k] = np.sum(self.window[k][0:-2], axis=0)

        self.prev_idx = self.__dateindex(self.date)

    def lookup_opsim(self, fieldid, filter=u'u'):
        """gets bonus values out of self.current_sky based on field ID and filter"""
        # do nothing if lookahead is "turned off" by a 0 window size.
        if self.window_size == 0:
            return 0

        if self.healpixmode:
            raise TypeError("A opsim field lookup was attempted on a Lookahead using healpix mode.")
        return self.current_sky[filter][fieldid - 1]  # opsim field ids start at 1, python starts at zero.

    def lookup_healpix(self, hpixid, filter=u'u'):
        """gets bonus values for individual healpixels. Generally I don't expect we'll
           be looking these up one-at-a-time but this us useful for debugging."""
        # do nothing if lookahead is "turned off" by a 0 window size.
        if self.window_size == 0:
            return 0

        if self.healpixmode == False:
            raise TypeError("A healpix lookup was attempted on a Lookahead using OpsimField mode.")
        return self.current_sky[filter][hpixid]

    def load_segment(self):
        """loads the next segment and appends it to the end of the current lookahead table"""

        # do nothing if lookahead is "turned off" by a 0 window size.
        if self.window_size == 0:
            return None

        filename = 'lookahead_pre_seg_' + str(self.loaded_segment).zfill(3) + '.npz'
        if 'TS_SCHEDULER_DIR' in os.environ:
            # build the path to the lookahead data in scheduler folder
            segment_dir = os.environ['TS_SCHEDULER_DIR']
            segment_dir = os.path.join(segment_dir, 'python', 'lsst', 'ts', 'scheduler',
                                       'lookahead')  # there must be a better way.
            if self.healpixmode:
                segment_dir = os.path.join(segment_dir, 'segments_nsides' + str(self.nSides))
            else:
                segment_dir = os.path.join(segment_dir, 'segments_opsimfields')

            readout = np.load(os.path.join(segment_dir, filename))
            self.log.info("Loading lookahead segment " + str(self.loaded_segment))
        else:
            # if we can't find the path to the ts_scheduler directory, we assume
            # the lookahead files are in the current directory.
            print("loading " + filename)
            if self.healpixmode:
                readout = np.load('segments_nsides' + str(self.nSides) + "/" + filename)
            else:
                readout = np.load('segments_opsimfields' + "/" + filename)

        starttime = time()
        if len(self.lookahead.keys()) == 0:
            for k in self.keys:
                self.lookahead[k] = readout['look_ahead'][()][k]
            self.lookahead_mjds = readout['mjds']
        else:
            for i, k in enumerate(self.keys):
                self.lookahead[k] = np.append(self.lookahead[k], readout['look_ahead'][()][k], axis=0)
            self.lookahead_mjds = np.append(self.lookahead_mjds, readout['mjds'])
        readout.close()
        endtime = time()
        self.loaded_segment += 1

        # need to add logic that overrides the precomputed lookahead 
        # tables to mark fields as unobservable on dates when we have 
        # scheduled downtime.

        # if we load a segment and the window still isn't as big as it 
        # needs to be, keep loading more segments.
        if len(self.lookahead_mjds) < self.window_size + 145:
            self.log.info('loading additional segment...')
            self.load_segment()

    def populate_lookahead_window(self):
        """fills the lookahead window starting from the current date"""

        idx = self.__dateindex(self.date)

        # populate the window
        for k in self.keys:
            arr = self.lookahead[k][idx:idx + self.window_size + 1]
            self.window[k] = arr
        self.window[u'mjds'] = self.lookahead_mjds[idx:idx + self.window_size + 1]

    def __dateindex(self, mjd):
        """private method that returns the index with the value closest to mjd"""
        idx = (np.abs(self.lookahead_mjds - mjd)).argmin()
        return idx

    def start_night(self):
        """intended to be called at the start of a night of observing, this trims
         the front end of the lookahead table to remove data associated with dates
         that have elapsed. If the table is getting too small, we also load the
         next segment"""
        # do nothing if lookahead is "turned off" by a 0 window size.
        if self.window_size == 0 or self.night_started:
            return
        # load the next segment if necessary

        padding = 144  # number of 5 minute intervals in 120 hours

        if len(self.lookahead_mjds) < self.window_size + padding:
            self.log.info("autoloading next lookahead segment after trimming")
            self.load_segment()

        self.log.info("start_night lookahead table size: " + str(len(self.lookahead_mjds)))

        # find the index where we need to trim
        bookmark = 0
        for i, date in enumerate(self.lookahead_mjds):
            if date >= self.date:
                bookmark = i
                break

        # trim all the lookahead arrays
        for k in self.keys:
            self.lookahead[k] = self.lookahead[k][bookmark:]
        self.lookahead_mjds = self.lookahead_mjds[bookmark:]

        self.log.info("lookahead table size after start_night trimming: " + str(len(self.lookahead_mjds)))

        idx = self.__dateindex(self.date)
        dates = self.lookahead_mjds[idx:idx + self.window_size]
        span = np.max(dates) - np.min(dates[np.nonzero(dates)])
        self.log.info('Current lookahead window spans ' + str(round(span, 2)) + " nights")
        self.night_started = True

    def end_night(self):
        self.night_started = False
