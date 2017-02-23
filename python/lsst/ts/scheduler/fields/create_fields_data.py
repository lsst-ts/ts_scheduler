import palpy
import numpy
import sys
import math

__all__ = ["create_fields_data"]

def create_fields_data(tessellation_filename, fieldsdata_filename):
    iy = 04
    im = 12
    id = 1
    mjd = palpy.caldj(iy, im, id)
    input_array = numpy.loadtxt(tessellation_filename)
    output_array = []

    for row in input_array:
        ra = math.radians(row[0])
        dec = math.radians(row[1])
        (gl, gb) = palpy.eqgal(ra, dec)
        (el, eb) = palpy.eqecl(ra, dec, mjd)

        ra = math.degrees(ra)
        dec = math.degrees(dec)
        gl = math.degrees(gl)
        gb = math.degrees(gb)
        el = math.degrees(el)
        eb = math.degrees(eb)

        if gl > 180:
            gl = - (360 - gl)
        if gb > 180:
            gb = - (360 - gb)
        if el > 180:
            el = - (360 - el)
        if eb > 180:
            eb = - (360 - eb)

        output_array.append([ra, dec, gl, gb, el, eb])

    numpy.savetxt(fieldsdata_filename, output_array, "%.6f")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: python create_fields_data.py <tessellationFileName> <fieldsDataFileName>"
        print "The <tessellationFilename> should contain rows of ra dec values"
    else:
        create_fields_data(sys.argv[1], sys.argv[2])

    sys.exit(0)
