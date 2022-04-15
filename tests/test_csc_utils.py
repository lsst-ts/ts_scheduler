# This file is part of ts_scheduler
#
# Developed for Vera C. Rubin Observatory.
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

import unittest

from lsst.ts.scheduler.utils.csc_utils import is_uri


class TestCSCUtils(unittest.TestCase):
    def test_is_uri_with_valid_uris(self):

        for valid_uri in self.get_valid_uris():
            assert is_uri(valid_uri)

    def test_is_uri_with_invalid_uris(self):

        for invalid_uri in self.get_invalid_uris():
            assert not is_uri(invalid_uri)

    def get_valid_uris(self):

        return [
            "file:///home/saluser/rubin_sim_data/fbs_scheduler_2022-04-01T15:49:53.662.p",
            "https://s3.cp.lsst.org/rubinobs-lfa-cp/Scheduler:2/Scheduler:2/2022/02/17/Scheduler:2_Scheduler:2_2022-02-18T09:26:04.347.p",  # noqa
        ]

    def get_invalid_uris(self):

        return [
            "/home/saluser/rubin_sim_data/fbs_scheduler_2022-04-01T15:49:53.662.p",
            "",
        ]
