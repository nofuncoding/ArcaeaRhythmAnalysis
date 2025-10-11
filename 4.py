import re
import os
import math
import keyboard
from pydub import AudioSegment
from tqdm import tqdm
import webbrowser

# 读取配置文件
config_file = os.path.join(os.path.dirname(__file__), 'config.txt')
with open(config_file, 'r', encoding='utf-8') as file:
    config_lines = file.readlines()
slow = 0
for line in config_lines:
    if line.startswith('folder='):
        folder = line.strip().split('=')[1].strip()
    if line.startswith('speed='):
        speed = float(line.strip().split('=')[1].strip())
    if line.startswith('chart='):
        chart = int(line.strip().split('=')[1].strip())
    if line.startswith('offset='):
        offset = int(line.strip().split('=')[1].strip())
    if line.startswith('volume='):
        volume = float(line.strip().split('=')[1].strip())
    if line.startswith('slow='):
        slow = int(line.strip().split('=')[1].strip())
    if line.startswith('longchart='):
        longchart = int(line.strip().split('=')[1].strip())
    if line.startswith('width='):
        width = int(line.strip().split('=')[1].strip()) / 1280
if chart == 2:
    aff_file_path = os.path.join(os.path.dirname(__file__), 'charts', folder, '0.aff')
if chart == 3 or chart == 4:
    aff_file_path = os.path.join(os.path.dirname(__file__), 'charts', folder, '1.aff')
slowtime = 1
rotate = 3
easea = 0.25
easeb = 0.5
if longchart == 0:
    longtime = 210000
else:
    longtime = 360000

# 解析timing，删除相邻行中bpm相同的行
timing_file_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f'timing_{chart}.txt')
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
        current_bpm = parts[1]
        if current_bpm != previous_bpm:
            processed_lines.append(line)
        previous_bpm = current_bpm
if offset == -1:
    offset = start
timing_content = ''.join(processed_lines)

# 解析音符时间（tap, hold, arc, arctap）
with open(aff_file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()
note_times = []
arc_times = []
offset = 0
for line in lines:
    # 匹配offset
    offset_match = re.search(r"AudioOffset:([-]?\d+)", line)
    if offset_match:
        offset = int(offset_match.group(1))
    # 匹配tap音符
    tap_match = re.search(r"\((\d+),\d+\);", line)
    if tap_match:
        start_time = int(tap_match.group(1)) + offset
        note_times.append(start_time)
    # 匹配hold音符
    hold_match = re.search(r"hold\((\d+),\d+,\d+\);", line)
    if hold_match:
        start_time = int(hold_match.group(1)) + offset
        note_times.append(start_time)
    # 匹配arc音符
    arc_match = re.search(r"arc\((\d+),(\d+),.*?,.*?,.*?,.*?,.*?,(\d),\w+,false\);", line)
    if arc_match:
        start_time = int(arc_match.group(1)) + offset
        if arc_match.group(1) != arc_match.group(2):
            arc_times.append(start_time)
    # 匹配arctap音符
    arctap_matches = re.findall(r"arctap\((\d+)\)", line)
    for start_time_str in arctap_matches:
        start_time = int(start_time_str) + offset
        arc_times.append(start_time)
note_times = sorted(note_times)
arc_times = sorted(arc_times)

# 读取音频文件
tap_path = os.path.join(os.path.dirname(__file__), 'note_sounds', f'tap.wav')
arc_path = os.path.join(os.path.dirname(__file__), 'note_sounds', f'arc.wav')
base_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f'base.ogg')
base_type = 'ogg'
if os.path.exists(base_path) == False:
    base_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f'base.mp3')
    base_type = 'mp3'
if os.path.exists(base_path) == False:
    base_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f'base.wav')
    base_type = 'wav'
output_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f"note_{chart}.wav")

# 检查是否已经存在合成后的音频文件
generate_audio = True
if os.path.exists(output_path):
    print(f"文件 {output_path} 已经存在。")
    print("按回车重新生成，按空格跳过。")
    while True:
        if keyboard.is_pressed('enter'):
            break
        if keyboard.is_pressed('space'):
            generate_audio = False
            break

