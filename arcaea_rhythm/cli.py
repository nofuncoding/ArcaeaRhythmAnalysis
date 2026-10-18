"""arcaea-rhythm command line interface."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from . import __version__, pipeline
from .cache import BuildCache
from .config import PROJECT_ROOT, load_config

TOP_HELP = """ArcaeaRhythmAnalysis

usage: arcaea-rhythm <command> [options]

commands:
  build           运行完整流水线（会提示选择谱面/难度）
  list            列出 charts/ 下的谱面文件夹与难度
  doctor          检查 Python、依赖、配置和谱面文件
  migrate-config  把 config.txt 转换为 config.toml

运行 arcaea-rhythm <command> --help 查看该命令参数。
"""


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in ("-h", "--help"):
        print(TOP_HELP)
        return 0
    if arguments[0] in ("-V", "--version"):
        print(f"arcaea-rhythm {__version__}")
        return 0

    command, rest = arguments[0], arguments[1:]
    if command == "build":
        return pipeline.main(rest)
    if command == "list":
        return cmd_list(rest)
    if command == "doctor":
        return cmd_doctor(rest)
    if command == "migrate-config":
        return cmd_migrate_config(rest)

    print(f"未知命令：{command}\n")
    print(TOP_HELP)
    return 2


def cmd_list(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="arcaea-rhythm list", description="列出谱面")
    parser.add_argument("--config", help="配置文件路径（用于标记当前谱面）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    active_folder = None
    if args.config or (PROJECT_ROOT / "config.toml").exists() or (PROJECT_ROOT / "config.txt").exists():
        try:
            active_folder = load_config(args.config).folder
        except (OSError, ValueError):
            active_folder = None

    charts_dir = PROJECT_ROOT / "charts"
    rows: list[dict[str, object]] = []
    if charts_dir.exists():
        for folder in sorted(path for path in charts_dir.iterdir() if path.is_dir()):
            difficulties = [chart for chart in (2, 3, 4) if (folder / f"{chart}.aff").exists()]
            if not difficulties and not any(folder.glob("*.aff")):
                continue
            rows.append({
                "folder": folder.name,
                "difficulties": difficulties,
                "active": folder.name == active_folder,
            })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print(f"没有找到谱面：{charts_dir}")
        return 0
    print("谱面文件夹                 难度")
    for row in rows:
        marker = "*" if row["active"] else " "
        difficulties = ", ".join(str(chart) for chart in row["difficulties"]) or "-"
        print(f"{marker} {row['folder']:<24} {difficulties}")
    return 0


def cmd_doctor(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="arcaea-rhythm doctor", description="环境检查")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--folder", help="检查指定谱面文件夹")
    parser.add_argument("--chart", type=int, choices=(2, 3, 4), help="检查指定难度")
    args = parser.parse_args(argv)

    critical_ok = True
    print("ArcaeaRhythmAnalysis doctor\n")

    python_ok = sys.version_info >= (3, 14)
    print(f"[{'OK' if python_ok else '!!'}] Python {sys.version.split()[0]}（需要 >= 3.14）")
    critical_ok &= python_ok

    for module_name in ("numpy", "soundfile", "soxr", "svgwrite", "tqdm"):
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "?")
            print(f"[OK] {module_name} {version}")
        except Exception as exc:  # noqa: BLE001 - doctor should report any import failure
            print(f"[!!] {module_name} 导入失败：{exc}")
            critical_ok = False

    try:
        cfg = load_config(args.config)
        if args.folder:
            cfg.folder = args.folder
        if args.chart:
            cfg.chart = args.chart
        cfg.__post_init__()
    except (OSError, ValueError) as exc:
        print(f"[!!] 配置：{exc}")
        return 1

    print(f"[OK] 配置：{cfg.source}")
    global_checks = [
        ("tap.wav", (PROJECT_ROOT / "note_sounds" / "tap.wav").is_file(), ""),
        ("arc.wav", (PROJECT_ROOT / "note_sounds" / "arc.wav").is_file(), ""),
        ("字体目录", (PROJECT_ROOT / "fonts").is_dir(), ""),
    ]
    for name, ok, detail in global_checks:
        suffix = f"（{detail}）" if detail else ""
        print(f"[{'OK' if ok else '!!'}] {name}{suffix}")
        critical_ok &= ok

    if cfg.folder and cfg.chart:
        checks = [
            ("谱面目录", cfg.chart_dir.is_dir(), str(cfg.chart_dir)),
            (f"{cfg.chart}.aff", (cfg.chart_dir / f"{cfg.chart}.aff").is_file(), ""),
            ("base 音频", any((cfg.chart_dir / name).is_file() for name in
                              ("base.ogg", "base.mp3", "base.wav", "base.flac")), ""),
        ]
        for name, ok, detail in checks:
            suffix = f"（{detail}）" if detail else ""
            print(f"[{'OK' if ok else '!!'}] {name}{suffix}")
            critical_ok &= ok

        cache_file = cfg.chart_dir / ".arcaea-cache.json"
        cached = BuildCache(cache_file).data["stages"]
        print(f"[{'OK' if cached else '-'}] 缓存：{'、'.join(sorted(cached)) or '尚未生成'}")
    else:
        print("[-] 未选择谱面；用 --folder/--chart 或在 build 时选择。")

    print("\n结果：", "可以运行" if critical_ok else "存在问题，请先修复上面的 [!!] 项")
    return 0 if critical_ok else 1


def cmd_migrate_config(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="arcaea-rhythm migrate-config",
                                     description="config.txt -> config.toml")
    parser.add_argument("--config", help="源配置文件（默认 config.txt）")
    parser.add_argument("--output", default="config.toml", help="输出路径（默认 config.toml）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出")
    args = parser.parse_args(argv)

    source = Path(args.config) if args.config else PROJECT_ROOT / "config.txt"
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    if not source.exists():
        print(f"找不到源配置：{source}", file=sys.stderr)
        return 1

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if output.exists() and not args.force:
        print(f"{output} 已存在；加 --force 覆盖。", file=sys.stderr)
        return 1
    if output.resolve() == source.resolve():
        print("输出路径不能与源配置相同。", file=sys.stderr)
        return 1

    try:
        cfg = load_config(source)
    except (OSError, ValueError) as exc:
        print(f"配置读取失败：{exc}", file=sys.stderr)
        return 1

    text = f"""# 由 arcaea-rhythm migrate-config 生成
# 谱面文件夹/难度在运行时选择，也可用 --folder/--chart 指定。
[chart]
speed = {cfg.speed}
version = {cfg.version}
offset = {cfg.offset}
longchart = {cfg.longchart}

[audio]
volume = {cfg.volume}
format = "{cfg.audio_format}"
slow = {cfg.slow}

[preview]
width = {cfg.width}
"""
    output.write_text(text, encoding="utf-8")
    print(f"已写入 {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
