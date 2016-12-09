import os
import logging
import unittest
import warnings

from ts_scheduler.schedulerDefinitions import read_conf_file, conf_file_path
from ts_scheduler.proposal import ScriptedProposal
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.sky_model import AstronomicalSkyModel

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
        tlist = self.scriptedprop.suggest_targets(1000)
        self.assertEqual(str(tlist[0]),
                         "targetid=0 field=2001 filter=r exp_times=[15, 15] ra=85.721 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1000.0 airmass=0.000 brightness=20.970 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1040)
        self.assertEqual(str(tlist[0]),
                         "targetid=1 field=2002 filter=r exp_times=[15, 15] ra=229.721 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1040.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1080)
        self.assertEqual(str(tlist[0]),
                         "targetid=2 field=2003 filter=r exp_times=[15, 15] ra=130.279 dec=-14.442 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1080.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1120)
        self.assertEqual(str(tlist[0]),
                         "targetid=3 field=2004 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1120.0 airmass=0.000 brightness=19.818 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1160)
        self.assertEqual(str(tlist[0]),
                         "targetid=4 field=2005 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1160.0 airmass=0.000 brightness=19.816 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1200)
        self.assertEqual(str(tlist[0]),
                         "targetid=5 field=2006 filter=i exp_times=[15, 15] ra=13.721 dec=-14.441 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1200.0 airmass=0.000 brightness=20.220 cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1240)
        self.assertEqual(str(tlist[0]),
                         "targetid=6 field=2007 filter=z exp_times=[15, 15] ra=199.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1240.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1280)
        self.assertEqual(str(tlist[0]),
                         "targetid=7 field=2008 filter=z exp_times=[15, 15] ra=160.794 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1280.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1320)
        self.assertEqual(str(tlist[0]),
                         "targetid=8 field=2009 filter=z exp_times=[15, 15] ra=232.794 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1320.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1360)
        self.assertEqual(str(tlist[0]),
                         "targetid=9 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1360.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1400)
        self.assertEqual(str(tlist[0]),
                         "targetid=10 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1400.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")

        tlist = self.scriptedprop.suggest_targets(1440)
        self.assertEqual(str(tlist[0]),
                         "targetid=11 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112 "
                         "ang=0.000 alt=0.000 az=0.000 rot=0.000 telalt=0.000 telaz=0.000 telrot=0.000 "
                         "time=1440.0 airmass=0.000 brightness=nan cloud=0.00 seeing=0.00 "
                         "visits=0 progress=0.00% "
                         "groupid=0 groupix=0 "
                         "need=0.000 bonus=0.000 value=1.000 propboost=1.000 "
                         "propid=[] need=[] bonus=[] value=[] propboost=[] "
                         "slewtime=0.000 costbonus=0.000 rank=0.000")
