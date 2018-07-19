import sqlite3
from database import *



def get_observation_history():
    '''queries the opsim database and returns a list of past observations for cold start'''
    db = database()
    c = db.connect()
    c.execute(("SELECT ra, dec, observationStartMJD, visitExposureTime, " 
    "filter, angle, numExposures, airmass, seeingFwhmEff, seeingFwhmGeom, "
    "skyBrightness, night, slewTime, fiveSigmaDepth, " 
    "altitude, azimuth, cloud, moonAlt, sunAlt, note, Field_fieldId, proposal_propId FROM ObsHistory "
    "JOIN SlewHistory ON (ObsHistory.observationId = SlewHistory.ObsHistory_observationId) JOIN "
    "ObsProposalHistory ON (ObsHistory.observationId = ObsProposalHistory.ObsHistory_observationId)"))
    
    obslist = []
    for obs in c.fetchall():
        pass

    c.close()

print(c.fetchall()[0])

