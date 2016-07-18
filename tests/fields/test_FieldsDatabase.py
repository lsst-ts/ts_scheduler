import unittest

from ts_scheduler.fields import FieldsDatabase

class FieldsDatabaseTest(unittest.TestCase):

    def setUp(self):

        self.db = FieldsDatabase()

    def test_query(self):

        sql = 'SELECT fieldID, fieldRA, fieldDec from Field WHERE fieldID <= 10 order by fieldID'

        res = self.db.query(sql)

        self.assertEqual(str(res), "[(1, 0.0, -90.0), (2, 180.0, -87.568555), "
                         "(3, 324.000429, -87.56855), (4, 35.999571, -87.56855), "
                         "(5, 252.001105, -87.568547), (6, 107.998895, -87.568547), "
                         "(7, 215.999822, -85.272913), (8, 144.000178, -85.272913), "
                         "(9, 0.0, -85.272892), (10, 288.000508, -85.272852)]")

    def test_get_all_fields(self):
        field_set = self.db.get_all_fields()
        self.assertEqual(len(field_set), 5292)
