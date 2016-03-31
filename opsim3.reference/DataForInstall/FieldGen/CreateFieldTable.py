import math
import numpy
import sys
import sqlite3

FOV = 3.5

def printUsage():
    print "Usage: python CreateFieldTable.py <tessellationFieldsFile>"
    print "The <tessellationFieldsFile> is the output of AddGalEcl script"

def createTessellationDB(tessellationFieldsFile):
    conn = sqlite3.connect("Fields.db")
    cursor = conn.cursor()

    sql = "delete from Field"
    print "Deleting data from Field"
    cursor.execute(sql)

    print "Reading %s file" % tessellationFieldsFile
    input_array = numpy.loadtxt(tessellationFieldsFile)

    print "Inserting data into Field table"
    fieldID = 1
    for row in input_array:
        data_string = ','.join([str(x) for x in row])
        sql = "insert into Field values (%s,%s,%s)" % (str(fieldID),str(FOV),data_string)
        print sql
        cursor.execute(sql)
        fieldID = fieldID + 1
    conn.commit()
    conn.close()
    print "Done Inserting data into Field table"

    return

if __name__ == "__main__" :
    if len(sys.argv) != 2:
        printUsage()
    else :
        createTessellationDB(sys.argv[1])

    sys.exit(0)
