# This file is part of ts_scheduler
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

__all__ = ["SurveyTopology"]


class SurveyTopology(object):
    def __init__(self):

        # self.num_props = 0
        self.num_general_props = 0
        self.num_seq_props = 0

        self.general_propos = []
        self.sequence_propos = []

    @property
    def num_props(self):
        return self.num_seq_props + self.num_general_props

    def from_topic(self, topic):

        self.num_general_props = topic.num_general_props
        self.num_seq_props = topic.num_seq_props

        # self.num_props = self.num_general_props + self.num_seq_props

        self.general_propos = topic.general_propos.split(",")
        self.sequence_propos = topic.sequence_propos.split(",")

    def to_topic(self, topic):
        """

        Parameters
        ----------
        topic

        Returns
        -------

        """
        topic.numGeneralProps = self.num_general_props
        topic.numSeqProps = self.num_seq_props

        general_propos = ""
        for i, gen_prop in enumerate(self.general_propos):
            general_propos += gen_prop
            if i < self.num_general_props - 1:
                general_propos += ","

        topic.generalPropos = general_propos

        sequence_propos = ""
        for i, seq_prop in enumerate(self.sequence_propos):
            sequence_propos += seq_prop
            if i < self.num_seq_props - 1:
                sequence_propos += ","

        topic.sequencePropos = sequence_propos

        return topic
