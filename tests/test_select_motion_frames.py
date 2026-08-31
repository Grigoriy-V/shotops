import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "select_motion_frames.py"
SPEC = importlib.util.spec_from_file_location("select_motion_frames", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class BiasedPositionsTest(unittest.TestCase):
    def test_keeps_requested_count_and_endpoints(self):
        positions = MODULE.biased_positions(124, 50)
        self.assertEqual(len(positions), 50)
        self.assertEqual(positions[0], 0)
        self.assertEqual(positions[-1], 123)
        self.assertEqual(positions, sorted(set(positions)))

    def test_power_concentrates_choices_at_the_middle(self):
        positions = MODULE.biased_positions(124, 50, power=3)
        gaps = [right - left for left, right in zip(positions, positions[1:])]
        self.assertGreater(gaps[0], gaps[len(gaps) // 2])
        self.assertGreater(gaps[-1], gaps[len(gaps) // 2])

    def test_center_moves_dense_region(self):
        positions = MODULE.biased_positions(124, 50, power=3, center=0.65)
        self.assertAlmostEqual(positions[24] / 123, 0.65, delta=0.03)


if __name__ == "__main__":
    unittest.main()
