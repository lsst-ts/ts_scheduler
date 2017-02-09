import sys

from lsst.ts.scheduler.fields import create_fields_db, create_fields_table
from lsst.ts.scheduler.fields import create_fields_data, ingest_fields_data

if __name__ == "__main__":

    dbfilename = "Fields.db"
    datafilename = "Fields.txt"
    create_fields_db(dbfilename)
    create_fields_table(dbfilename)
    create_fields_data("tessellationInput.txt", datafilename)
    ingest_fields_data(dbfilename, datafilename)

    sys.exit(0)
