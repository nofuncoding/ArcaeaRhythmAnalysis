#!/usr/bin/env python3
"""一条命令运行 ArcaeaRhythmAnalysis 的四个阶段。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from .cache import BuildCache
from .config import Config, PROJECT_ROOT, load_config
from .selection import SelectionError, resolve_selection

ROOT = PROJECT_ROOT
RUN_STAGES = ("arcs", "rhythm", "svg", "audio", "preview")
STAGES = ("all", *RUN_STAGES)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 Arcaea 节奏解析流水线（1.py → 2.py → 3.py → 4.py）"
    )
    stage_group = parser.add_mutually_exclusive_group()
    stage_group.add_argument("--stage", choices=STAGES, default=None,
                             help="只运行指定阶段；默认 all")
    stage_group.add_argument("--from", dest="from_stage", choices=RUN_STAGES,
                             help="从指定阶段运行到结尾（用于手动修改后继续）")
    parser.add_argument("--config", help="配置文件路径（默认 config.toml 或 config.txt）")
    parser.add_argument("--folder", help="覆盖配置中的谱面文件夹")
    parser.add_argument("--chart", type=int, choices=(2, 3, 4), help="覆盖配置中的难度")
    parser.add_argument("--max-bpm", type=float,
                        help="过滤高于该值的特效 BPM；默认 1000，0 表示不限制")
    bpm_group = parser.add_mutually_exclusive_group()
    bpm_group.add_argument("--ignore-effect-bpm", action="store_true",
                           help="兼容项：默认已按 max_bpm=1000 过滤，可显式指定")
    bpm_group.add_argument("--keep-effect-bpm", "--no-ignore-effect-bpm",
                           dest="keep_effect_bpm", action="store_true",
                           help="保留 9999999 等特效 BPM（等价于 --max-bpm 0）")
    parser.add_argument("--force", action="store_true",
                        help="忽略缓存，强制重新生成 1.aff/0.aff 和按键音")
    parser.add_argument("--no-cache", action="store_true",
                        help="不读写阶段缓存")
    parser.add_argument("--refresh-timing", action="store_true",
                        help="重新提取 timing_{chart}.txt（会覆盖手动修改）")
    parser.add_argument("--no-audio", action="store_true",
                        help="跳过按键音生成，只生成 HTML")
    parser.add_argument("--no-open", action="store_true",
                        help="不自动打开浏览器")
    parser.add_argument("--audio-format", choices=("flac", "wav", "ogg", "mp3"),
                        help="覆盖配置文件中的音频输出格式")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示 timing、节奏数组等详细中间结果")
    parser.add_argument("-y", "--yes", "--no-confirm", action="store_true",
                        dest="yes", help="跳过阶段之间的 Y/n 确认（适合自动化）")
    return parser.parse_args(argv)


def read_config(config_path: str | None = None) -> Config:
    return load_config(config_path)


def find_base_audio(cfg: Config) -> Path | None:
    for name in ("base.ogg", "base.mp3", "base.wav", "base.flac"):
        candidate = cfg.chart_dir / name
        if candidate.exists():
            return candidate
    return None


def ask_confirm(question: str, assume_yes: bool) -> bool:
    """交互式 Y/n 确认；非 TTY 或 --yes 时自动继续。"""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("（非交互环境，自动继续；加 --yes 可显式跳过确认）", flush=True)
        return True
    while True:
        try:
            answer = input(f"{question} [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("请输入 Y 或 n。")


def pause(next_stage: str, message: str) -> None:
    print(f"\n已暂停：{message}")
    print(f"修改完成后继续运行：python run.py --from {next_stage}")


def run_stage(name: str, script: str, extra: list[str]) -> None:
    command = [sys.executable, str(ROOT / script), *extra]
    print(f"\n== {name}: {' '.join(command[1:])}", flush=True)
    started = time.perf_counter()
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"== {name} 完成，用时 {time.perf_counter() - started:.2f}s", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.from_stage:
        selected = set(RUN_STAGES[RUN_STAGES.index(args.from_stage):])
    elif args.stage and args.stage != "all":
        selected = {args.stage}
    else:
        selected = set(RUN_STAGES)

    try:
        cfg = read_config(args.config)
        folder, chart = resolve_selection(cfg, args.folder, args.chart)
        cfg.folder, cfg.chart = folder, chart
        if args.ignore_effect_bpm:
            cfg.max_bpm = 1000.0
        if args.keep_effect_bpm:
            cfg.max_bpm = 0.0
        if args.max_bpm is not None:
            cfg.max_bpm = args.max_bpm
        cfg.__post_init__()
    except (OSError, ValueError, SelectionError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 1

    os.environ["ARCAEA_FOLDER"] = cfg.folder
    os.environ["ARCAEA_CHART"] = str(cfg.chart)
    os.environ["ARCAEA_MAX_BPM"] = str(cfg.max_bpm)
    os.environ["ARCAEA_SUBPROCESS"] = "1"
    folder, chart = cfg.folder, cfg.chart
    chart_dir = f"charts/{folder}"
    aff_file = f"{chart_dir}/{cfg.aff_name}"
    timing_file = f"{chart_dir}/timing_{chart}.txt"
    rhythm_file = f"{chart_dir}/rhythm_{chart}.txt"
    audio_format = args.audio_format or cfg.audio_format
    note_file = cfg.chart_dir / f"note_{chart}.{audio_format}"
    html_file = cfg.chart_dir / f"index_{chart}.html"
    default_svg = cfg.chart_dir / f"default_{chart}.svg"
    base_path = find_base_audio(cfg)
    tap_path = ROOT / "note_sounds" / "tap.wav"
    arc_path = ROOT / "note_sounds" / "arc.wav"
    config_flags = ["--config", args.config] if args.config else []
    cache = None if args.no_cache else BuildCache(cfg.chart_dir / ".arcaea-cache.json")

    def stage_key(files: list[Path | None], config: dict) -> str:
        clean = [Path(path) for path in files if path is not None]
        return cache.make_key(clean, config) if cache else ""

    def is_fresh(stage: str, key: str, outputs: list[Path]) -> bool:
        return bool(cache and not args.force and cache.fresh(stage, key, outputs))

    def remember(stage: str, files: list[Path | None], config: dict, outputs: list[Path]) -> None:
        if cache:
            clean = [Path(path) for path in files if path is not None]
            cache.update(stage, cache.make_key(clean, config), outputs)
            cache.save()

    try:
        if "arcs" in selected:
            extra = list(config_flags)
            if args.force:
                extra.append("--force")
            if args.refresh_timing:
                extra.append("--refresh-timing")
            run_stage("arcs", "1.py", extra)
            if "rhythm" in selected and not ask_confirm(
                f"请检查 {aff_file}、{timing_file} 是否手动修改完毕？", args.yes
            ):
                pause("rhythm", "请先检查/修改 1.aff（或 0.aff）和 timing 文件。")
                return 0

        if "rhythm" in selected:
            rhythm_inputs = [cfg.output_aff, cfg.timing_file]
            rhythm_config = {"speed": cfg.speed, "chart": cfg.chart, "max_bpm": cfg.max_bpm}
            rhythm_key = stage_key(rhythm_inputs, rhythm_config)
            if is_fresh("rhythm", rhythm_key, [cfg.rhythm_file, cfg.timing_file]):
                print("\n== rhythm: 缓存命中，跳过（--force 可重建）", flush=True)
            else:
                extra = list(config_flags)
                if args.verbose:
                    extra.append("--verbose")
                run_stage("rhythm", "2.py", extra)
                remember("rhythm", rhythm_inputs, rhythm_config, [cfg.rhythm_file, cfg.timing_file])
                if "svg" in selected and not ask_confirm(
                    f"请检查 {rhythm_file} 是否手动调整完毕？", args.yes
                ):
                    pause("svg", "请先检查/修改 rhythm 文件。")
                    return 0

        if "svg" in selected:
            svg_inputs = [cfg.timing_file, cfg.rhythm_file]
            svg_config = {
                "speed": cfg.speed,
                "version": cfg.version,
                "longchart": cfg.longchart,
                "chart": cfg.chart,
                "max_bpm": cfg.max_bpm,
            }
            svg_outputs = [cfg.svg_file, default_svg]
            svg_key = stage_key(svg_inputs, svg_config)
            if is_fresh("svg", svg_key, svg_outputs):
                print("\n== svg: 缓存命中，跳过（--force 可重建）", flush=True)
            else:
                extra = list(config_flags)
                if args.verbose:
                    extra.append("--verbose")
                run_stage("svg", "3.py", extra)
                remember("svg", svg_inputs, svg_config, svg_outputs)
                next_label = "网页预览" if (args.no_audio or not ("audio" in selected)) else "音频和网页预览"
                if ("audio" in selected or "preview" in selected) and not ask_confirm(
                    f"SVG 已生成，是否继续生成{next_label}？", args.yes
                ):
                    pause("audio", "请先检查 SVG；若只想生成 HTML，可用 --stage preview。")
                    return 0

        wants_audio = "audio" in selected and not args.no_audio
        wants_preview = "preview" in selected
        if wants_audio or wants_preview:
            audio_inputs = [cfg.output_aff, cfg.timing_file, base_path, tap_path, arc_path]
            audio_config = {
                "volume": cfg.volume,
                "offset": cfg.offset,
                "audio_format": audio_format,
                "slow": cfg.slow,
            }
            preview_inputs = [cfg.output_aff, cfg.timing_file, base_path]
            preview_config = {
                "speed": cfg.speed,
                "offset": cfg.offset,
                "width": cfg.width,
                "longchart": cfg.longchart,
                "audio_format": audio_format,
                "chart": cfg.chart,
                "max_bpm": cfg.max_bpm,
            }
            audio_key = stage_key(audio_inputs, audio_config)
            preview_key = stage_key(preview_inputs, preview_config)
            audio_fresh = wants_audio and is_fresh("audio", audio_key, [note_file])
            preview_fresh = wants_preview and is_fresh("preview", preview_key, [html_file])
            need_audio = wants_audio and not audio_fresh
            need_preview = wants_preview and not preview_fresh

            if not need_audio and not need_preview:
                print("\n== audio/preview: 缓存命中，跳过（--force 可重建）", flush=True)
            else:
                extra = list(config_flags)
                if need_audio:
                    extra.append("--force")
                if not need_audio:
                    extra.append("--no-audio")
                if args.no_open:
                    extra.append("--no-open")
                if args.audio_format:
                    extra.extend(["--audio-format", args.audio_format])
                run_stage("preview", "4.py", extra)
                if need_audio:
                    remember("audio", audio_inputs, audio_config, [note_file])
                    remember("preview", preview_inputs, preview_config, [html_file])
                elif need_preview:
                    remember("preview", preview_inputs, preview_config, [html_file])
    except subprocess.CalledProcessError as exc:
        print(f"\n阶段失败：{exc.cmd[-2]}（exit code {exc.returncode}）", file=sys.stderr)
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
