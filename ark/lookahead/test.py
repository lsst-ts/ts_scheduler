from lookahead import Lookahead
import numpy as np

def testLoadingAndAppendingSegments():
    la = Lookahead(59560.2, window_size=2000)
    la.load_segment()
    before = len(la.lookahead_mjds)
    la.load_segment()
    after = len(la.lookahead_mjds)
    assert before < after

def testStartNightArraySlicing():
    
    la = Lookahead(59560.2,window_size=30,healpix=True,nSides=8)
    la.load_segment()
    before = len(la.lookahead_mjds)
    la.date = 59561.2
    la.start_night()
    after = len(la.lookahead_mjds)
    print(before)
    print after

    assert before > after

    assert len(la.lookahead_mjds) == len(la.lookahead[u'u'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'g'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'r'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'i'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'z'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'y'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'moonangle'])
    assert len(la.lookahead_mjds) == len(la.lookahead[u'airmass'])

def testArrayShapes():
    '''makes sure the numpy arrays we're passing around have the right number
    of dimensions'''

    la = Lookahead()
    la.load_segment()

    #dates should be same length as sky map arrays
    assert la.lookahead[u'u'].shape[0]==la.lookahead_mjds.shape[0]

    #dates should be 1-dimensional, everything else should be 2-dimensional
    assert len(la.lookahead_mjds.shape) == 1
    for k in la.keys:
        assert len(la.lookahead[k].shape) == 2
 
    #trim the array, load some more data, and check again
    la.date += 5
    la.start_night()
    la.load_segment()
    
    assert la.lookahead[u'u'].shape[0]==la.lookahead_mjds.shape[0]
    assert len(la.lookahead_mjds.shape) == 1
    for k in la.keys:
        assert len(la.lookahead[k].shape) == 2

    
    
def testMemoryUsage():
    '''one simulated year's worth of loading and trimming'''
    la = Lookahead(healpix=True,nSides=8)
    la.load_segment()
    while la.date < 59885:
        la.date += 1
        la.start_night()
    assert True

def testDateIndex():
    '''test that when we ask for a date that isn't an exact value in the date table, we get 
    the closest available date'''
    la = Lookahead()
    la.load_segment()
    la.populate_lookahead_window()
    print(la.dateindex(59550.0278))
    print(la.date)
    print(la.lookahead_mjds[7])
    print(la.lookahead_mjds[8])
    print(la.lookahead_mjds[9])
    print(la.lookahead_mjds[10])



def testShortcutAccuracy():
    la1 = Lookahead(59560.16)
    la1.load_segment()
    la2 = Lookahead(59560.16)
    la2.load_segment()
    la1.calculate_bonus_fast()
    la2.calculate_bonus()
    logdiff = la1.current_sky['g'] == la2.current_sky['g']
    assert logdiff.all()==True
    
    la1.date += .003
    la2.date += .003
    la1.calculate_bonus_fast()
    la2.calculate_bonus()
    logdiff = la1.current_sky['g'] == la2.current_sky['g']
    print(logdiff)
    assert logdiff.all()==True
    la1.date += .003
    la2.date += .003
    la1.calculate_bonus_fast()
    la2.calculate_bonus()
    logdiff = la1.current_sky['g'] == la2.current_sky['g']
    assert logdiff.all()==True

    


    

if __name__ == "__main__":
    testLoadingAndAppendingSegments()
    testStartNightArraySlicing()
    testMemoryUsage()
    testArrayShapes()
    #testDateIndex()
    #testShortcutAccuracy()



