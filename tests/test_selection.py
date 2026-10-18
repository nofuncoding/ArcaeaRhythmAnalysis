from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from arcaea_rhythm.config import Config
from arcaea_rhythm.selection import SelectionError, discover_charts, resolve_selection


class SelectionTest(unittest.TestCase):
    def make_charts(self, tmp: str) -> Path:
        root = Path(tmp)
        for folder, difficulties in (("Alpha", (2, 3)), ("Beta", (3,))):
            chart_dir = root / "charts" / folder
            chart_dir.mkdir(parents=True)
            for chart in difficulties:
                (chart_dir / f"{chart}.aff").write_text("-\n", encoding="utf-8")
        return root

    def test_discover_charts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            self.assertEqual(
                discover_charts(root),
                [("Alpha", [2, 3]), ("Beta", [3])],
            )

    def test_explicit_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            self.assertEqual(
                resolve_selection(Config(), "Alpha", 3, root=root, interactive=False),
                ("Alpha", 3),
            )

    def test_noninteractive_requires_folder_when_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            with self.assertRaises(SelectionError):
                resolve_selection(Config(), root=root, interactive=False)

    def test_noninteractive_requires_chart_when_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            with self.assertRaises(SelectionError):
                resolve_selection(Config(folder="Alpha"), root=root, interactive=False)

    def test_single_candidate_is_automatic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chart_dir = root / "charts" / "Only"
            chart_dir.mkdir(parents=True)
            (chart_dir / "3.aff").write_text("-\n", encoding="utf-8")
            self.assertEqual(
                resolve_selection(Config(), root=root, interactive=False),
                ("Only", 3),
            )

    def test_invalid_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            with self.assertRaises(SelectionError):
                resolve_selection(Config(folder="Alpha"), "Alpha", 4, root=root, interactive=False)

    def test_interactive_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_charts(tmp)
            with patch("builtins.input", side_effect=["2", "3"]), redirect_stdout(io.StringIO()):
                self.assertEqual(
                    resolve_selection(Config(), root=root, interactive=True),
                    ("Beta", 3),
                )


if __name__ == "__main__":
    unittest.main()
