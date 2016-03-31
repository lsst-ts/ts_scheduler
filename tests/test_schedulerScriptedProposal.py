import unittest

from ts_scheduler.schedulerDefinitions import read_conf_file, conf_file_path
from ts_scheduler.schedulerScriptedProposal import ScriptedProposal
from ts_scheduler.observatoryModel import ObservatoryLocation
from ts_scheduler.sky_model import AstronomicalSkyModel

class ScriptedProposalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        site_confdict = read_conf_file(conf_file_path(__name__, "../conf", "system", "site.conf"))
        location = ObservatoryLocation()
        location.configure(site_confdict)
        cls.skyModel = AstronomicalSkyModel(location)

    def setUp(self):
        self.scriptedprop = ScriptedProposal(conf_file_path(__name__, "../conf", "survey",
                                             "scriptedProp1.conf"), self.skyModel)

    def test_init(self):
        self.assertEqual(len(self.scriptedprop.targetsList), 10)

    def test_suggest_targets(self):
        tlist = self.scriptedprop.suggest_targets(1000)
        self.assertEqual(str(tlist[0]), "ID=0 field=2001 filter=r ra=85.721 dec=-14.442 "
                         "time=1000.0 skybrightness=20.970")

        tlist = self.scriptedprop.suggest_targets(1040)
        self.assertEqual(str(tlist[0]), "ID=1 field=2002 filter=r ra=229.721 dec=-14.442 "
                         "time=1040.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1080)
        self.assertEqual(str(tlist[0]), "ID=2 field=2003 filter=r ra=130.279 dec=-14.442 "
                         "time=1080.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1120)
        self.assertEqual(str(tlist[0]), "ID=3 field=2004 filter=i ra=346.279 dec=-14.441 "
                         "time=1120.0 skybrightness=19.818")

        tlist = self.scriptedprop.suggest_targets(1160)
        self.assertEqual(str(tlist[0]), "ID=4 field=2005 filter=i ra=346.279 dec=-14.441 "
                         "time=1160.0 skybrightness=19.816")

        tlist = self.scriptedprop.suggest_targets(1200)
        self.assertEqual(str(tlist[0]), "ID=5 field=2006 filter=i ra=13.721 dec=-14.441 "
                         "time=1200.0 skybrightness=20.220")

        tlist = self.scriptedprop.suggest_targets(1240)
        self.assertEqual(str(tlist[0]), "ID=6 field=2007 filter=z ra=199.206 dec=-14.112 "
                         "time=1240.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1280)
        self.assertEqual(str(tlist[0]), "ID=7 field=2008 filter=z ra=160.794 dec=-14.112 "
                         "time=1280.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1320)
        self.assertEqual(str(tlist[0]), "ID=8 field=2009 filter=z ra=232.794 dec=-14.112 "
                         "time=1320.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1360)
        self.assertEqual(str(tlist[0]), "ID=9 field=2010 filter=y ra=127.206 dec=-14.112 "
                         "time=1360.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1400)
        self.assertEqual(str(tlist[0]), "ID=10 field=2010 filter=y ra=127.206 dec=-14.112 "
                         "time=1400.0 skybrightness=nan")

        tlist = self.scriptedprop.suggest_targets(1440)
        self.assertEqual(str(tlist[0]), "ID=11 field=2010 filter=y ra=127.206 dec=-14.112 "
                         "time=1440.0 skybrightness=nan")
