import numpy as np
from time import time

class Lookahead(object):
    '''This object stores the lookahead tables and calculates bonus scores to be applied
    based on future visibility. We assume that dates will always increment forward in time
    '''


    def __init__(self, mjd):
        
        self.date = mjd
        self.lookahead = {}
        self.keys = [u'airmass', u'g', u'i', u'moonangle', u'r', u'u', u'y', u'z', u'mjds']
        for k in self.keys:
            self.lookahead[k] = np.array([])

 
    def calculate_bonus(self,window_size):
        pass

    def load_segment(self,segNum):
        '''loads a segment and appends it to the end of the current lookahead table'''

        readout = np.load('segments_uncompressed/lookahead_pre_seg_'+str(segNum).zfill(3)+'.npz')
        #self.lookahead = readout['look_ahead'][()]
        #self.dates = readout['mjds'][()]
        starttime = time()
        for i,k in enumerate(self.keys):
            print(str(i+1)+"/"+str(len(self.keys)))
            self.lookahead[k] = np.append(self.lookahead[k],readout['look_ahead'][()][k])
            
        readout.close()
        endtime=time()
        print(endtime-starttime)
        print(len(self.lookahead[u'mjds']))
        