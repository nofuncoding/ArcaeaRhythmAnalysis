import argparse
import re
from fractions import Fraction

from arcaea_config import load_config
from arcaea_rhythm.selection import SelectionError, resolve_selection
from arcaea_rhythm.timing import valid_bpm

parser = argparse.ArgumentParser(description='生成节奏数组')
parser.add_argument('--config', help='配置文件路径（默认 config.toml 或 config.txt）')
parser.add_argument('--folder', help='谱面文件夹名（覆盖配置/交互选择）')
parser.add_argument('--chart', type=int, choices=(2, 3, 4), help='难度（覆盖配置/交互选择）')
parser.add_argument('-v', '--verbose', action='store_true', help='打印完整节奏数组')
args = parser.parse_args()

try:
    cfg = load_config(args.config)
    folder_name, chart = resolve_selection(cfg, args.folder, args.chart)
    cfg.folder, cfg.chart = folder_name, chart
    cfg.__post_init__()
except (OSError, ValueError, SelectionError) as exc:
    raise SystemExit(str(exc)) from exc

chart = cfg.chart
speed = cfg.speed

# 设置文件路径
timing_file_path = str(cfg.timing_file)
rhythm_file_path = str(cfg.rhythm_file)
aff_file_path = str(cfg.chart_dir / cfg.aff_name)

# 解析timing
with open(timing_file_path, 'r', encoding='utf-8') as file:
    timing_lines = file.readlines()
timings = []
skipped_timings = 0
for line in timing_lines:
    match = re.search(r"timing\((\d+),([\d.]+),.*\);", line)
    if match:
        timestamp = int(match.group(1))
        bpm = float(match.group(2))
        if not valid_bpm(bpm, cfg.max_bpm):
            skipped_timings += 1
            continue
        timings.append((timestamp, bpm))
if skipped_timings:
    print(f"忽略 {skipped_timings} 个特效 timing。")
if not timings:
    raise SystemExit(f"{timing_file_path} 中没有可用的 timing。")

# 解析音符时间（tap, hold, arc, arctap）
with open(aff_file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()
note_times = []
offset = 0
for line in lines:
    # 匹配offset
    offset_match = re.search(r"AudioOffset:([-]?\d+)", line)
    if offset_match:
        offset = int(offset_match.group(1))
    # 匹配tap音符
    tap_match = re.search(r"\((\d+),\d+\);", line)
    if tap_match:
        start_time = int(tap_match.group(1))
        note_times.append([start_time, False])  # False表示不是标记的音符
    # 匹配hold音符
    hold_match = re.search(r"hold\((\d+),\d+,\d+\);", line)
    if hold_match:
        start_time = int(hold_match.group(1))
        note_times.append([start_time, False])
    # 匹配arc音符
    arc_match = re.search(r"arc\((\d+),.*?,.*?,.*?,.*?,.*?,.*?,(\d),.*?,false\);", line)
    if arc_match:
        start_time = int(arc_match.group(1))
        is_marked = arc_match.group(2) == '2'  # 绿蛇为标记的音符
        note_times.append([start_time, is_marked])
    # 匹配arctap音符
    arctap_matches = re.findall(r"arctap\((\d+)\)", line)
    for start_time_str in arctap_matches:
        start_time = int(start_time_str)
        note_times.append([start_time, False])
note_times = sorted(note_times)
if not note_times:
    raise SystemExit(f"{aff_file_path} 中没有找到音符。")

# 使分音单位为指定数值
def processed_fraction(decimal_number):
    closest_fraction = None
    min_difference = float('inf')
    allowed_denominators = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 24]
    
    for denominator in allowed_denominators:
        numerator = round(decimal_number * denominator)
        candidate_fraction = Fraction(numerator, denominator)
        
        difference = abs(decimal_number - float(candidate_fraction))
        if difference < min_difference:
            min_difference = difference
            closest_fraction = candidate_fraction

    return closest_fraction

# 计算音符时值
note_value = []

# 5ms 内视为多押；同一时间点只要有一条绿蛇/标记音符，就保留标记
unique_note_times = []
i = 0
while i < len(note_times):
    start_time, marked = note_times[i]
    i += 1
    while i < len(note_times) and note_times[i][0] - start_time <= 5:
        marked = marked or note_times[i][1]
        i += 1
    unique_note_times.append([start_time, marked])

timing_index = 0
for i in range(1, len(unique_note_times)):
    current_time = unique_note_times[i][0]
    previous_time = unique_note_times[i - 1][0]
    
    # 计算跨越多个timing段的情况
    # 音符时间单调递增，timing 指针只需向前移动
    duration = 0
    j = timing_index
    while j < len(timings) - 1 and timings[j + 1][0] <= previous_time:
        j += 1
    
    start_time = previous_time
    while j < len(timings) - 1 and timings[j + 1][0] < current_time:
        end_time = timings[j + 1][0]
        bpm = timings[j][1] * speed
        interval_ms = end_time - start_time
        beat_duration = 60000 / bpm
        duration += interval_ms / beat_duration
        start_time = end_time
        j += 1

    # 处理最后一个timing段
    if start_time < current_time:
        end_time = current_time
        bpm = timings[j][1] * speed
        interval_ms = end_time - start_time
        beat_duration = 60000 / bpm
        duration += interval_ms / beat_duration
    timing_index = j

    # 根据持续时间判断音符时值
    duration = processed_fraction(duration)
    is_marked = unique_note_times[i-1][1]
    if duration >= 1/16:
        fractional_duration = f"{Fraction(6 / duration)}." if duration < 4 and 4 / duration % 1 != 0 and 6 / duration % 1 == 0 else f"{Fraction(4 / duration)}"
        if is_marked:
            note_value.append(fractional_duration + "!")    # 标记的音符在最后加感叹号标记
        else:
            note_value.append(fractional_duration)
    else:
        continue
if unique_note_times[len(unique_note_times) - 1][1]:
    note_value.append("-!")
else:
    note_value.append("-")
note_value_str = str(note_value).replace("'", '"')


# 打印结果并将其写入文件
if args.verbose:
    print(note_value_str)
else:
    print(f"rhythm_{chart}.txt：{len(note_value)} 个节奏值")
with open(rhythm_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(note_value_str)

# 将开始时间和每拍时值写入timing.txt文件的开头
first_note_time = note_times[0][0]
with open(timing_file_path, 'r+', encoding='utf-8') as file:
    content = file.read()
    file.seek(0, 0)
    if "offset=" not in content:
        content = f"offset={offset}\n" + content
        file.write(content)
        print(f"Offset: {offset}")
    if "start=" not in content:
        content = f"start={first_note_time}\n" + content
        file.write(content)
        print(f"Start time: {first_note_time}")
    if ",2);" not in content and ",4);" not in content and ",8);" not in content and ",16);" not in content: 
        content = content.replace(");", ",4);")
        content = content.replace(".50,4);", ".50,8);").replace(".25,4);", ".25,16);").replace(".75,4);", ".75,16);")
        file.seek(0) 
        file.write(content)
        file.truncate() 
        print(f"Added note value per beat into file.")
