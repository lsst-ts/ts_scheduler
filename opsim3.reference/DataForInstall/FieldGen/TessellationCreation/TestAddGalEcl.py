import unittest
from AddGalEcl import *
import numpy

class TestAddGalEcl(unittest.TestCase):

    def setUp(self):
        pass

    def test_add_gal_ecl(self):
        createTessellationFile("input", "output_unittest")

        orig = numpy.loadtxt("tessellationFields_UnitTest")
        calc = numpy.loadtxt("output_unittest")

        diff = orig - calc

        print diff
        print diff > .01

        self.assertEqual(numpy.array_equal(orig, calc), True)

if __name__ == "__main__":
    unittest.main()
