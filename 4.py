import argparse
import json
import os
import re
import time
import webbrowser

import numpy as np
import soundfile as sf
from tqdm import tqdm

from arcaea_config import load_config
from arcaea_rhythm.audio import add_hit, prepare_sample, write_audio
from arcaea_rhythm.selection import SelectionError, resolve_selection
from arcaea_rhythm.timing import valid_bpm

parser = argparse.ArgumentParser(description='生成节奏解析预览和按键音')
parser.add_argument('--config', help='配置文件路径（默认 config.toml 或 config.txt）')
parser.add_argument('--folder', help='谱面文件夹名（覆盖配置/交互选择）')
parser.add_argument('--chart', type=int, choices=(2, 3, 4), help='难度（覆盖配置/交互选择）')
parser.add_argument('--force', action='store_true', help='强制重新生成音频')
parser.add_argument('--no-audio', action='store_true', help='跳过音频生成，只生成 HTML')
parser.add_argument('--no-open', action='store_true', help='不自动打开浏览器')
parser.add_argument('--audio-format', choices=('flac', 'wav', 'ogg', 'mp3'),
                    help='覆盖配置文件中的音频格式')
args = parser.parse_args()

try:
    cfg = load_config(args.config)
    folder, chart = resolve_selection(cfg, args.folder, args.chart)
    cfg.folder, cfg.chart = folder, chart
    cfg.__post_init__()
except (OSError, ValueError, SelectionError) as exc:
    raise SystemExit(str(exc)) from exc

folder = cfg.folder
chart = cfg.chart
speed = cfg.speed
manual_offset = cfg.offset
volume = cfg.volume
slow = cfg.slow
longchart = cfg.longchart
width = cfg.width / 1280
audio_format = args.audio_format or cfg.audio_format

aff_file_path = str(cfg.chart_dir / cfg.aff_name)
slowtime = 1
rotate = 3
easea = 0.25
easeb = 0.5
longtime = 0

# 解析timing，删除相邻行中bpm相同的行
timing_file_path = str(cfg.timing_file)
with open(timing_file_path, 'r', encoding='utf-8') as file:
    timing_lines = file.readlines()
processed_lines = []
previous_bpm = None
start = 0
for line in timing_lines:
    if line.startswith('start='):
        start = int(line.strip().split('=')[1]) * speed
    parts = line.strip().split(',')
    if len(parts) > 1:
        try:
            current_bpm = float(parts[1])
        except ValueError:
            current_bpm = parts[1]
        if current_bpm != previous_bpm:
            processed_lines.append(line)
        previous_bpm = current_bpm
timings_data = []
skipped_timings = 0
for line in processed_lines:
    match = re.search(r"timing\((\d+),\s*([\d.]+),", line)
    if match:
        bpm = float(match.group(2))
        if not valid_bpm(bpm, cfg.max_bpm):
            skipped_timings += 1
            continue
        timings_data.append({
            "timestamp": int(match.group(1)),
            "bpm": bpm,
        })
if skipped_timings:
    print(f"忽略 {skipped_timings} 个特效 timing。")
if not timings_data:
    raise SystemExit(f"{timing_file_path} 中没有 timing(...) 行。")
timings_json = json.dumps(timings_data, ensure_ascii=False, separators=(',', ':'))

