import palpy
import math
import numpy
import sys

def printUsage():
    print "Usage: python AddGalEcl.py <packFileName> <outputFileName>"
    print "The <packfile> should contain rows of ra dec values"

def createTessellationFile(packFileName, outputFileName):
    iy = 04
    im = 12
    id = 1
    mjd = palpy.caldj(iy, im, id)
    input_array = numpy.loadtxt(packFileName)
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

    numpy.savetxt(outputFileName, output_array, "%.6f")

if __name__ == "__main__" :
    if len(sys.argv) != 3:
        printUsage()
    else :
        createTessellationFile(sys.argv[1], sys.argv[2])

    sys.exit(0)
