import palpy
import numpy
import sys
import math

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
        (l, b) = palpy.eqgal(ra, dec)
        (el, eb) = palpy.eqecl(ra, dec, mjd)

        ra = math.degrees(ra)
        dec = math.degrees(dec)
        l = math.degrees(l)
        b = math.degrees(b)
        el = math.degrees(el)
        eb = math.degrees(eb)

        if l > 180:
            l = - (360 - l)
        if b > 180:
            b = - (360 - b)
        if el > 180:
            el = - (360 - el)
        if eb > 180:
            eb = - (360 - eb)

        output_array.append([ra, dec, l, b, el, eb])

    numpy.savetxt(fieldsdata_filename, output_array, "%.6f")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: python createFieldsData.py <tessellationFileName> <fieldsDataFileName>"
        print "The <tessellationFilename> should contain rows of ra dec values"
    else:
        create_fields_data(sys.argv[1], sys.argv[2])

    sys.exit(0)