# 解析音符时间（tap, hold, arc, arctap）
with open(aff_file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()
note_times = []
arc_times = []
audio_offset = 0
for line in lines:
    # 匹配 AudioOffset
    offset_match = re.search(r"AudioOffset:([-]?\d+)", line)
    if offset_match:
        audio_offset = int(offset_match.group(1))
    # 谱面时间 + AudioOffset + 手动 offset = 音频时间
    total_offset = audio_offset + manual_offset
    # 匹配tap音符
    tap_match = re.search(r"\((\d+),\d+\);", line)
    if tap_match:
        start_time = int(tap_match.group(1)) + total_offset
        note_times.append(start_time)
    # 匹配hold音符
    hold_match = re.search(r"hold\((\d+),\d+,\d+\);", line)
    if hold_match:
        start_time = int(hold_match.group(1)) + total_offset
        note_times.append(start_time)
    # 匹配arc音符
    arc_match = re.search(r"arc\((\d+),(\d+),.*?,.*?,.*?,.*?,.*?,(\d),\w+,false\);", line)
    if arc_match:
        start_time = int(arc_match.group(1)) + total_offset
        if arc_match.group(1) != arc_match.group(2):
            arc_times.append(start_time)
    # 匹配arctap音符
    arctap_matches = re.findall(r"arctap\((\d+)\)", line)
    for start_time_str in arctap_matches:
        start_time = int(start_time_str) + total_offset
        arc_times.append(start_time)
note_times = sorted(note_times)
arc_times = sorted(arc_times)
html_offset = audio_offset + manual_offset

# 读取音频文件
base_dir = os.path.dirname(__file__)
tap_path = os.path.join(base_dir, 'note_sounds', 'tap.wav')
arc_path = os.path.join(base_dir, 'note_sounds', 'arc.wav')
chart_dir = str(cfg.chart_dir)

base_path = None
for base_name in ('base.ogg', 'base.mp3', 'base.wav', 'base.flac'):
    candidate = os.path.join(chart_dir, base_name)
    if os.path.exists(candidate):
        base_path = candidate
        break
if base_path is None:
    raise SystemExit(f"找不到 base 音频（base.ogg / base.mp3 / base.wav / base.flac）: {chart_dir}")

output_path = os.path.join(chart_dir, f"note_{chart}.{audio_format}")

# 预览至少覆盖最后一个音符和完整 base 音频
base_info = sf.info(base_path)
base_end_ms = base_info.duration * 1000
preview_last = max(note_times + arc_times, default=0)
longtime = max(preview_last + 10000, base_end_ms + 1000)
print(f"Base: {os.path.basename(base_path)} / {base_info.samplerate} Hz / "
      f"{base_info.channels} ch / {base_info.duration:.2f} s")


# 检查是否已经存在合成后的音频文件
generate_audio = not args.no_audio and (args.force or not os.path.exists(output_path))
if not generate_audio:
    if args.no_audio:
        print("已跳过音频生成（--no-audio）。")
    elif os.path.exists(output_path):
        print(f"音频已存在，跳过：{output_path}（--force 可重新生成）。")

# 执行音频合成
if generate_audio:
    started = time.perf_counter()
    base, sr = sf.read(base_path, dtype='float32', always_2d=True)
    tap = prepare_sample(tap_path, sr, base.shape[1])
    arc = prepare_sample(arc_path, sr, base.shape[1])

    # 原实现用 +20*log10(volume) 调整 base 音量，这里等价为线性增益
    base *= np.float32(volume)

    total_items = len(note_times) + len(arc_times)
    with tqdm(total=total_items, desc='Mixing') as pbar:
        for time_ms in note_times:
            add_hit(base, tap, time_ms, sr)
            pbar.update(1)
        for time_ms in arc_times:
            add_hit(base, arc, time_ms, sr)
            pbar.update(1)

    # audioop.add 是饱和相加；最后统一裁剪，避免浮点溢出
    np.clip(base, -1.0, 1.0, out=base)
    write_audio(output_path, base, sr, audio_format)

    elapsed = time.perf_counter() - started
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"音频已保存：{output_path}（{size_mb:.1f} MB，{elapsed:.2f} s）")

















    # 生成嵌入的 script 内容
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>节奏解析</title>
    <style>
        @font-face {{
            font-family: 'Exo';
            src: url('../../fonts/Exo-VariableFont_wght.ttf') format('truetype');
            font-weight: 100 900;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'Edwin';
            src: url('../../fonts/Edwin-BdIta.otf') format('opentype');
        }}
        @font-face {{
            font-family: 'Noto Sans ExtraCondensed';
            src: url('../../fonts/noto-sans-extracondensed.ttf') format('truetype');
        }}
        :root {{
            --scale: 1;
            --design-width: 1280px;
            --design-height: 720px;
            --right-left: calc(var(--design-width) - 56px);
        }}
        body {{
            margin: 0;
            overflow: hidden;
            padding-top: 50px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .scale-container {{
            position: fixed;
            top: 50%;
            left: 50%;
            width: var(--design-width);
            height: var(--design-height);
            transform: translate(-50%, -50%) scale(var(--scale, 1));
            transform-origin: center center;
            overflow: hidden;
        }}
        .svg-container {{
            width: 100%;
            height: 100%;
            position: absolute;
            mask-image: linear-gradient(to right, transparent 12.8%, black 16.8%);
            -webkit-mask-image: linear-gradient(to right, transparent 12.8%, black 16.8%);
        }}
        .scrolling-svg {{
            position: absolute;
            top: 50px;
            left: 0;
            transform-origin: top left;
            transition: transform 1s linear;
            transform: scale(4) translateX(0);
            will-change: transform, transition;
            z-index: 1;
        }}
        .default-svg {{
            position: absolute;
            top: 50px;
            left: 0;
            transform-origin: top left;
            transition: transform 1s linear;
            transform: scale(4) translateX(0);
            will-change: transform, transition;
            z-index: 0;
        }}
        @keyframes rotateAnimation {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .title {{
            font-size: 96px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 80px;
        }}
        .left-pentagon {{
            position: absolute;
            top: 50px;
            left: 0;
            width: 173.2px;
            height: 130.8px;
            clip-path: polygon(0% 0%, 87.5% 0%, 100% 50%, 87.5% 100%, 0% 100%);
        }}
        .right-pentagon {{
            position: absolute;
            top: 50px;
            left: var(--right-left);
            width: 173.2px;
            height: 130.8px;
            clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 12.5% 50%);
        }}
        .left-pentagon.layer-1 {{ left: -7.2px; }}
        .left-pentagon.layer-2 {{ left: -18px; }}
        .right-pentagon.layer-1 {{ left: calc(var(--right-left) + 7.2px); }}
        .right-pentagon.layer-2 {{ left: calc(var(--right-left) + 14.4px); }}
        .start-overlay {{
            position: fixed;
            inset: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(20, 20, 20, 0.85);
            color: white;
            cursor: wait;
            font-family: 'Exo', sans-serif;
            font-size: 28px;
            letter-spacing: 2px;
        }}
        .start-overlay.ready {{ cursor: pointer; }}
        .start-text {{
            padding: 16px 28px;
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.25);
        }}
        .start-overlay.ready:hover .start-text {{
            background: rgba(255, 255, 255, 0.12);
        }}
        .outer-hexagon {{
            position: absolute;
            top: 58.8px;
            left: 16px;
            width: 110px;
            height: 110px;
            clip-path: polygon(
                50% 5%, 
                89% 27.5%, 
                89% 72.5%, 
                50% 95%, 
                11% 72.5%, 
                11% 27.5%
            );
            background-color: white;
            z-index: 5;
            animation: rotateAnimation {rotate}s linear infinite;
        }}

        .inner-hexagon {{
            width: 102px;
            height: 102px;
            margin: 4px;
            background-color: #282828;
            clip-path: polygon(
                50% 5%, 
                89% 27.5%, 
                89% 72.5%, 
                50% 95%, 
                11% 72.5%, 
                11% 27.5%
            );
        }}

        .bpm-label {{
            position: absolute;
            top: 91.2px;
            left: 71.2px;
            transform: translate(-50%, -50%);
            color: white;
            font-family: 'Noto Sans ExtraCondensed', sans-serif;
            font-size: 16px;
            z-index: 6;
            text-align: center;
        }}

        .bpm-number {{
            position: absolute;
            top: 84.8px;
            left: 43.2px;
            transition: color 0.5s ease;
            color: white;
            will-change: transform, transition, color;
            font-family: 'Noto Sans ExtraCondensed', sans-serif;
            font-size: 44px;
            z-index: 6;
            text-align: center;
        }}
        .absolute-circle {{
            position: absolute;
            top: 68px;
            left: 190px;
            width: 56px;
            height: 56px;
            background-color: transparent;
            border: 2px solid white;
            border-radius: 50%;
            z-index: 6;
        }}

        .actual-bpm-container {{
            position: absolute;
            top: 147px;
            left: 10px;
            background-color: rgba(80, 80, 80, 0.8);
            color: white;
            width: 122px;
            height: 28px;
            border-radius: 7px;
            font-family: 'Noto Sans ExtraCondensed', sans-serif;
            font-size: 19px;
            display: none; /* 初始隐藏 */
            text-align: center;
            z-index: 7;
        }}
    </style>
</head>
<body>
<div class="start-overlay" id="startOverlay">
    <div class="start-text">加载中…</div>
</div>
<div class="scale-container">
    <object class="default-svg" type="image/svg+xml" data="default_{chart}.svg"></object>
    <div class="svg-container">
        <object class="scrolling-svg" type="image/svg+xml" data="rhythm_{chart}.svg"></object>
    </div>
    <div class="left-pentagon" style="background-color: #282828; z-index: 2;"></div>
    <div class="left-pentagon layer-1" style="background-color: #ffffff; z-index: 3;"></div>
    <div class="left-pentagon layer-2" style="background-color: #282828; z-index: 4;"></div>
    <div class="right-pentagon" style="background-color: #282828; z-index: 2;"></div>
    <div class="right-pentagon layer-1" style="background-color: #ffffff; z-index: 3;"></div>
    <div class="right-pentagon layer-2" style="background-color: #282828; z-index: 4;"></div>
    <div class="outer-hexagon">
        <div class="inner-hexagon"></div>
    </div>
    <div class="bpm-label">BPM</div>
    <div class="bpm-number"></div>
    <div class="absolute-circle"></div>
    <div class="actual-bpm-container" id="actualBpmContainer">
        Actual BPM: <span id="actualBpmValue"></span>
    </div>
</div>

<script>
    document.addEventListener("DOMContentLoaded", function() {{
        const speed = Number(`{speed}`);
        const offset = Number(`{html_offset}`);
        const actualBpmContainer = document.getElementById('actualBpmContainer');
        const actualBpmValue = document.getElementById('actualBpmValue');
        const overlay = document.getElementById('startOverlay');
        const overlayText = overlay.querySelector('.start-text');

        // timing 数据由 Python 以 JSON 注入，避免字符串解析与转义问题
        const timings = {timings_json};

        if (!timings.length) {{
            overlayText.textContent = 'timing 数据为空';
            return;
        }}

        // speed 只影响 BPM；时间轴边界使用音频时间（chart timestamp + offset）
        for (const timing of timings) {{
            timing.bpm *= speed;
        }}
        const leadIn = (14850 * 60 / timings[0].bpm) / 1000;
        const lastBoundary = leadIn + (timings[timings.length - 1].timestamp + offset) / 1000;
        const timelineEnd = Math.max(leadIn + {longtime} / 1000, lastBoundary + 10);

        // 视口自适应：1280x720 设计稿等比缩放
        const DESIGN_WIDTH = 1280;
        const DESIGN_HEIGHT = 720;
        const CONFIG_SCALE = {width};
        const fit = () => {{
            const scale = Math.min(window.innerWidth / DESIGN_WIDTH,
                                   window.innerHeight / DESIGN_HEIGHT) * CONFIG_SCALE;
            document.documentElement.style.setProperty('--scale', String(Math.max(scale, 0.1)));
        }};
        fit();
        window.addEventListener('resize', fit);


        const scrollingSvg = document.querySelector(".scrolling-svg");
        const defaultSvg = document.querySelector(".default-svg");
        const bpmNumberDiv = document.querySelector(".bpm-number");
        const PIXELS_PER_BEAT = 192 / 60 / 4;

        // 时间轴：0 = 点击时刻，leadIn 后音频开始；边界 = leadIn + (chart timestamp + offset)
        const segments = [];
        let segmentStart = 0;
        for (let i = 0; i < timings.length; i++) {{
            const end = i + 1 < timings.length
                ? leadIn + (timings[i + 1].timestamp + offset) / 1000
                : timelineEnd;
            if (end <= segmentStart) continue;
            segments.push({{
                start: segmentStart,
                end: end,
                bpm: timings[i].bpm,
            }});
            segmentStart = end;
        }}

        let timelineDistance = 0;
        for (const segment of segments) {{
            segment.startDistance = timelineDistance;
            timelineDistance += (segment.end - segment.start) * segment.bpm * PIXELS_PER_BEAT;
            segment.endDistance = timelineDistance;
        }}

        scrollingSvg.style.transition = defaultSvg.style.transition = 'none';

        let currentSegment = -1;
        let currentBpm = timings[0].bpm;
        const updateBpmDisplay = (segment, index) => {{
            const bpm = segment.bpm;
            const previousBpm = currentBpm;
            currentBpm = bpm;
            const actualBpm = bpm / speed;
            if (bpmNumberDiv) {{
                let bpmText = Math.round(bpm).toString();
                if (bpmText < 100) {{
                    bpmText = " " + bpmText;
                }}
                bpmNumberDiv.textContent = bpmText;
                if (index > 0 && bpm !== previousBpm) {{
                    bpmNumberDiv.style.transition = 'color 0s ease, transform {easea}s ease';
                    bpmNumberDiv.style.color = bpm < previousBpm ? '#0080ff' : 'red';
                    bpmNumberDiv.style.transform = 'scale(1.1)';
                    setTimeout(() => {{
                        bpmNumberDiv.style.transition = 'color {easeb}s ease, transform {easea}s ease';
                        bpmNumberDiv.style.color = 'white';
                        bpmNumberDiv.style.transform = 'scale(1)';
                    }}, 130);
                }}
            }}
            actualBpmValue.textContent = actualBpm.toFixed(0);
            if (speed != 1) {{
                actualBpmContainer.style.display = 'block';
            }}
        }};

        const findSegment = (elapsed) => {{
            for (let i = 0; i < segments.length; i++) {{
                if (elapsed < segments[i].end || i === segments.length - 1) return i;
            }}
            return segments.length - 1;
        }};

        const renderAt = (elapsed) => {{
            if (!segments.length) return;
            const index = findSegment(elapsed);
            if (index !== currentSegment) {{
                currentSegment = index;
                updateBpmDisplay(segments[index], index);
            }}
            const segment = segments[index];
            const local = Math.max(0, Math.min(elapsed, segment.end) - segment.start);
            const distance = segment.startDistance + local * segment.bpm * PIXELS_PER_BEAT;
            scrollingSvg.style.transform = defaultSvg.style.transform =
                `scale(4) translateX(-${{distance}}px)`;
        }};

        const startAnimation = () => {{
            const start = performance.now();
            const tick = (now) => {{
                const elapsed = (now - start) / 1000;
                renderAt(elapsed);
                if (elapsed < timelineEnd) {{
                    requestAnimationFrame(tick);
                }}
            }};
            requestAnimationFrame(tick);
        }};

    function loadAudio(src) {{
        return new Promise((resolve, reject) => {{
            const audio = new Audio();
            audio.src = src;
            audio.preload = 'auto';
            audio.oncanplaythrough = () => resolve(audio);
            audio.onloadeddata = () => resolve(audio);
            audio.onerror = () => reject(new Error('无法加载音频'));
            audio.load();
        }});
    }}

        (async () => {{
            let noteAudio = null;
            try {{
                noteAudio = await loadAudio("note_{chart}.{audio_format}");
                overlayText.textContent = '点击开始';
            }} catch (err) {{
                console.warn(err);
                overlayText.textContent = '点击开始（无音频）';
            }}
            overlay.classList.add('ready');
            overlay.tabIndex = 0;
            overlay.focus();

            let started = false;
            const startPlayback = () => {{
                if (started) return;
                started = true;
                overlay.style.display = 'none';
                if (noteAudio) {{
                    setTimeout(() => {{
                        noteAudio.play().catch(err => console.warn(err));
                    }}, leadIn * 1000);
                }}
                startAnimation();
            }};
            overlay.addEventListener('click', startPlayback, {{ once: true }});
            overlay.addEventListener('keydown', (event) => {{
                if (event.key === 'Enter' || event.key === ' ') startPlayback();
            }});
        }})();
    }});
</script>
</body>
</html>"""






html_path = str(cfg.chart_dir / f'index_{chart}.html')
with open(html_path, 'w', encoding='utf-8') as script_file:
    script_file.write(html_content)

print("index.html 已完成替换内容")

# 自动打开保存的SVG文件
if not args.no_open:
    webbrowser.open(html_path)
