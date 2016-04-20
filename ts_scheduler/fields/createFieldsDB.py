import sys
import os
import time
import sqlite3

def create_fields_db(dbfilename="Fields.db"):

    if os.path.isfile(dbfilename):
        timestr = time.strftime(".%Y-%m-%d_%H:%M:%S")
        os.rename(dbfilename, dbfilename + timestr)

    conn = sqlite3.connect(dbfilename)
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print "Usage: python create_fields_db.py"
    else:
        create_fields_db()
    sys.exit(0)
