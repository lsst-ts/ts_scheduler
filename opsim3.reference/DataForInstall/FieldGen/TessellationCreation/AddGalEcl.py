#include "slalib.h"
#include <stdio.h>

#int main(int argc, char **argv)
#{
#  double ra, dec, l, b, mjd, el, eb;
#  double deg_to_rad = M_PI/180.0;
#  int ok;

#  int iy = 04;
#  int im = 12;
#  int id = 1;
#  slaCaldj (iy, im, id, &mjd, &ok);
#  fprintf(stderr,"mjd = %lf\n", mjd);
#  while (scanf("%lf %lf %ld", &ra, &dec, &id) == 3) {
#    ra *= deg_to_rad;
#    dec *= deg_to_rad;
#    slaEqgal(ra, dec, &l, &b);
#    slaEqecl(ra, dec, mjd, &el, &eb);
#    printf("%ld %lf %lf %lf %lf %lf %lf\n", id, ra/deg_to_rad, dec/deg_to_rad, l/deg_to_rad, b/deg_to_rad, el/deg_to_rad, eb/deg_to_rad);
#  }
#}

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
