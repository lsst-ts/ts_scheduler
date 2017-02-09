import sqlite3

from lsst.ts.scheduler.kernel import Field, conf_file_path

__all__ = ["FieldsDatabase"]

FIELDSDB_FILENAME = "Fields.db"

class FieldsDatabase(object):

    def __init__(self):
        self.dbfilepath = conf_file_path(__name__, FIELDSDB_FILENAME)

    def query(self, sql):

        conn = sqlite3.connect(self.dbfilepath)
        cursor = conn.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()

        return res

    def get_all_fields(self):
        return self.get_field_set("select * from Field;")

    def get_field_set(self, query):
        field_set = set()
        field_rows = self.query(query)
        for field_row in field_rows:
            field = Field.from_db_row(field_row)
            field_set.add(field)

        return field_set
