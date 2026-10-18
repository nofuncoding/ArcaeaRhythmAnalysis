from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from arcaea_rhythm import __version__, cli, pipeline


class CliTest(unittest.TestCase):
    def test_version(self) -> None:
        self.assertTrue(__version__)

    def test_list(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cli.main(["list"])
        self.assertEqual(code, 0)
        self.assertIn("KikaiNoTsubasa", buffer.getvalue())

    def test_keep_effect_bpm_flag(self) -> None:
        args = pipeline.parse_args(["--keep-effect-bpm"])
        self.assertTrue(args.keep_effect_bpm)
        self.assertIsNone(args.max_bpm)

    def test_keep_and_ignore_are_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            pipeline.parse_args(["--keep-effect-bpm", "--ignore-effect-bpm"])

    def test_migrate_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "config.toml"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = cli.main([
                    "migrate-config",
                    "--config", "config.txt",
                    "--output", str(output),
                    "--force",
                ])
            self.assertEqual(code, 0)
            text = output.read_text(encoding="utf-8")
            self.assertIn("[chart]", text)
            self.assertIn("speed = 1.0", text)
            self.assertNotIn("folder =", text)


if __name__ == "__main__":
    unittest.main()
