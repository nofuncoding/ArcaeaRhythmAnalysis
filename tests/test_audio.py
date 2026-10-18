from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from arcaea_rhythm.audio import add_hit, ensure_channels, prepare_sample, write_audio


class AudioHelpersTest(unittest.TestCase):
    def test_ensure_channels(self) -> None:
        mono = np.zeros((100, 1), dtype=np.float32)
        stereo = ensure_channels(mono, 2)
        self.assertEqual(stereo.shape, (100, 2))
        one_d = ensure_channels(np.zeros(100, dtype=np.float32), 1)
        self.assertEqual(one_d.shape, (100, 1))

    def test_add_hit_position(self) -> None:
        buffer = np.zeros((1000, 2), dtype=np.float32)
        sample = np.ones((50, 2), dtype=np.float32)
        add_hit(buffer, sample, 100, 1000)
        self.assertTrue(np.all(buffer[100:150] == 1))
        self.assertTrue(np.all(buffer[:100] == 0))
        self.assertTrue(np.all(buffer[150:] == 0))

    def test_add_hit_clips_at_end(self) -> None:
        buffer = np.zeros((100, 2), dtype=np.float32)
        add_hit(buffer, np.ones((50, 2), dtype=np.float32), 90, 1000)
        self.assertTrue(np.all(buffer[90:100] == 1))

    def test_write_audio_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.wav"
            data = np.zeros((4410, 2), dtype=np.float32)
            write_audio(path, data, 44100, "wav")
            info = sf.info(path)
            self.assertEqual(info.samplerate, 44100)
            self.assertEqual(info.channels, 2)
            self.assertAlmostEqual(info.duration, 0.1, places=2)

    def test_prepare_sample_resamples_and_channels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.wav"
            sf.write(path, np.zeros((22050, 1), dtype=np.float32), 22050)
            data = prepare_sample(path, 44100, 2)
            self.assertEqual(data.shape[1], 2)
            self.assertAlmostEqual(len(data), 44100, delta=2)


if __name__ == "__main__":
    unittest.main()
