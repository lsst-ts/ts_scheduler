import unittest

from lsst.ts.scheduler.fields import FieldSelection

class FieldSelectionTest(unittest.TestCase):

    def setUp(self):
        self.fs = FieldSelection()

        self.truth_base_query = "select * from Field"
        self.truth_galactic_exclusion = '(abs(fieldGB) > (10.0 - (9.9 * abs(fieldGL)) / 90.0))'
        self.truth_galactic_region = '(abs(fieldGB) <= (10.0 - (9.9 * abs(fieldGL)) / 90.0))'
        self.truth_normal_ra_region = 'fieldRA between 90.0 and 270.0'
        self.truth_cross_region = '(fieldRA between 270.0 and 360 or fieldRA between 0 and 90.0)'
        self.truth_normal_dec_region = 'fieldDec between -90.0 and -61.0'

    def test_base_select(self):
        self.assertEqual(self.fs.base_select(), self.truth_base_query)

    def test_finish_query(self):
        query = "silly query"
        self.assertEqual(self.fs.finish_query(query), query + ";")

    def test_galactic_region(self):
        self.assertEqual(self.fs.galactic_region(10.0, 0.1, 90.0), self.truth_galactic_exclusion)
        self.assertEqual(self.fs.galactic_region(10.0, 0.1, 90.0, exclusion=False),
                         self.truth_galactic_region)

    def test_select_region(self):
        self.assertEqual(self.fs.select_region("fieldRA", 90.0, 270.0), self.truth_normal_ra_region)
        self.assertEqual(self.fs.select_region("fieldRA", 270.0, 90.0), self.truth_cross_region)

    def test_combine_queries(self):
        query1 = self.fs.select_region("fieldRA", 90.0, 270.0)
        query2 = self.fs.select_region("fieldDec", -90.0, -61.0)
        combiners = ("and",)

        truth_query_parts = [self.truth_base_query]
        truth_query_parts.append("where")
        truth_query_parts.append(query1)
        truth_query_parts.append(combiners[0])
        truth_query_parts.append(query2)
        truth_query_parts.append("order by fieldId")

        truth_query = " ".join(truth_query_parts) + ";"
        self.assertEqual(self.fs.combine_queries(combiners, query1, query2), truth_query)

    def test_bad_combine_queries(self):
        query1 = self.fs.select_region("fieldRA", 90.0, 270.0)
        query2 = self.fs.select_region("fieldDec", -90.0, -61.0)
        combiners = ()
        with self.assertRaises(RuntimeError):
            self.fs.combine_queries(combiners, query1, query2)

        combiners = ("and",)
        with self.assertRaises(RuntimeError):
            self.fs.combine_queries(combiners, query1)
