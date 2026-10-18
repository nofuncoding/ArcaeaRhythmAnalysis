"""音频混音辅助函数。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

BASE_AUDIO_NAMES = ("base.ogg", "base.mp3", "base.wav", "base.flac")


def find_base_audio(chart_dir: str | Path) -> Path | None:
    for name in BASE_AUDIO_NAMES:
        candidate = Path(chart_dir) / name
        if candidate.exists():
            return candidate
    return None


def audio_duration_ms(path: str | Path) -> float:
    return sf.info(path).duration * 1000.0


def ensure_channels(data: np.ndarray, channels: int) -> np.ndarray:
    """把音频统一到目标声道数。"""
    if data.ndim == 1:
        data = data[:, np.newaxis]
    if data.shape[1] == channels:
        return data
    if data.shape[1] == 1:
        return np.repeat(data, channels, axis=1)
    if data.shape[1] > channels:
        return data[:, :channels]
    pad = np.repeat(data[:, -1:], channels - data.shape[1], axis=1)
    return np.concatenate((data, pad), axis=1)


def resample_audio(data: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """重采样；优先 soxr，未安装时退化为线性插值。"""
    if sr_in == sr_out or len(data) == 0:
        return data
    data = data.astype(np.float32, copy=False)
    try:
        import soxr
        return soxr.resample(data, sr_in, sr_out, quality="HQ").astype(np.float32, copy=False)
    except ImportError:
        n_out = max(1, int(round(len(data) * sr_out / sr_in)))
        x_old = np.arange(len(data), dtype=np.float64)
        x_new = np.linspace(0.0, len(data) - 1.0, n_out)
        out = np.empty((n_out, data.shape[1]), dtype=np.float32)
        for channel in range(data.shape[1]):
            out[:, channel] = np.interp(x_new, x_old, data[:, channel])
        return out


def prepare_sample(path: str | Path, target_sr: int, target_channels: int) -> np.ndarray:
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    data = ensure_channels(data, target_channels)
    return resample_audio(data, sr, target_sr)


def add_hit(buffer: np.ndarray, sample: np.ndarray, time_ms: float, sr: int) -> None:
    """在 time_ms 对应的采样位置叠加一个采样。"""
    start = int(round(time_ms * sr / 1000.0))
    if start < 0:
        sample = sample[-start:]
        start = 0
    if start >= len(buffer) or len(sample) == 0:
        return
    n = min(len(sample), len(buffer) - start)
    if n > 0:
        buffer[start:start + n] += sample[:n]


def write_audio(path: str | Path, data: np.ndarray, sr: int, fmt: str) -> None:
    """分块写出，避免 soundfile 一次写超长数组时的内存问题。"""
    formats = {"flac": "FLAC", "wav": "WAV", "ogg": "OGG", "mp3": "MP3"}
    subtypes = {"flac": "PCM_16", "wav": "PCM_16", "ogg": "VORBIS"}
    kwargs = {"samplerate": sr, "channels": data.shape[1], "format": formats[fmt]}
    if fmt in subtypes:
        kwargs["subtype"] = subtypes[fmt]
    with sf.SoundFile(path, mode="w", **kwargs) as file:
        step = 1_000_000
        for start in range(0, len(data), step):
            file.write(data[start:start + step])
