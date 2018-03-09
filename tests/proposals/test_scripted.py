from builtins import str
import os
import logging
import unittest
import warnings

from lsst.ts.astrosky.model import AstronomicalSkyModel
from lsst.ts.dateloc import ObservatoryLocation
from lsst.ts.scheduler.kernel import read_conf_file, conf_file_path
from lsst.ts.scheduler.proposals import ScriptedProposal

class ScriptedProposalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings('ignore', category=FutureWarning, append=True)
        location = ObservatoryLocation()
        location.for_lsst()
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
        self.assertEqual(str(tlist[0])[:71],
                         "targetid=0 field=2001 filter=r exp_times=[15, 15] ra=85.721 dec=-14.442")

        tlist = self.scriptedprop.suggest_targets(1641091040)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=1 field=2002 filter=r exp_times=[15, 15] ra=229.721 dec=-14.442")

        tlist = self.scriptedprop.suggest_targets(1641091080)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=2 field=2003 filter=r exp_times=[15, 15] ra=130.279 dec=-14.442")

        tlist = self.scriptedprop.suggest_targets(1641091120)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=3 field=2004 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441")

        tlist = self.scriptedprop.suggest_targets(1641091160)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=4 field=2005 filter=i exp_times=[15, 15] ra=346.279 dec=-14.441")

        tlist = self.scriptedprop.suggest_targets(1641091200)
        self.assertEqual(str(tlist[0])[:71],
                         "targetid=5 field=2006 filter=i exp_times=[15, 15] ra=13.721 dec=-14.441")

        tlist = self.scriptedprop.suggest_targets(1641091240)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=6 field=2007 filter=z exp_times=[15, 15] ra=199.206 dec=-14.112")

        tlist = self.scriptedprop.suggest_targets(1641091280)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=7 field=2008 filter=z exp_times=[15, 15] ra=160.794 dec=-14.112")

        tlist = self.scriptedprop.suggest_targets(1641091320)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=8 field=2009 filter=z exp_times=[15, 15] ra=232.794 dec=-14.112")

        tlist = self.scriptedprop.suggest_targets(1641091360)
        self.assertEqual(str(tlist[0])[:72],
                         "targetid=9 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112")

        tlist = self.scriptedprop.suggest_targets(1641091400)
        self.assertEqual(str(tlist[0])[:73],
                         "targetid=10 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112")

        tlist = self.scriptedprop.suggest_targets(1641091440)
        self.assertEqual(str(tlist[0])[:73],
                         "targetid=11 field=2010 filter=y exp_times=[15, 15] ra=127.206 dec=-14.112")
