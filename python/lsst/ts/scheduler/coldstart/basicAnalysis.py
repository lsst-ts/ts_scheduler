#!/usr/bin/env python

import time
import sys
import sqlite3

from database import *
from config import *


class basicAnalysis:
	"""I wanted to make the basicAnalysis class as decoupled as possible. Every
	definition will be it's own metric. There may be redundency when calculating 
	averages for example. However a user will be free to comment out any metrics
	they wish with no recoil. For ease of readbility, variables should be very
	explicit. If variable names contains an underscore, then I am refering to 
	either a whole table, or just a column form the database schema.
	"""

	db = database()
	c = db.connect()
	print("\nConnecting to " + db.path)

	# Constant that determines the order in which filters are printed in the filter count table
	FILTERS = [ "z", "y", "i", "r", "g", "u"]
	
	# Our data structures used to store all of the queries.
	obs_history_table = {"observationId": [], "night":[], "Field_fieldId":[],"filter":[]}
	obs_proposal_history_table = {"propHistId":[], "proposal_propId":[], "obsHistory_observationId":[]}
	slew_history_table = {"slewTime":[]}
	
	# List of tuples to store all proposals ex; [(1, "WideFastDeep", "General"), ...]
	proposals = []


	def __init__(self):
		"""Does the querying into the Database, then stores them into the data
		structures defined above as class vairables.
    	"""

		print("\n" + ("=" * 80) ) 
		print("CALCULATING METRICS...")
		print("-" * 80)

		for row in self.c.execute("SELECT observationId, night, Field_fieldId, filter FROM ObsHistory;"):	

			self.obs_history_table["observationId"].append(row[0])
			self.obs_history_table["night"].append(row[1])
			self.obs_history_table["Field_fieldId"].append(row[2])
			self.obs_history_table["filter"].append(row[3])

		for row in self.c.execute("SELECT propHistId, Proposal_propId, ObsHistory_observationId FROM ObsProposalHistory;"):
			
			self.obs_proposal_history_table["propHistId"].append(row[0])
			self.obs_proposal_history_table["proposal_propId"].append(row[1])
			self.obs_proposal_history_table["obsHistory_observationId"].append(row[2])

		for row in self.c.execute("SELECT slewTime FROM SlewHistory;"):
			
			self.slew_history_table["slewTime"].append(row[0])

		# Create a list of tuples of the proposals ex; (1, "WideFastDeep", "General")
		for row in self.c.execute("SELECT propId, propName, propType FROM Proposal;"):

			self.proposals.append((row[0],row[1],row[2],))


	def numberOfVisits(self):

		numberOfVisits = len(self.obs_history_table["night"])

		print("		number of visits: " + str(numberOfVisits))


	def numberOfNightsAndObserved(self):
		"""Print number of nights the survey took, as well as the number of
		nights that were observed. In other words excluding nights the 
		observatory was down for.
    	"""

		numberOfObservedNights = 1

		currentNight = self.obs_history_table["night"][0]

		for night in self.obs_history_table["night"]:

			if night == currentNight:
				continue
			else:
				numberOfObservedNights += 1
				currentNight = night

		print("		number of nights: " + str(self.obs_history_table["night"][-1]))
		print("		number of observed nights: " + str(numberOfObservedNights))


	def averageVisitsPerObservedNight(self):
		"""Prints the average visits the observatory did per night. Does not 
		count the nights the observatory was down for.
    	"""

		numberOfVisits = len(self.obs_history_table["night"]) * 1.0

		numberOfObservedNights = 1

		currentNight = self.obs_history_table["night"][0]

		for night in self.obs_history_table["night"]:

			if night == currentNight:
				continue
			else:
				numberOfObservedNights += 1
				currentNight = night

		averageVisitsPerObservedNights = round(numberOfVisits/numberOfObservedNights, 4)

		print("		avg visits/observed nights: " + str(averageVisitsPerObservedNights))


	def numberOfFilterChanges(self):
		"""Prints the total number of filter changes the observatory did."""
		
		filterChangeCounter = 0
		currentCamFilter = self.obs_history_table["filter"][0]

		for camFilter in self.obs_history_table["filter"]:			
			
			if camFilter == currentCamFilter:
				continue
			else:
				filterChangeCounter += 1
				currentCamFilter = camFilter

		print("		number of filter changes: " + str(filterChangeCounter))


	def avgFilterChangesPerObservedNight(self):
		"""Prints the average number of filter changes the observatory did per
		night. Does not count the nights the observatory was down for.
   		"""

		filterChangeCounter = 0.0
		currentCamFilter = self.obs_history_table["filter"][0]

		for camFilter in self.obs_history_table["filter"]:			
			
			if camFilter == currentCamFilter:
				continue
			else:
				filterChangeCounter += 1
				currentCamFilter = camFilter

		numberOfObservedNights = 1.0

		currentNight = self.obs_history_table["night"][0]

		for night in self.obs_history_table["night"]:

			if night == currentNight:
				continue
			else:
				numberOfObservedNights += 1
				currentNight = night

		avgFilterChangesPerNight = round(filterChangeCounter/numberOfObservedNights,4)

		print("		avg filer changes/observed nights: " + str(avgFilterChangesPerNight))


	def maxSlewTime(self):
		"""Prints the max slew time value found."""

		maxSlewTime = round(max(self.slew_history_table["slewTime"]),4)

		print("		max slew time: " + str(maxSlewTime))


	def minSlewTime(self):
		"""Prints the minimum slew time found."""

		minSlewTime = round(min(self.slew_history_table["slewTime"]),4)

		print("		min slew time: " + str(minSlewTime))


	def avgSlewTime(self):
		"""Prints the average slew time the observatory underwent."""

		totalSlewTime = 0
		slewTimeCount = len(self.slew_history_table["slewTime"])

		for slewTime in self.slew_history_table["slewTime"]:
			totalSlewTime += slewTime

		avgSlewTime = round(totalSlewTime/slewTimeCount, 4)

		print("		avg slew time: " + str(avgSlewTime))


	def numberOfVisitsPerProposal(self):
		"""Prints the total number of visits each proposal accounted for. Note
		there is a possibility that multiple proposals account for a single
		visit. This allows for the very likely possibility of the total visit
		count by each proposal exceeding the actual counted visit count. 
		"""

		numberOfVisits = len(self.obs_history_table["night"]) * 1.0

		proposalIdCounter = {}

		# This is not the same as the total amount of visits. One visit may
		# account for two proposals, that total is what this variable captures.
		proposalVisitTotal = 0
		
		# Count the total number of visits every proposal ID counted for
		for each in self.obs_proposal_history_table["proposal_propId"]:

			if each in proposalIdCounter:
				proposalIdCounter[each] += 1
			else:
				proposalIdCounter[each] = 1

		# Get the total across all proposals
		for propTuple in self.proposals:

			propId = propTuple[0]
			proposalVisitTotal += proposalIdCounter[propId]

		# Print each proposals information into a decent looking table
		print("		Visits accounted for in each proposal")
		print("		" + "-"*42)
		
		total = 0
		totalPercent = 0.0

		for propTuple in self.proposals:

			name = (propTuple[1][:13] + '..') if len(propTuple[1]) > 15 else propTuple[1]
			count = proposalIdCounter[propTuple[0]]
			percent = round(( (count * 1.0) / (numberOfVisits * 1.0) ) * 100,4)
			
			total += count
			# I dont round here until the print so we have a more accurate percentage
			totalPercent += ( (count * 1.0) / (numberOfVisits * 1.0) ) * 100

			print("		{:<15} : {:>10} {:>12}%".format(name, str(count), str(percent)))
		
		print("		" + "-"*42)
		print("		Total           : {:>10} {:>12}%".format(total, round(totalPercent,4)))


	def numberOfVisitsInEachFilterPerProposal(self):
		"""Because we load only tables and reduce run time by limiting our sql calls,
		we do a python equivilent of a sql "join". The explicit naming convention is
		meant to clarify any ambiguity. Here we are using one tables unique key to
		guide is in another table.  
		"""  
		
		# Will look something like {"proposal Id" : {"filter Id" : "count"} }
		numberOfVisitsPerFilterPerProposal = {}

		# Our columns that we will need to traverse to calculate this metric
		obs_proposal_history_propId_col = self.obs_proposal_history_table["proposal_propId"]
		obs_proposal_history_obsHistoryId_col = self.obs_proposal_history_table["obsHistory_observationId"]
		obs_history_filter_col = self.obs_history_table["filter"]

		# Start by itertating through all exposures made on behalf of a proposal,
		# may be more than the amount of exposures physically made since one exposure
		# can count for more than one proposal
		for i in range(len(obs_proposal_history_propId_col)):

			proposalId = obs_proposal_history_propId_col[i]

			# Our arrays start at 0, the unique id's we derive indexes from do not, 
			# so subtract 1 to accomodate for this caveat			
			indexToObsHistory = obs_proposal_history_obsHistoryId_col[i]-1

			# Retieve the filter which is in another table that was made on behalf of this exposure
			filterForThisProposal = obs_history_filter_col[indexToObsHistory]

			# If the proposal already exists in our dictionary
			if proposalId in numberOfVisitsPerFilterPerProposal:
				
				# AND if the the filter exists in that then increment its count
				if filterForThisProposal in numberOfVisitsPerFilterPerProposal[proposalId]:
					numberOfVisitsPerFilterPerProposal[proposalId][filterForThisProposal] += 1

				# If the filter does not exist create it and set it to 1
				else:
					numberOfVisitsPerFilterPerProposal[proposalId][filterForThisProposal] = 1

			# If the proposal is not in the dictinary, add it along with its filter set to 1
			else:
				numberOfVisitsPerFilterPerProposal[proposalId] = {}
				numberOfVisitsPerFilterPerProposal[proposalId][filterForThisProposal] = 1

		
		print("		Visits in each filter per proposal")
		print("		" + "-"*64)
		
		for propTuple in self.proposals:

			propId = propTuple[0]
			name = (propTuple[1][:13] + '..') if len(propTuple[1]) > 15 else propTuple[1]
			propFilters = []

			# Iterate through all possible filters, checking to see if this proposal has some
			for filterId in self.FILTERS:

				# If the proposal did indeed have some visits on this filter add it to our list
				if filterId in numberOfVisitsPerFilterPerProposal[propId]:
					propFilters.append(numberOfVisitsPerFilterPerProposal[propId][filterId])
				# Otherwise add a 0
				else:
					propFilters.append(0)

			print("		{:<15} : {:>6}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}".format(name, *propFilters ) )
		print("		" + "-"*64)
		print("		{:>16}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}".format(" ", "z", "y", "i", "r", "g", "u"))


	def totalTimeSpent(self):

		# Take advantage of work that has been done in database.py to find log file
		r = re.compile('\w*_(' + self.db.dbNumber + ').(log)')
		
		try:
			logFile = filter(r.match, self.db.logFiles)[0]
		except Exception as e:
			print("		Could not find logfile, omitting 'totalTimeSpent' metric")
			return

		logFilePath = LOG_DIRECTORY + logFile

		# Open the log file and print the time spent line
		fopen = open(logFilePath, "r")
		for line in fopen:
			
			if "Total running time" in line:

				# Remove junk in the line
				timeLine = line.split("-")[-1][1:]

				# Extract only the time and convert to float
				timeSec = float(timeLine.split("=")[-1][1:].split(" ")[0])

				# Seconds to hours, minutes, seconds conversion
				m, s = divmod(timeSec, 60)
				h, m = divmod(m, 60)
				
				print("		Total running time (s)    : " + str(timeSec))
				print("		Total running time (h,m,s): %d:%02d:%02d" % (h, m, s))


	def maxImmediateVisit(self):
		"""Print the max number of times a field was revisited within the same night"""

		# We ignore sequence proposals when finding max visit value
		ignoredPropIds = []

		for propTuple in self.proposals:
			if propTuple[2] == "Sequence":
				ignoredPropIds.append(propTuple[0])

		# Grab the lists we will use, including the unique key to foriegn ones
		propIds = self.obs_proposal_history_table["proposal_propId"]
		foriegnKeys = self.obs_proposal_history_table["obsHistory_observationId"]
		
		filterIds = self.obs_history_table["filter"]
		fieldIds = self.obs_history_table["Field_fieldId"]
		nights = self.obs_history_table["night"]
		uniqueKeys = self.obs_history_table["observationId"]

		# Max visit counting begins at 1, which is just a regular visit		
		maxVisit = 1
		maxVisitTemp = 1

		# Making out first tuple to make looping logic more readable  
		lastObsProp = (propIds[0], filterIds[0], fieldIds[0], nights[0])

		for i in range(len(propIds)):
			
			# We already made the first ObsProp so skip the first
			if i == 0:
				continue

			# Create an observation proposal tuple
			propId = propIds[i]
			foriegnKey = foriegnKeys[i]-1 # -1 for 0-based indexing 
			filterId = filterIds[foriegnKey]
			field = fieldIds[foriegnKey]
			night = nights[foriegnKey]

			thisObsProp = (propId, filterId, field, night)

			# Now compare the two, while maintaining maxVisit count

			# If its the same proposal
			if thisObsProp[0] == lastObsProp[0] and thisObsProp[0] not in ignoredPropIds:
				# And the same field
				if thisObsProp[2] == lastObsProp[2]:
					# And it's the same night
					if thisObsProp[3] == lastObsProp[3]:
						maxVisitTemp += 1

			# Otherwise, reset the counter
					else:
						maxVisitTemp = 1
				else:
					maxVisitTemp = 1
			else:
				maxVisitTemp = 1

			# If the temp max holder is ever greater than the global 
			if maxVisitTemp > maxVisit:
				maxVisit = maxVisitTemp

			# This ObsProp will now be the last one for the next loop
			lastObsProp = thisObsProp

		print("		Max immediate field visit: " + str(maxVisit))

	def maxNightlyVisit(self):
		"""Print the max number of times a field was revisited within the same
		night for every proposal within a neat table.
		"""

		# We ignore sequence proposals when finding max visit value
		ignoredPropIds = []

		for propTuple in self.proposals:
			if propTuple[2] == "Sequence":
				ignoredPropIds.append(propTuple[0])

		# Grab the lists we will use, including the unique key to foriegn ones
		propIds = self.obs_proposal_history_table["proposal_propId"]
		foriegnKeys = self.obs_proposal_history_table["obsHistory_observationId"]
		
		filterIds = self.obs_history_table["filter"]
		fieldIds = self.obs_history_table["Field_fieldId"]
		nights = self.obs_history_table["night"]
		uniqueKeys = self.obs_history_table["observationId"]

		# Will need this for loop logic
		lastNight = nights[0]

		# Data struct to store the field winners of the survey
		winners = {}

		# Data struct to store all field id counts for the night
		contestants = {}

		for i in range(len(propIds)):
			
			# Create an observation proposal tuple
			propId = propIds[i]
			foriegnKey = foriegnKeys[i]-1 # -1 for 0-based indexing 
			filterId = filterIds[foriegnKey]
			field = fieldIds[foriegnKey]
			thisNight = nights[foriegnKey]

			# The night has changed, or it's the last night to be considered
			if lastNight != thisNight or i == len(propIds)-1:

				# Data struct to hold the field counts that will be compared
				# with the winners every night change.
				challengers = {}
				
				# For every propId that participated this night
				for contestantPropId in contestants:

					# Find out what field had the highest count
					highestFieldCount = 1
					highestFieldProp = {}
					for contestantField in contestants[contestantPropId]:

						thisFieldCount = contestants[contestantPropId][contestantField]

						if  thisFieldCount > highestFieldCount:

							highestFieldCount = thisFieldCount
							highestFieldProp = {contestantPropId:{"field":contestantField, "count":thisFieldCount, "night":lastNight}}

					# The winner of this propId/night found, add to challenger list
					challengers.update(highestFieldProp)
				


				# We have the challengers for this night, compare them to current winners
				for challengerPropId in challengers:

					if challengerPropId in winners:

						if challengers[challengerPropId]["count"] > winners[challengerPropId]["count"]:

							winners[challengerPropId] = challengers[challengerPropId]

					else:
						winners[challengerPropId] = challengers[challengerPropId]

				# Change the night and clear the contestants for a new collection
				lastNight = thisNight
				contestants.clear()
				# We ignored an observation because the night has changed, so add it now or we lose it
				contestants[propId] = {field:1}

			# If the night has not changed, keep tallying fields
			else:
				# If we already had this propId in contestant list
				if propId in contestants:

					# And if this field was already accounted for within this propId
					if field in contestants[propId]:

						# Increment its field counter
						contestants[propId][field] += 1

					# If the field has not been accounted for within this propId
					else: 
						contestants[propId][field] = 1

				# If the propId has not been seen within the night add it
				else:
					contestants[propId] = {field:1}


		print("		Max nightly revisit count")
		print("		" + "-"*44)

		# Print out the winners, loop by the self.proposals so we know the names
		for propTuple in self.proposals:

			# Check to see if that propId is in the winners list (Will only ever not be if the survey was too short)
			if propTuple[0] not in winners:
				continue

			name = (propTuple[1][:13] + '..') if len(propTuple[1]) > 15 else propTuple[1]
			fieldId = winners[propTuple[0]]["field"]
			count = winners[propTuple[0]]["count"]
			night = winners[propTuple[0]]["night"]

			print("		{:<15} : {:>8} {:>8} {:>8}".format(name, fieldId, count, night))
		print("		" + "-"*44)
		print("		{:<15}   {:>8} {:>8} {:>8}".format(" ", "fieldId", "count", "night"))



ba = basicAnalysis()

ba.numberOfVisits()
ba.numberOfNightsAndObserved()
ba.averageVisitsPerObservedNight()
print("")

ba.numberOfFilterChanges()
ba.avgFilterChangesPerObservedNight()
print("")

ba.maxSlewTime()
ba.minSlewTime()
ba.avgSlewTime()
print("")

ba.maxImmediateVisit()
print("")

ba.maxNightlyVisit()
print("")

ba.numberOfVisitsPerProposal()
print("")

ba.numberOfVisitsInEachFilterPerProposal()
print("")

ba.totalTimeSpent()
print("")
