"""统一配置加载：支持 config.toml（推荐）和旧版 config.txt。"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = _PACKAGE_ROOT if (_PACKAGE_ROOT / "charts").exists() else Path.cwd()
AUDIO_FORMATS = ("flac", "wav", "ogg", "mp3")
_INT_KEYS = {"chart", "version", "offset", "longchart", "width", "slow"}
_FLOAT_KEYS = {"speed", "volume", "max_bpm"}


@dataclass(slots=True)
class Config:
    folder: str | None = None
    chart: int | None = None
    speed: float = 1.0
    version: int = 0
    offset: int = 0
    volume: float = 0.7
    longchart: int = 1
    width: int = 1280
    audio_format: str = "flac"
    slow: int = 0
    max_bpm: float = 1000.0
    source: Path | None = None

    def __post_init__(self) -> None:
        if self.folder is not None and not self.folder:
            raise ValueError("folder 不能为空")
        if self.chart is not None and self.chart not in (2, 3, 4):
            raise ValueError("chart 必须是 2、3 或 4")
        if self.speed <= 0:
            raise ValueError("speed 必须大于 0")
        if not 0 <= self.volume <= 4:
            raise ValueError("volume 必须在 0 到 4 之间")
        if self.longchart not in (0, 1):
            raise ValueError("longchart 必须是 0 或 1")
        if self.width <= 0:
            raise ValueError("width 必须大于 0")
        if self.max_bpm < 0:
            raise ValueError("max_bpm 必须 >= 0（0 表示不限制）")
        if self.audio_format not in AUDIO_FORMATS:
            raise ValueError(f"audio_format 必须是 {'、'.join(AUDIO_FORMATS)}")

    def require_selection(self) -> None:
        if not self.folder:
            raise ValueError("尚未选择谱面文件夹")
        if self.chart is None:
            raise ValueError("尚未选择难度")

    @property
    def chart_dir(self) -> Path:
        if not self.folder:
            raise ValueError("尚未选择谱面文件夹")
        return PROJECT_ROOT / "charts" / self.folder

    @property
    def aff_name(self) -> str:
        if self.chart is None:
            raise ValueError("尚未选择难度")
        return "0.aff" if self.chart == 2 else "1.aff"

    @property
    def output_aff(self) -> Path:
        return self.chart_dir / self.aff_name

    @property
    def timing_file(self) -> Path:
        self.require_selection()
        return self.chart_dir / f"timing_{self.chart}.txt"

    @property
    def rhythm_file(self) -> Path:
        self.require_selection()
        return self.chart_dir / f"rhythm_{self.chart}.txt"

    @property
    def svg_file(self) -> Path:
        self.require_selection()
        return self.chart_dir / f"rhythm_{self.chart}.svg"


def _parse_txt(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number} 不是 key=value 格式")
        key, value = (part.strip() for part in line.split("=", 1))
        key = key.lower()
        if key == "difficulty":
            key = "chart"
        if key == "format":
            key = "audio_format"
        try:
            if key in _INT_KEYS:
                data[key] = int(value)
            elif key in _FLOAT_KEYS:
                data[key] = float(value)
            elif key in ("folder", "audio_format"):
                data[key] = value.lower() if key == "audio_format" else value
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number} 的 {key} 值无效：{value}") from exc
    return data


def _parse_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        document = tomllib.load(file)

    chart_section = document.get("chart", {})
    audio = document.get("audio", {})
    preview = document.get("preview", {})
    top_chart = document.get("chart")
    if isinstance(top_chart, dict):
        top_chart = None

    def first(*values: Any, default: Any = None) -> Any:
        for value in values:
            if value is not None:
                return value
        return default

    return {
        "folder": first(chart_section.get("folder"), document.get("folder")),
        "chart": first(chart_section.get("difficulty"), chart_section.get("chart"), top_chart),
        "speed": first(chart_section.get("speed"), document.get("speed"), default=1.0),
        "version": first(chart_section.get("version"), document.get("version"), default=0),
        "offset": first(chart_section.get("offset"), document.get("offset"), default=0),
        "volume": first(audio.get("volume"), document.get("volume"), default=0.7),
        "longchart": first(chart_section.get("longchart"), document.get("longchart"), default=1),
        "width": first(preview.get("width"), document.get("width"), default=1280),
        "audio_format": first(audio.get("format"), audio.get("audio_format"),
                              document.get("audio_format"), default="flac"),
        "slow": first(audio.get("slow"), chart_section.get("slow"), document.get("slow"), default=0),
        "max_bpm": first(chart_section.get("max_bpm"), document.get("max_bpm"), default=1000.0),
    }


def load_config(path: str | Path | None = None) -> Config:
    """加载配置；未指定路径时优先 config.toml，其次 config.txt。"""
    if path is not None:
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path
        if not config_path.exists():
            raise FileNotFoundError(f"找不到配置文件：{config_path}")
    else:
        config_path = None
        for candidate in (PROJECT_ROOT / "config.toml", PROJECT_ROOT / "config.txt"):
            if candidate.exists():
                config_path = candidate
                break
        if config_path is None:
            raise FileNotFoundError("找不到 config.toml 或 config.txt")

    data = _parse_toml(config_path) if config_path.suffix.lower() == ".toml" else _parse_txt(config_path)

    # CLI 的 --folder/--chart 会通过环境变量传给子进程
    env_folder = os.environ.get("ARCAEA_FOLDER")
    if env_folder:
        data["folder"] = env_folder
    env_chart = os.environ.get("ARCAEA_CHART")
    if env_chart:
        try:
            data["chart"] = int(env_chart)
        except ValueError as exc:
            raise ValueError(f"ARCAEA_CHART 不是整数：{env_chart}") from exc
    env_max_bpm = os.environ.get("ARCAEA_MAX_BPM")
    if env_max_bpm:
        try:
            data["max_bpm"] = float(env_max_bpm)
        except ValueError as exc:
            raise ValueError(f"ARCAEA_MAX_BPM 不是数字：{env_max_bpm}") from exc

    data["audio_format"] = str(data.get("audio_format", "flac")).lower()
    return Config(**data, source=config_path)
