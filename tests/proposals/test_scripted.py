import os
import logging
import unittest
import warnings

from lsst.ts.scheduler.kernel import read_conf_file, conf_file_path
from lsst.ts.scheduler.proposals import ScriptedProposal
from lsst.ts.scheduler.observatory_model import ObservatoryLocation
from lsst.ts.scheduler.sky_model import AstronomicalSkyModel

class ScriptedProposalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=FutureWarning, append=True)
        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        location = ObservatoryLocation()
        location.configure(site_confdict)
        cls.skyModel = AstronomicalSkyModel(location)

    def setUp(self):
        logging.getLogger().setLevel(logging.WARN)
        configfilepath = conf_file_path(__name__, "../conf", "survey", "scriptedProp1.conf")
        resource_path = os.path.dirname(configfilepath)
        proposal_confdict = read_conf_file(configfilepath)
        script_file = os.path.join(resource_path, proposal_confdict["script"]["scriptfile"])
        self.scriptedprop = ScriptedProposal(1, "scriptedProp1", proposal_confdict,
                                             script_file, self.skyModel)

    def test_init(self):
        self.assertEqual(len(self.scriptedprop.targetsList), 10)

    def test_suggest_targets(self):
        tlist = self.scriptedprop.suggest_targets(1641090000)
        self.assertEqual(str(tlist[0]),
                         "targetid=0 field=2001 filter=r exp_times=[15, 15] ra=85.721 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641090000.0 airmass=0.000 brightness=21.211 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091040)
        self.assertEqual(str(tlist[0]),
                         "targetid=1 field=2002 filter=r exp_times=[15, 15] ra=229.721 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091040.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091080)
        self.assertEqual(str(tlist[0]),
                         "targetid=2 field=2003 filter=r exp_times=[15, 15] ra=130.279 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091080.0 airmass=0.000 brightness=20.869 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091120)
        self.assertEqual(str(tlist[0]),
                         "targetid=3 field=2004 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091120.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091160)
        self.assertEqual(str(tlist[0]),
                         "targetid=4 field=2005 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091160.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091200)
        self.assertEqual(str(tlist[0]),
                         "targetid=5 field=2006 filter=i exp_times=[15, 15] ra=13.721 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091200.0 airmass=0.000 brightness=19.857 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091240)
        self.assertEqual(str(tlist[0]),
                         "targetid=6 field=2007 filter=z exp_times=[15, 15] ra=199.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091240.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091280)
        self.assertEqual(str(tlist[0]),
                         "targetid=7 field=2008 filter=z exp_times=[15, 15] ra=160.794 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091280.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091320)
        self.assertEqual(str(tlist[0]),
                         "targetid=8 field=2009 filter=z exp_times=[15, 15] ra=232.794 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091320.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091360)
        self.assertEqual(str(tlist[0]),
                         "targetid=9 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091360.0 airmass=0.000 brightness=17.725 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091400)
        self.assertEqual(str(tlist[0]),
                         "targetid=10 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091400.0 airmass=0.000 brightness=17.728 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1641091440)
        self.assertEqual(str(tlist[0]),
                         "targetid=11 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1641091440.0 airmass=0.000 brightness=17.731 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 cost=0.000 rank=0.000")
