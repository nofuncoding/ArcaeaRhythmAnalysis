"""运行时谱面/难度选择。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import Config, PROJECT_ROOT

DIFFICULTY_LABELS = {2: "ftr", 3: "byd", 4: "etr"}


class SelectionError(Exception):
    pass


def discover_charts(root: Path = PROJECT_ROOT) -> list[tuple[str, list[int]]]:
    charts_dir = root / "charts"
    charts: list[tuple[str, list[int]]] = []
    if not charts_dir.exists():
        return charts
    for folder in sorted(path for path in charts_dir.iterdir() if path.is_dir()):
        difficulties = [chart for chart in (2, 3, 4) if (folder / f"{chart}.aff").exists()]
        if difficulties:
            charts.append((folder.name, difficulties))
    return charts


def _prompt_folder(charts: list[tuple[str, list[int]]], default_index: int) -> str:
    print("可用谱面：")
    for index, (folder, difficulties) in enumerate(charts, 1):
        labels = ", ".join(f"{chart} {DIFFICULTY_LABELS[chart]}" for chart in difficulties)
        print(f"  {index}) {folder}  [{labels}]")
    while True:
        try:
            raw = input(f"选择谱面 [1-{len(charts)}]（默认 {default_index + 1}）: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise SelectionError("已取消选择") from None
        if not raw:
            return charts[default_index][0]
        if raw.isdigit() and 1 <= int(raw) <= len(charts):
            return charts[int(raw) - 1][0]
        for folder, _ in charts:
            if raw == folder:
                return folder
        print("无效选择，请输入序号或文件夹名。")


def _prompt_chart(difficulties: list[int], default_index: int) -> int:
    labels = ", ".join(f"{chart} {DIFFICULTY_LABELS[chart]}" for chart in difficulties)
    print(f"可用难度：{labels}")
    while True:
        try:
            raw = input(f"选择难度 [{'/'.join(str(chart) for chart in difficulties)}]"
                        f"（默认 {difficulties[default_index]}）: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise SelectionError("已取消选择") from None
        if not raw:
            return difficulties[default_index]
        if raw.isdigit() and int(raw) in difficulties:
            return int(raw)
        for chart in difficulties:
            if raw == DIFFICULTY_LABELS[chart]:
                return chart
        print("无效选择，请输入难度编号（2/3/4）或 ftr/byd/etr。")


def resolve_selection(
    cfg: Config,
    folder: str | None = None,
    chart: int | None = None,
    root: Path = PROJECT_ROOT,
    interactive: bool | None = None,
) -> tuple[str, int]:
    """确定本次运行的 folder/chart；交互环境给选择，非交互环境要求参数或唯一候选。"""
    if interactive is None:
        interactive = sys.stdin.isatty() and os.environ.get("ARCAEA_SUBPROCESS") != "1"

    charts = discover_charts(root)
    if not charts:
        raise SelectionError(f"{root / 'charts'} 下没有找到包含 2/3/4.aff 的谱面")

    names = [name for name, _ in charts]
    difficulty_map = dict(charts)

    if folder:
        normalized = Path(folder).name
        folder = normalized if normalized in names else folder
        if folder not in names:
            raise SelectionError(f"找不到谱面文件夹 {folder}；可用：{', '.join(names)}")
    elif not interactive:
        if cfg.folder in names:
            folder = cfg.folder
        elif len(names) == 1:
            folder = names[0]
        else:
            raise SelectionError(f"有多个谱面，请用 --folder 指定：{', '.join(names)}")
    else:
        default_index = names.index(cfg.folder) if cfg.folder in names else 0
        folder = _prompt_folder(charts, default_index)

    difficulties = difficulty_map[folder]
    if chart is not None:
        if chart not in difficulties:
            available = ", ".join(str(item) for item in difficulties)
            raise SelectionError(f"{folder} 没有 {chart}.aff；可用难度：{available}")
    elif not interactive:
        if cfg.chart in difficulties:
            chart = cfg.chart
        elif len(difficulties) == 1:
            chart = difficulties[0]
        else:
            available = ", ".join(str(item) for item in difficulties)
            raise SelectionError(f"{folder} 有多个难度，请用 --chart 指定：{available}")
    else:
        default_index = difficulties.index(cfg.chart) if cfg.chart in difficulties else 0
        chart = _prompt_chart(difficulties, default_index)

    return folder, chart
