import unittest
import numpy
import sqlite3

from ts_scheduler.fields import *

class TestFieldGen(unittest.TestCase):

    def setUp(self):
        pass

    def test_add_gal_ecl(self):
        createTessellationFile("input", "output_unittest")

        orig = numpy.loadtxt("tessellationFields_UnitTest")
        calc = numpy.loadtxt("output_unittest")

        diff = orig - calc

        self.assertEqual(numpy.array_equal(orig, calc), True)

    def test_query_field_table(self):
        # https://docs.python.org/2/library/sqlite3.html
        # More examples are here

        conn = sqlite3.connect("Fields.db")
        cursor = conn.cursor()

        sql = "select fieldID, fieldFov, fieldRA, fieldDEC, fieldGL, fieldGB, fieldEL, fieldEB from Field limit 0,10"

        data = cursor.execute(sql)

        self.assertEqual(data.arraysize>0, True)

if __name__ == "__main__":
    unittest.main()
