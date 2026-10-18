"""timing 数据清洗：过滤特效 BPM / 拍号，避免除零和异常坐标。"""

from __future__ import annotations

import math

MAX_BEATS_PER_MEASURE = 64.0


def valid_bpm(bpm: float, max_bpm: float = 0.0) -> bool:
    """BPM 必须为正；max_bpm > 0 时同时过滤超过上限的特效 BPM。"""
    return bpm > 0 and (max_bpm <= 0 or bpm <= max_bpm)


def valid_beats_per_measure(value: float) -> bool:
    """拍号必须是正常的 1..64；999/1024 等视为特效值。"""
    return 1 <= value <= MAX_BEATS_PER_MEASURE


def measure_aligned(delta_beats: float, beats_per_measure: float, tolerance: float = 0.01) -> bool:
    """判断 delta_beats 是否接近整数个小节，避免浮点取模误判。"""
    if beats_per_measure <= 0:
        return False
    measure_count = round(delta_beats / beats_per_measure)
    return math.isclose(delta_beats, measure_count * beats_per_measure, abs_tol=tolerance)
