import sys

from ts_scheduler.fields import create_fields_db
from ts_scheduler.fields import create_fields_table
from ts_scheduler.fields import create_fields_data
from ts_scheduler.fields import ingest_fields_data

if __name__ == "__main__":

    dbfilename = "Fields.db"
    datafilename = "Fields.txt"
    create_fields_db(dbfilename)
    create_fields_table(dbfilename)
    create_fields_data("tessellationInput.txt", datafilename)
    ingest_fields_data(dbfilename, datafilename)

    sys.exit(0)