# 执行音频合成
if generate_audio:
    # 加载音频文件
    tap = AudioSegment.from_wav(tap_path) #-6
    arc = AudioSegment.from_wav(arc_path) #-6

    # 在对应的时间戳位置插入tap.wav和arc.wav
    if base_type == 'ogg':
        full_audio = AudioSegment.from_ogg(base_path) + 20 * math.log10(volume)
    elif base_type == 'wav':
        full_audio = AudioSegment.from_wav(base_path) + 20 * math.log10(volume)
    else:
        full_audio = AudioSegment.from_mp3(base_path) + 20 * math.log10(volume)
    total_items = len(note_times) + len(arc_times)
    with tqdm(total=total_items, desc="Processing") as pbar:
        for time in note_times:
            full_audio = full_audio.overlay(tap, position=time)
            pbar.update(1)
        for time in arc_times:
            full_audio = full_audio.overlay(arc, position=time)
            pbar.update(1)

    # 保存合成后的音频
    full_audio.export(output_path, format="mp3")
    print(f"音频文件已保存到 {output_path}")

















    # 生成嵌入的 script 内容
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>节奏解析</title>
    <style>
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
            transform: translate(-50%, -50%) scale({width});
            transform-origin: top left;
            width: 100%; 
            height: 100%; 
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
            width: 173.2px;
            height: 130.8px;
            clip-path: polygon(0% 0%, 87.5% 0%, 100% 50%, 87.5% 100%, 0% 100%);
        }}
        .right-pentagon {{
            position: absolute;
            top: 50px;
            width: 173.2px;
            height: 130.8px;
            clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 12.5% 50%);
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
<div class="scale-container">
    <object class="default-svg" type="image/svg+xml" data="default_{chart}.svg"></object>
    <div class="svg-container">
        <object class="scrolling-svg" type="image/svg+xml" data="rhythm_{chart}.svg"></object>
    </div>
    <div class="left-pentagon" style="background-color: #282828; z-index: 2; left: 0px;"></div>
    <div class="left-pentagon" style="background-color: #ffffff; z-index: 3; left: -7.2px;"></div>
    <div class="left-pentagon" style="background-color: #282828; z-index: 4; left: -18px;"></div>
    <div class="right-pentagon" style="background-color: #282828; z-index: 2; left: 1224px;"></div>
    <div class="right-pentagon" style="background-color: #ffffff; z-index: 3; left: 1231.2px;"></div>
    <div class="right-pentagon" style="background-color: #282828; z-index: 4; left: 1238.4px;"></div>
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
        const folder = `{folder}`;
        const speed = `{speed}`;
        const offset = `{offset}`;
        const actualBpmContainer = document.getElementById('actualBpmContainer');
        const actualBpmValue = document.getElementById('actualBpmValue');

        // 嵌入 timing.txt 的内容
        const timingText = `{timing_content}`;
        const timingRegex = /timing\\((\\d+),\\s*(\\d+\\.?\\d*),\\s*(\\d+\\.?\\d*),\\s*(\\d+\\.?\\d*)\\);/g;

        let match;
        const timings = [];

        while (match = timingRegex.exec(timingText)) {{
            const bpm = parseFloat(match[2]);
            let timestamp = parseFloat(match[1]) - offset;
            timings.push({{ timestamp, bpm }});
        }}

        // 根据speed调整BPM
        timings[0].bpm *= speed;
        for (let i = 1; i < timings.length; i++) {{
            timings[i].bpm *= speed;
            timings[i].timestamp += (4 * 48 * 4 - 218 / 4) / timings[0].bpm / 0.8 * 1000;
        }}

        let scrollDistance = 0.0;
        //let animationStartTime = Date.now() + 14500 * 60 / timings[0].bpm;  // 记录动画开始时间

        const playSound = (soundFile, volume) => {{
            const audio = new Audio(soundFile);
            audio.volume = volume;
            audio.play();
        }};

        // 处理音符播放和滚动的动画
        let startTime = 0;
        let delayTime = 10;
        const scrollAnimation = (index, previousBpm, previousTimestamp) => {{
            if (index < timings.length) {{
                const {{ bpm, timestamp }} = timings[index];
                let nextTimestamp;

                if (index + 1 < timings.length) {{
                    nextTimestamp = timings[index + 1].timestamp;
                }} else {{
                    nextTimestamp = {longtime};
                }}
        if (index != 0) {{
            delayTime = Date.now() - startTime - (timestamp - previousTimestamp);
            }}
            startTime = Date.now();  

                const actualBpm = bpm / speed;
                const duration = (nextTimestamp - timestamp + 1000) / 1000 / {slowtime};
                if (index != 0) {{
                    scrollDistance += (duration * bpm - previousBpm) * 192 / 60 / 4 * {slowtime};
                }} else {{
                    scrollDistance += (duration * bpm) * 192 / 60 / 4 * {slowtime};
                }}
                const scrollingSvg = document.querySelector(".scrolling-svg");
                const defaultSvg = document.querySelector(".default-svg");

                scrollingSvg.style.transition = defaultSvg.style.transition = `transform ${{duration}}s linear`;
                scrollingSvg.style.transform = defaultSvg.style.transform = `scale(4) translateX(-${{scrollDistance}}px)`;

                const bpmNumberDiv = document.querySelector(".bpm-number");

                if (bpmNumberDiv) {{
                    let bpmText = Math.round(bpm).toString();
                    if (bpmText < 100) {{
                        bpmText = " " + bpmText;
                    }}
                    bpmNumberDiv.textContent = bpmText;

                    if (index > 0) {{
                        bpmNumberDiv.style.transition = 'color 0s ease, transform {easea}s ease';
                        bpmNumberDiv.style.color = bpm < previousBpm ? '#0080ff' : bpm > previousBpm ? 'red' : 'white';
                        bpmNumberDiv.style.transform = bpm !== previousBpm ? 'scale(1.1)' : 'scale(1)';
                        setTimeout(() => {{
                            bpmNumberDiv.style.transition = 'color {easeb}s ease, transform {easea}s ease';
                            bpmNumberDiv.style.color = 'white';
                            bpmNumberDiv.style.transform = 'scale(1)';
                        }}, 250);
                    }}
                }}

                actualBpmValue.textContent = actualBpm.toFixed(0);
                if (speed != 1) {{
                    actualBpmContainer.style.display = 'block';
                }}

                if (index + 1 < timings.length) {{
                    setTimeout(() => scrollAnimation(index + 1, bpm, timestamp), nextTimestamp - timestamp - delayTime)/{slowtime};
                }}
            }}
        }};

    function loadAudio(src) {{
        return new Promise(resolve => {{
            const audio = new Audio();
            audio.src = src;
            audio.oncanplaythrough = () => resolve(audio);
        }});
    }}

        (async () => {{
            const noteAudio = await loadAudio("note_{chart}.wav");
            setTimeout(() => {{noteAudio.play();}}, 14850 * 60 / timings[0].bpm);
            scrollAnimation(0, timings[0].bpm, 0);
        }})();
    }});
</script>
</body>
</html>"""






html_path = os.path.join(os.path.dirname(__file__), 'charts', folder, f'index_{chart}.html')
with open(html_path, 'w', encoding='utf-8') as script_file:
    script_file.write(html_content)

print("index.html 已完成替换内容")

# 自动打开保存的SVG文件
webbrowser.open(html_path)
