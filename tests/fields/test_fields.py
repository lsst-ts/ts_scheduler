import unittest
import os
import sqlite3

from ts_scheduler.fields import createFieldsDB
from ts_scheduler.fields import createFieldsTable
from ts_scheduler.fields import createFieldsData
from ts_scheduler.fields import ingestFieldsData

class FieldsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dbfilename = "test_Fields.db"

    def test_fields(self):

        dbfilename = "test_Fields.db"
        fieldsDataFilename = "test_Fields.txt"

        createFieldsDB(dbfilename)
        filestat = os.stat(dbfilename)
        self.assertEqual(filestat.st_size, 0)

        createFieldsTable(dbfilename)
        conn = sqlite3.connect(dbfilename)
        cursor = conn.cursor()
        sql = "select * from Field"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(row.__str__(), "")

        createFieldsData("ts_scheduler/fields/tessellationInput.txt", fieldsDataFilename)
        filestat = os.stat(fieldsDataFilename)
        self.assertEqual(filestat.st_size, 335705)

        ingestFieldsData(dbfilename, fieldsDataFilename)
        sql = "select * from Field limit 1"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(row.__str__(), "(1, 3.5, 0.0, -90.0, -57.068082, -27.128251, -89.93121, -66.561358)")

        conn.close()

