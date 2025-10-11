import re
import os
from fractions import Fraction

# 读取配置文件
config_file = os.path.join(os.path.dirname(__file__), 'config.txt')
with open(config_file, 'r', encoding='utf-8') as file:
    config_lines = file.readlines()
for line in config_lines:
    if line.startswith('folder='):
        folder = os.path.join(os.path.dirname(__file__), 'charts', f'{line.strip().split('=')[1].strip()}')
    if line.startswith('speed='):
        speed = float(line.strip().split('=')[1].strip())
    if line.startswith('chart='):
        chart = int(line.strip().split('=')[1].strip())
if folder is None:
    raise ValueError("Folder name not found in config file.")

# 设置文件路径
timing_file_path = os.path.join(folder, f'timing_{chart}.txt')
rhythm_file_path = os.path.join(folder, f'rhythm_{chart}.txt')
if chart == 2:
    aff_file_path = os.path.join(folder, '0.aff')
if chart == 3 or chart == 4:
    aff_file_path = os.path.join(folder, '1.aff')

# 解析timing
with open(timing_file_path, 'r', encoding='utf-8') as file:
    timing_lines = file.readlines()
timings = []
for line in timing_lines:
    match = re.search(r"timing\((\d+),([\d.]+),.*\);", line)
    if match:
        timestamp = int(match.group(1))
        bpm = float(match.group(2))
        timings.append((timestamp, bpm))

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

# 使分音单位为指定数值
def processed_fraction(decimal_number):
    closest_fraction = None
    min_difference = float('inf')
    allowed_denominators = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 24]
    
    for denominator in allowed_denominators:
        fraction = Fraction(decimal_number).limit_denominator()
        numerator = round(decimal_number * denominator)
        candidate_fraction = Fraction(numerator, denominator)
        
        difference = abs(decimal_number - float(candidate_fraction))
        if difference < min_difference:
            min_difference = difference
            closest_fraction = candidate_fraction

    return closest_fraction

# 计算音符时值
note_value = []

unique_note_times = [note_times[0]]
for i in range(1, len(note_times)):
    if note_times[i][0] - unique_note_times[-1][0] > 5: # 相差5毫秒以内当成多押
        unique_note_times.append(note_times[i])

for i in range(1, len(unique_note_times)):
    current_time = unique_note_times[i][0]
    previous_time = unique_note_times[i - 1][0]
    
    # 计算跨越多个timing段的情况
    duration = 0
    j = 0
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
print(note_value_str)
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
