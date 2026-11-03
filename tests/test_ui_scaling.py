from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_scaling import MonitorMetrics, fit_client_size


class MonitorSizingTests(unittest.TestCase):
    def test_secondary_screen_uses_unscaled_minimum_and_work_area(self):
        monitor = MonitorMetrics(2, 1, (-1920, 0, 0, 1032), (16, 40))
        size, minimum = fit_client_size((1280, 780), 1, monitor)
        self.assertEqual(size, (1280, 780))
        self.assertEqual(minimum, (1180, 640))
        self.assertGreater(size[0], minimum[0])
        self.assertGreater(size[1], minimum[1])

    def test_oversized_window_fits_destination_with_titlebar_and_taskbar(self):
        monitor = MonitorMetrics(2, 1, (-1920, 0, 0, 1032), (16, 40))
        size, minimum = fit_client_size((2200, 1500), 1, monitor)
        self.assertEqual(size, (1888, 976))
        self.assertLessEqual(size[0] + 16, 1920)
        self.assertLessEqual(size[1] + 40, 1032)

    def test_primary_scaling_preserves_logical_size(self):
        monitor = MonitorMetrics(1, 1.75, (0, 0, 2880, 1716), (16, 40))
        size, minimum = fit_client_size((1280, 780), 1.75, monitor)
        self.assertEqual(size, (2240, 1365))
        self.assertEqual(minimum, (2065, 1120))

    def test_minimum_never_exceeds_a_smaller_work_area(self):
        monitor = MonitorMetrics(3, 1.5, (0, 0, 1280, 720), (16, 40))
        size, minimum = fit_client_size((1180, 640), 1.5, monitor)
        self.assertEqual(size, minimum)
        self.assertLess(size[0], 1280)
        self.assertLess(size[1], 720)


if __name__ == "__main__":
    unittest.main()
