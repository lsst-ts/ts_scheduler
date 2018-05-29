
__all__ = ['SurveyTopology']


class SurveyTopology(object):

    def __init__(self):

        # self.num_props = 0
        self.num_general_props = 0
        self.num_seq_props = 0

        self.general_propos = []
        self.sequence_propos = []

    @property
    def num_props(self):
        return self.num_seq_props+self.num_general_props

    def from_topic(self, topic):

        self.num_general_props = topic.num_general_props
        self.num_seq_props = topic.num_seq_props

        # self.num_props = self.num_general_props + self.num_seq_props

        self.general_propos = topic.general_propos.split(',')
        self.sequence_propos = topic.sequence_propos.split(',')

    def to_topic(self):

        from SALPY_scheduler import scheduler_surveyTopologyC

        topic = scheduler_surveyTopologyC()

        topic.num_general_props = self.num_general_props
        topic.num_seq_props = self.num_seq_props

        general_propos = ''
        for i,gen_prop in enumerate(self.general_propos):
            general_propos += gen_prop
            if i < self.num_general_props:
                general_propos += ','

        topic.general_propos = general_propos

        sequence_propos = ''
        for i, seq_prop in enumerate(self.sequence_propos):
            sequence_propos += seq_prop
            if i < self.num_seq_props:
                sequence_propos += ','

        topic.sequence_propos = sequence_propos

        return topic
