FIELDSDB_FILENAME = "Fields.db"

import sqlite3

from ts_scheduler.schedulerDefinitions import conf_file_path

class FieldsDatabase(object):

    def __init__(self):
        self.dbfilepath = conf_file_path(__name__, FIELDSDB_FILENAME)

    def query(self, sql):

        conn = sqlite3.connect(self.dbfilepath)
        cursor = conn.cursor()
        data = cursor.execute(sql)
        res = cursor.fetchall()

        return res
