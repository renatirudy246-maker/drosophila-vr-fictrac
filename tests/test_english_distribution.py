import json
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".cpp", ".h", ".src", ".in", ".yml", ".yaml"}


class EnglishDistributionTests(unittest.TestCase):
    def test_distributed_text_is_english_ascii(self):
        paths = list(SOURCE.glob("*.py")) + list(SOURCE.glob("*.md")) + list(SOURCE.glob("*.txt")) + [SOURCE / "settings.json"]
        paths += list((SOURCE / "hardware").glob("*.md"))
        paths += list((SOURCE / "tests").glob("*.py"))
        upstream = SOURCE / "fictrac-2.1.1"
        if upstream.exists():
            paths += [path for path in upstream.rglob("*")
                      if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
                      and not any(part.startswith(("build", "bin", "lib")) for part in path.relative_to(upstream).parts)
                      and "_backup_" not in path.name]
        for path in paths:
            with self.subTest(path=path.relative_to(SOURCE).as_posix()):
                text = path.read_text(encoding="utf-8-sig")
                self.assertTrue(text.isascii(), "Non-English or damaged text in " + str(path))

    def test_default_settings_select_english_without_changing_trial_parameters(self):
        settings = json.loads((SOURCE / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["UI_LANGUAGE"], "en")
        self.assertEqual(settings["STATE_DURATION_S"], 20)
        self.assertEqual(settings["VIRTUAL_WALL_DISTANCE_CM"], 9.75)


if __name__ == "__main__":
    unittest.main()
