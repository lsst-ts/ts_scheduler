import unittest
import os
import sqlite3

from ts_scheduler.fields import create_fields_db
from ts_scheduler.fields import create_fields_table
from ts_scheduler.fields import create_fields_data
from ts_scheduler.fields import ingest_fields_data

class FieldsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dbfilename = "test_Fields.db"

    def test_fields(self):

        dbfilename = "test_Fields.db"
        fieldsdata_filename = "test_Fields.txt"

        create_fields_db(dbfilename)
        filestat = os.stat(dbfilename)
        self.assertEqual(filestat.st_size, 0)

        create_fields_table(dbfilename)
        conn = sqlite3.connect(dbfilename)
        cursor = conn.cursor()
        sql = "select * from Field"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(row.__str__(), "")

        create_fields_data("ts_scheduler/fields/tessellationInput.txt", fieldsdata_filename)
        filestat = os.stat(fieldsdata_filename)
        self.assertEqual(filestat.st_size, 335705)

        ingest_fields_data(dbfilename, fieldsdata_filename)
        sql = "select * from Field limit 1"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(row.__str__(),
                             "(1, 3.5, 0.0, -90.0, -57.068082, -27.128251, -89.93121, -66.561358)")

        conn.close()
