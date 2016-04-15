import sys
import sqlite3

def printUsage():
    print "Usage: python createFieldsTable.py"

def createFieldsTable() :
    conn = sqlite3.connect("Fields.db")
    cursor = conn.cursor()

    sql = "CREATE TABLE Field(fieldID INT PRIMARY KEY NOT NULL, fieldFov REAL NOT NULL, fieldRA REAL NOT NULL, fieldDEC REAL NOT NULL, fieldGL REAL NOT NULL, fieldGB REAL NOT NULL, fieldEL REAL NOT NULL, fieldEB REAL NOT NULL);"
    print "Creating Field Table"
    cursor.execute(sql)
    conn.commit()
    conn.close()

if __name__ == "__main__" :
    if len(sys.argv) != 1:
        printUsage()
    else :
        createFieldsTable()
    sys.exit(0)
