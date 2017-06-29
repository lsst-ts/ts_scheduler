from __future__ import print_function
from builtins import str
import numpy
import sys
import sqlite3

__all__ = ["ingest_fields_data"]

FOV = 3.5

def ingest_fields_data(dbfilename, fieldsdatafilename):
    conn = sqlite3.connect(dbfilename)
    cursor = conn.cursor()

    sql = "delete from Field"
    cursor.execute(sql)

    input_array = numpy.loadtxt(fieldsdatafilename)

    field_id = 1
    for row in input_array:
        data_string = ','.join([str(x) for x in row])
        sql = "insert into Field values (%s,%s,%s)" % (str(field_id), str(FOV), data_string)
        cursor.execute(sql)
        field_id = field_id + 1
    conn.commit()
    conn.close()

    return


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python CreateFieldTable.py <tessellationFieldsFile>")
        print("The <tessellationFieldsFile> is the output of AddGalEcl script")
    else:
        ingest_fields_data(sys.argv[1])

    sys.exit(0)
