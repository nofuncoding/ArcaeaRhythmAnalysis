from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = PROJECT_ROOT / "charts" / "_test_noinput"


class ArcNoInputTest(unittest.TestCase):
    def test_noinput_arcs_are_removed_in_source_order(self) -> None:
        if CHART_DIR.exists():
            shutil.rmtree(CHART_DIR)
        CHART_DIR.mkdir(parents=True)
        try:
            (CHART_DIR / "3.aff").write_text(
                "AudioOffset:0\n"
                "-\n"
                "timing(0,200.00,4.00);\n"
                "arc(0,0,0.50,0.50,s,1.00,1.00,0,none,true);\n"
                "timinggroup(noinput){\n"
                "  timing(0,200.00,4.00);\n"
                "  arc(100,200,0.50,0.50,s,1.00,1.00,0,none,false);\n"
                "};\n"
                "arc(300,400,0.50,0.50,s,1.00,1.00,0,none,false);\n",
                encoding="utf-8",
            )
            with tempfile.TemporaryDirectory() as tmp:
                config = Path(tmp) / "config.txt"
                config.write_text("folder=_test_noinput\nchart=3\n", encoding="utf-8")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(PROJECT_ROOT / "1.py"),
                        "--config", str(config),
                        "--force",
                        "--refresh-timing",
                    ],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            output = (CHART_DIR / "1.aff").read_text(encoding="utf-8")
            self.assertNotIn("arc(100,200", output)
            self.assertIn("arc(300,400", output)
        finally:
            shutil.rmtree(CHART_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
