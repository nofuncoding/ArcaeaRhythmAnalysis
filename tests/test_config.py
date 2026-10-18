from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arcaea_config import load_config


class ConfigLoaderTest(unittest.TestCase):
    def test_load_txt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.txt"
            path.write_text(
                "folder=TestSong\nchart=4\nspeed=1.5\nvolume=0.5\n"
                "longchart=0\nwidth=1920\naudio_format=ogg\n",
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.folder, "TestSong")
            self.assertEqual(cfg.chart, 4)
            self.assertEqual(cfg.speed, 1.5)
            self.assertEqual(cfg.volume, 0.5)
            self.assertEqual(cfg.longchart, 0)
            self.assertEqual(cfg.width, 1920)
            self.assertEqual(cfg.audio_format, "ogg")

    def test_load_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "[chart]\n"
                'folder = "TestSong"\n'
                "difficulty = 3\n"
                "speed = 2.0\n"
                "longchart = 1\n"
                "max_bpm = 10000\n"
                "[audio]\n"
                "volume = 0.8\n"
                'format = "wav"\n'
                "[preview]\n"
                "width = 1600\n",
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.folder, "TestSong")
            self.assertEqual(cfg.chart, 3)
            self.assertEqual(cfg.speed, 2.0)
            self.assertEqual(cfg.volume, 0.8)
            self.assertEqual(cfg.width, 1600)
            self.assertEqual(cfg.audio_format, "wav")
            self.assertEqual(cfg.max_bpm, 10000)

    def test_invalid_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.txt"
            path.write_text("folder=TestSong\nchart=9\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_selection_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.txt"
            path.write_text("speed=1.25\nvolume=0.8\n", encoding="utf-8")
            cfg = load_config(path)
            self.assertIsNone(cfg.folder)
            self.assertIsNone(cfg.chart)
            self.assertEqual(cfg.max_bpm, 1000.0)
            with self.assertRaises(ValueError):
                _ = cfg.chart_dir

    def test_toml_selection_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "[chart]\n"
                "speed = 1.25\n"
                "[audio]\n"
                'format = "ogg"\n',
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertIsNone(cfg.folder)
            self.assertIsNone(cfg.chart)
            self.assertEqual(cfg.speed, 1.25)
            self.assertEqual(cfg.audio_format, "ogg")

    def test_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_config("definitely-not-here.toml")


if __name__ == "__main__":
    unittest.main()
