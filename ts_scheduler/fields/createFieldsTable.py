import sys
import sqlite3

def create_fields_table(dbfilename="Fields.db"):
    conn = sqlite3.connect(dbfilename)
    cursor = conn.cursor()

    sql = ("CREATE TABLE Field(fieldID INT PRIMARY KEY NOT NULL, fieldFov REAL NOT NULL, "
           "fieldRA REAL NOT NULL, fieldDEC REAL NOT NULL, fieldGL REAL NOT NULL, "
           "fieldGB REAL NOT NULL, fieldEL REAL NOT NULL, fieldEB REAL NOT NULL);")
    cursor.execute(sql)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print "Usage: python createFieldsTable.py"
    else:
        create_fields_table()
    sys.exit(0)
