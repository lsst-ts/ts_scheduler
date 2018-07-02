import sqlite3
from database import *

db = database()
c = db.connect()
c.execute(("SELECT ra, dec, observationStartMJD, visitExposureTime, " 
"filter, angle, numExposures, airmass, seeingFwhmEff, seeingFwhmGeom, "
"skyBrightness, night, slewTime, fiveSigmaDepth, " 
"altitude, azimuth, cloud, moonAlt, sunAlt, note, Field_fieldId, proposal_propId "
"FROM ObsHistory JOIN SlewHistory ON (ObsHistory.observationId = SlewHistory.ObsHistory_observationId) JOIN "
"ObsProposalHistory ON (ObsHistory.observationId = ObsProposalHistory.ObsHistory_observationId)"))
#"FROM ObsHistory JOIN SlewHistory ON (observationId = ObsHistory_observationId) JOIN "
#"ObsProposalHistory ON (ObsHistory.observationId = ObsProposalHistory.ObsHistory_observationId)"))



print(c.fetchall()[0])

