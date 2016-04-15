import sys
import sqlite3

def printUsage():
    print "Usage: python createFieldsDB.py"

def createFieldsDB() :
    conn = sqlite3.connect("Fields.db")
    conn.close()

if __name__ == "__main__" :
    if len(sys.argv) != 1:
        printUsage()
    else :
        createFieldsDB()
    sys.exit(0)
