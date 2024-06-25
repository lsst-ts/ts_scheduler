# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from lsst.ts.salobj.type_hints import BaseDdsDataType

__all__ = ["SurveyTopology"]


class SurveyTopology:
    """Stores information about survey topology.

    Survey topology is basically an account of how many proposals are defined,
    the type of proposal and their names.
    """

    def __init__(self) -> None:
        self.num_general_props = 0
        self.num_seq_props = 0

        self.general_propos = []
        self.sequence_propos = []

    @property
    def num_props(self) -> int:
        """Total number of proposals."""
        return self.num_seq_props + self.num_general_props

    def from_topic(self, topic: BaseDdsDataType) -> None:
        """Update internal information from the topic data."""

        self.num_general_props = topic.num_general_props
        self.num_seq_props = topic.num_seq_props

        self.general_propos = topic.general_propos.split(",")
        self.sequence_propos = topic.sequence_propos.split(",")

    def as_dict(self) -> dict[str, int | list[str]]:
        """Return survey topology as a dictionary.

        Returns
        -------
        `dict`
            Dictionary with survey topology data.
        """

        return dict(
            numGeneralProps=self.num_general_props,
            numSeqProps=self.num_seq_props,
            generalPropos=",".join(self.general_propos),
            sequencePropos=",".join(self.sequence_propos),
        )
