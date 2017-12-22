from __future__ import print_function
from builtins import zip
import numpy as np
np.set_printoptions(threshold=np.nan)
import lsst.sims.utils as utils
import healpy as hp
import sys
import ephem
import palpy
from lsst.sims.skybrightness.utils import mjd2djd
import lsst.sims.skybrightness as sb
from lsst.ts.astrosky.model import AstronomicalSkyModel
from time import time


def generate_lookahead_tables(mjd0=59560.2, mjd_max=59621.2, timestep=5., timestep_max=20.,
                 outfile='generated_sky.npz', outpath=None, nside=32,
                 sunLimit=-12., fieldID=False, airmass_limit=1.5, dm=0.3, verbose=True):
    """
    Use the sky brightness model and the astronomical sky model to generate map of whether
    the sky will be observable at a given point in time and space, based on airmass, sky
    brightness, and moon location. Each feature gets its own map, where a 0 means a field
    or healpixel is not observable, and a 1 means it is. For now these are always 0 or 1 
    but they are typed as floats to accomodate future improvements
    """
    
    sunLimit = np.radians(sunLimit)

    # Set the time steps
    timestep = timestep / 60. / 24.  # Convert to days
    timestep_max = timestep_max / 60. / 24.  # Convert to days
    # Switch the indexing to opsim field ID if requested

    # Look at the mjds and toss ones where the sun is up
    mjds = np.arange(mjd0, mjd_max+timestep, timestep)
    sunAlts = np.zeros(mjds.size, dtype=float)

    telescope = utils.Site('LSST')
    Observatory = ephem.Observer()
    Observatory.lat = telescope.latitude_rad
    Observatory.lon = telescope.longitude_rad
    Observatory.elevation = telescope.height


    sun = ephem.Sun()

    for i, mjd in enumerate(mjds):
        Observatory.date = mjd2djd(mjd)
        sun.compute(Observatory)
        sunAlts[i] = sun.alt
    
    mjds = mjds[np.where(sunAlts <= np.radians(sunLimit))]
    
    
    if fieldID:
        field_data = np.loadtxt('fieldID.dat', delimiter='|', skiprows=1,
                                dtype=list(zip(['id', 'ra', 'dec'], [int, float, float])))
        ra = field_data['ra']
        dec = field_data['dec']
    else:
        hpindx = np.arange(hp.nside2npix(nside))
        ra, dec = utils.hpid2RaDec(nside, hpindx)

    if verbose:
        print('using %i points on the sky' % ra.size)
        print('using %i mjds' % mjds.size)

        # Set up the sky brightness model
    sm = sb.SkyModel(mags=True)
    

    filter_names = [u'u', u'g', u'r', u'i', u'z', u'y']

    # Initialize the relevant lists
    sky_brightness = {u'airmass': np.zeros((len(mjds), len(ra)), dtype = float),\
     u'mjds': np.zeros((len(mjds), len(ra)), dtype = float),\
     u'moonangle': np.zeros((len(mjds), len(ra)), dtype = float) }
    vmjd = np.zeros(len(mjds))

    for filter_name in filter_names:
        sky_brightness[filter_name] = np.zeros((len(mjds),len(ra)), dtype = float)

    length = mjds[-1] - mjds[0]

    for i, mjd in enumerate(mjds):
        progress = (mjd-mjd0)/length*100
        text = "\rprogress = %.1f%%"%progress
        sys.stdout.write(text)
        sys.stdout.flush()
        sm.setRaDecMjd(ra, dec, mjd, degrees=True)
        if sm.sunAlt <= sunLimit:
            mags = sm.returnMags()
            for key in filter_names:
                sky_brightness[key][i] = mags[key]  < 21.3 #placeholder skybrightness
            airmasscomp = np.bitwise_and(1.5 > sm.airmass, sm.airmass > 1.0)
            sky_brightness['airmass'][i] = airmasscomp
            moonangles = palpy.dsepVector(np.full_like(ra,sm.moonRA), np.full_like(dec,sm.moonDec),\
                np.deg2rad(ra), np.deg2rad(dec))
            sky_brightness['moonangle'][i] = moonangles > 0.698 #placeholder moon angle limit, ~40 degrees
            vmjd[i] = mjd
           
    print('')

#     for key in dict_of_lists:
#         dict_of_lists[key] = np.array(dict_of_lists[key])
# #         print(len(dict_of_lists[key]))
#     for key in sky_brightness:
#         sky_brightness[key] = np.array(sky_brightness[key])

    np.savez(outfile, mjds=vmjd, look_ahead=sky_brightness)
if __name__ == "__main__":
    startt = time()
    generate_lookahead_tables(fieldID=False)
    print(str(time()-startt)+"seconds")
    nyears = 11
    day_pad = 0 #overlap
    # Full year
    # mjds = np.arange(59560, 59560+365.25*nyears+day_pad+366, 366)
    # 3-months
    mjds = np.arange(59560, 59560+366*nyears+366/6., 366/6.)
    count = 0
    for mjd1, mjd2 in zip(mjds[:-1], mjds[1:]):
        print('Generating file %i' % count)
        #generate_sky(mjd0=mjd1, mjd_max=mjd2, outpath='opsimFields', fieldID=True)
        generate_lookahead_tables(mjd0=mjd1, mjd_max=mjd2+day_pad,\
        outfile="lookahead_pre_seg_"+str(count).zfill(3), outpath=None,fieldID=False)
        count += 1
    #generate_sky(fieldID=True, outfile='generated_sky_field.npz')
    
