"""Verify bilingual README navigation, local links and license details."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
ZH = (ROOT / "README.md").read_text(encoding="utf-8")
EN = (ROOT / "README.en.md").read_text(encoding="utf-8")
LICENSE = (ROOT / "LICENSE").read_text(encoding="utf-8")


class ReadmeLocalizationTests(unittest.TestCase):
    def test_language_navigation(self):
        self.assertIn("[English](README.en.md)", ZH)
        self.assertIn("[简体中文](README.md)", EN)

    def test_same_essential_commands(self):
        for command in ("seed_ideation.py plan", "seed_ideation.py batch",
                        "seed_ideation.py replay", "unittest discover -s tests"):
            with self.subTest(command=command):
                self.assertIn(command, ZH)
                self.assertIn(command, EN)

    def test_same_important_descriptions(self):
        for value in ("quick", "standard", "rigorous", "64", "96", "MIT"):
            with self.subTest(value=value):
                self.assertIn(value, ZH)
                self.assertIn(value, EN)

    def test_local_links_exist(self):
        for name, doc in (("README.md", ZH), ("README.en.md", EN)):
            for link in re.findall(r"\]\(([^)]+)\)", doc):
                if link.startswith(("https://", "http://", "#")):
                    continue
                with self.subTest(name=name, link=link):
                    self.assertTrue((ROOT / link.split("#", 1)[0]).exists())

    def test_license(self):
        self.assertTrue(LICENSE.startswith("MIT License\n\nCopyright (c) 2026 coicy"))
        self.assertIn("The above copyright notice", LICENSE)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', LICENSE)


if __name__ == "__main__":
    unittest.main()
