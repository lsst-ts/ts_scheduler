import sys
import os
import time
import sqlite3

def printUsage():
    print "Usage: python createFieldsDB.py"

def createFieldsDB(dbfilename = "Fields.db") :

    if os.path.isfile(dbfilename):
        timestr = time.strftime(".%Y-%m-%d_%H:%M:%S")
        os.rename(dbfilename, dbfilename + timestr)

    conn = sqlite3.connect(dbfilename)
    conn.close()

if __name__ == "__main__" :
    if len(sys.argv) != 1:
        printUsage()
    else :
        createFieldsDB()
    sys.exit(0)
