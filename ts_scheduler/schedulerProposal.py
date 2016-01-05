from schedulerDefinitions import readConfFile

class schedulerProposal(object):
    def __init__(self, log, configFilePath):

        self.log = log

        self.propConfigDict, pairs = readConfFile(configFilePath)

        return

    def startSurvey(self):

        return

    def endSurvey(self):

        return

    def startNight(self):

        return

    def endNight(self):

        return

    def suggestTargets(self):

        return
