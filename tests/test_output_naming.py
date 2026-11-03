import itertools
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from output_naming import (condition_file_prefix, existing_fly_ids, fly_folder_name,
                           is_experiment_csv, output_root_dir)
from plot_split_trajectory import find_csv_in_folder


class OutputNamingTests(unittest.TestCase):
    def test_grouped_fly_folder_names_cover_all_calibrated_conditions(self):
        for wing, color, (original, level) in itertools.product(
                ("wing", "no_wing"), ("white", "green", "red"),
                (("dark", "low"), ("medium", "medium"), ("bright", "high"))):
            values = dict(config._cfg, SINGLE_BG_NAME=color)
            values["SINGLE_BRIGHTNESS"] = values[f"STATE_{color.upper()}_{original.upper()}_BRIGHTNESS"]
            self.assertEqual(fly_folder_name(values, wing, "1"), f"{wing}_01_{color}_{level}")
            self.assertEqual(fly_folder_name(values, wing, "102"), f"{wing}_102_{color}_{level}")
        for wing, number in (("other", "1"), ("wing", "0"), ("wing", "../1")):
            with self.assertRaises(ValueError):
                fly_folder_name(config._cfg, wing, number)

    def test_group_numbering_is_independent_and_ignores_unrelated_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(existing_fly_ids(root, "wing"), set())
            for group, name in (("wing", "wing_01_white_low"), ("wing", "wing_02_red_high"),
                                ("wing", "no_wing_99_green_low"), ("wing", "other_folder"),
                                ("no_wing", "no_wing_01_green_medium")):
                (root / group / name).mkdir(parents=True)
            (root / "wing" / "wing_99_white_low").touch()
            self.assertEqual(existing_fly_ids(root, "wing"), {1, 2})
            self.assertEqual(existing_fly_ids(root, "no_wing"), {1})

    def test_output_root_recovers_group_sample_and_legacy_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in (root, root / "wing", root / "no_wing",
                         root / "wing" / "wing_01_white_low", root / "no_wing" / "no_wing_01_green_high",
                         root / "wing_01_1", root / "no_wing_02_3"):
                self.assertEqual(Path(output_root_dir(str(path))), root, str(path))

    def test_all_eighteen_calibrated_conditions(self):
        for color, (original, label), stimulus in itertools.product(
                ("white", "green", "red"),
                (("dark", "low"), ("medium", "medium"), ("bright", "high")), (False, True)):
            with self.subTest(color=color, level=label, stimulus=stimulus):
                values = dict(config._cfg, EXPERIMENT_PROTOCOL="single_condition", SINGLE_BG_NAME=color,
                              SINGLE_STIMULUS_ON=stimulus, SINGLE_BRIGHTNESS_LABEL="custom")
                values["SINGLE_BRIGHTNESS"] = values[f"STATE_{color.upper()}_{original.upper()}_BRIGHTNESS"]
                prefix = f"{color}_{label}_{'on' if stimulus else 'off'}"
                self.assertEqual(condition_file_prefix(values), prefix)
                self.assertTrue(is_experiment_csv(prefix + "_20261104_123456.csv"))
                self.assertFalse(is_experiment_csv(prefix + "_20261104_123456_phase_summary.csv"))

    def test_custom_values_are_not_rounded_or_classified_by_thirds(self):
        values = dict(config._cfg, EXPERIMENT_PROTOCOL="single_condition", SINGLE_BG_NAME="white")
        for brightness in (0, 0.1971, 0.42, 1):
            with self.subTest(brightness=brightness):
                values["SINGLE_BRIGHTNESS"] = brightness
                self.assertEqual(condition_file_prefix(values), "white_custom_off")
                self.assertEqual(values["SINGLE_BRIGHTNESS"], brightness)
        values["SINGLE_BRIGHTNESS"] = values["STATE_WHITE_MEDIUM_BRIGHTNESS"] = 0.197
        self.assertEqual(condition_file_prefix(values), "white_custom_off")

    def test_invalid_metadata_cannot_create_a_misleading_name(self):
        valid = dict(config._cfg, EXPERIMENT_PROTOCOL="single_condition")
        for change in ({"SINGLE_BG_NAME": "../white"}, {"SINGLE_BRIGHTNESS": float("nan")},
                       {"SINGLE_BRIGHTNESS": 1.1}, {"SINGLE_STIMULUS_ON": "false"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                condition_file_prefix(dict(valid, **change))

    def test_legacy_names_and_non_experiment_files(self):
        self.assertEqual(condition_file_prefix({}), "drosophila_exp")
        self.assertEqual(condition_file_prefix({"EXPERIMENT_PROTOCOL": "18_states"}), "drosophila_exp")
        self.assertTrue(is_experiment_csv("drosophila_exp_20261104_123456.csv"))
        for name in ("experiment_settings.json", "other.csv", "white_high.csv",
                     "white_high_off_20261104_123456_phase_summary.csv",
                     "drosophila_exp_20261104_123456_phase_summary.csv"):
            self.assertFalse(is_experiment_csv(name), name)

    def test_plot_folder_lookup_accepts_new_and_legacy_names(self):
        for prefix in ("drosophila_exp", "white_high_off", "green_low_on", "red_custom_on"):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = root / (prefix + "_20261104_123456.csv")
                data.touch()
                (root / (prefix + "_20261104_123456_phase_summary.csv")).touch()
                (root / "other.csv").touch()
                self.assertEqual(Path(find_csv_in_folder(directory)), data)


if __name__ == "__main__":
    unittest.main()
