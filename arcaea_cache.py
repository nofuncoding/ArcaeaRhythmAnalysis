"""兼容 shim：缓存实现已移动到 arcaea_rhythm.cache。"""

from arcaea_rhythm.cache import CACHE_VERSION, BuildCache

__all__ = ["CACHE_VERSION", "BuildCache"]
