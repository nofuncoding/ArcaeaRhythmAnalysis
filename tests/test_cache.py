from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arcaea_cache import BuildCache


class BuildCacheTest(unittest.TestCase):
    def test_fresh_and_invalidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            output = root / "output.txt"
            cache_path = root / ".cache.json"
            source.write_text("v1", encoding="utf-8")
            output.write_text("out", encoding="utf-8")

            cache = BuildCache(cache_path)
            key = cache.make_key([source], {"speed": 1.0})
            self.assertFalse(cache.fresh("stage", key, [output]))
            cache.update("stage", key, [output])
            cache.save()

            reloaded = BuildCache(cache_path)
            self.assertTrue(reloaded.fresh("stage", key, [output]))

            source.write_text("v2", encoding="utf-8")
            self.assertNotEqual(reloaded.make_key([source], {"speed": 1.0}), key)

    def test_missing_output_is_not_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("v1", encoding="utf-8")
            cache = BuildCache(root / ".cache.json")
            key = cache.make_key([source], {})
            cache.update("stage", key, [root / "missing.txt"])
            self.assertFalse(cache.fresh("stage", key, [root / "missing.txt"]))

    def test_corrupt_cache_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / ".cache.json"
            cache_path.write_text("{not json", encoding="utf-8")
            cache = BuildCache(cache_path)
            self.assertEqual(cache.data["version"], 8)
            self.assertEqual(cache.data["stages"], {})


if __name__ == "__main__":
    unittest.main()
