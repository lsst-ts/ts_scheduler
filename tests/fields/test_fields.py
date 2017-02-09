import unittest
import os
import sqlite3

from lsst.ts.scheduler.fields import create_fields_db, create_fields_table
from lsst.ts.scheduler.fields import create_fields_data, ingest_fields_data

class FieldsTest(unittest.TestCase):

    def setUp(self):
        self.dbfilename = "test_Fields.db"
        self.fieldsdata_filename = "test_Fields.txt"

    def tearDown(self):
        if os.path.exists(self.dbfilename):
            os.remove(self.dbfilename)
        if os.path.exists(self.fieldsdata_filename):
            os.remove(self.fieldsdata_filename)

    def xtest_fields(self):
        create_fields_db(self.dbfilename)
        filestat = os.stat(self.dbfilename)
        self.assertEqual(filestat.st_size, 0)

        create_fields_table(self.dbfilename)
        conn = sqlite3.connect(self.dbfilename)
        cursor = conn.cursor()
        sql = "select * from Field"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(str(row), "")

        create_fields_data("ts_scheduler/python/lsst/ts/scheduler/fields/tessellationInput.txt",
                           self.fieldsdata_filename)
        filestat = os.stat(self.fieldsdata_filename)
        self.assertEqual(filestat.st_size, 335705)

        ingest_fields_data(self.dbfilename, self.fieldsdata_filename)
        sql = "select * from Field limit 1"
        data = cursor.execute(sql)
        for row in data:
            self.assertEqual(str(row),
                             "(1, 3.5, 0.0, -90.0, -57.068082, -27.128251, -89.93121, -66.561358)")

        conn.close()
