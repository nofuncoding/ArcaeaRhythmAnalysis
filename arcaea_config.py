"""兼容 shim：配置实现已移动到 arcaea_rhythm.config。"""

from arcaea_rhythm.config import AUDIO_FORMATS, Config, PROJECT_ROOT, load_config

__all__ = ["AUDIO_FORMATS", "Config", "PROJECT_ROOT", "load_config"]
