import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import COLUMNS, check_rows


def row():
    r = {key: '0' for key in COLUMNS}
    r.update(instant='1', dteday='2011-01-01', hr='8', workingday='1',
             casual='2', registered='3', cnt='5')
    return r


class DataChecks(unittest.TestCase):
    def test_rejects_mismatched_components(self):
        r = row()
        r['cnt'] = '6'
        with self.assertRaisesRegex(ValueError, 'Count components disagree'):
            check_rows([r])

    def test_rejects_duplicate_date_hour_even_with_distinct_ids(self):
        first, second = row(), copy.copy(row())
        second['instant'] = '2'
        with self.assertRaisesRegex(ValueError, 'Duplicate observation'):
            check_rows([first, second])

    def test_reports_missing_hours_without_imputing_zero(self):
        result = check_rows([row()])
        self.assertEqual(result['missing_date_hour_combinations'], 23)


if __name__ == '__main__':
    unittest.main()
