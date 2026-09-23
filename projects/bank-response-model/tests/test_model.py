import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import FEATURES, check_data, split_positions, top_fraction


class ModelChecks(unittest.TestCase):
    def test_split_has_order_and_no_overlap(self):
        a, b, c = split_positions(101)
        self.assertEqual((a.stop, b.start, b.stop, c.start, c.stop), (64, 64, 80, 80, 101))

    def test_duration_is_not_a_feature(self):
        self.assertNotIn('duration', FEATURES)

    def test_top_fraction_selects_highest_probability(self):
        y = pd.Series([0, 1, 0, 1, 0, 0, 0, 0, 0, 0])
        result = top_fraction(y, np.array([.1, .9, .2, .4, .3, .2, .1, .1, .1, .1]))
        self.assertEqual((result['selected'], result['responses']), (1, 1))


if __name__ == '__main__':
    unittest.main()
