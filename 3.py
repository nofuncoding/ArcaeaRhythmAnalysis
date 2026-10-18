import argparse
import json
import math
import shutil

import svgwrite
from fractions import Fraction

from arcaea_config import load_config
from arcaea_rhythm.selection import SelectionError, resolve_selection
from arcaea_rhythm.timing import measure_aligned, valid_bpm, valid_beats_per_measure

parser = argparse.ArgumentParser(description='生成节奏 SVG')
parser.add_argument('--config', help='配置文件路径（默认 config.toml 或 config.txt）')
parser.add_argument('--folder', help='谱面文件夹名（覆盖配置/交互选择）')
parser.add_argument('--chart', type=int, choices=(2, 3, 4), help='难度（覆盖配置/交互选择）')
parser.add_argument('-v', '--verbose', action='store_true', help='打印 timing、小节线等中间结果')
args = parser.parse_args()

try:
    cfg = load_config(args.config)
    folder_name, chart = resolve_selection(cfg, args.folder, args.chart)
    cfg.folder, cfg.chart = folder_name, chart
    cfg.__post_init__()
except (OSError, ValueError, SelectionError) as exc:
    raise SystemExit(str(exc)) from exc

speed = cfg.speed
chart = cfg.chart
version = cfg.version
longchart = cfg.longchart

def format_number(value):
    if value % 1 == 0:  # 判断值是否为整数
        return int(value)
    else:
        return value

# 解析timing.txt文件内容并检查是否为其他音符为一拍
timing_file_path = str(cfg.timing_file)
with open(timing_file_path, 'r', encoding='utf-8') as file:
    timing_lines = file.readlines()
timing_info = []
start = 0
offset = 0
for line in timing_lines:
    if line.startswith('start='):
        start = int(line.strip().split('=')[1]) * speed
        if args.verbose:
            print(f"start={start}")
    elif line.startswith('offset='):
        offset = int(line.strip().split('=')[1].strip())
        if args.verbose:
            print(f"offset={offset}")
    elif line.startswith('timing('):
        parts = line.strip().strip('timing()').split(',')
        timestamp = int(parts[0])
        bpm = float(parts[1])
        beats_per_measure = float(parts[2].rstrip(');'))
        note_value_per_beat = float(parts[3].rstrip(');')) if len(parts) > 3 else 4.0
        timing_info.append((timestamp, bpm, beats_per_measure, note_value_per_beat))

# 过滤特效 timing（BPM 0/极大值、999/1024 拍号），避免负坐标和异常分段
raw_timing_info = list(timing_info)
raw_timing_count = len(timing_info)
timing_info = [
    item for item in timing_info
    if valid_bpm(item[1], cfg.max_bpm) and valid_beats_per_measure(item[2])
]
skipped_timings = raw_timing_count - len(timing_info)
if skipped_timings:
    print(f"忽略 {skipped_timings} 个特效 timing。")
if not timing_info:
    raise SystemExit(f"{timing_file_path} 中没有可用的 timing。")

# 第一个有效 timing 可能不是 0（例如 0ms 的拍号是特效值）。
# 补一个 0ms 锚点，保证第一段 BPM/拍号与谱面开头一致。
if raw_timing_info and timing_info[0][0] > 0:
    first = raw_timing_info[0]
    anchor_bpm = first[1] if valid_bpm(first[1], cfg.max_bpm) else timing_info[0][1]
    anchor_meter = first[2] if valid_beats_per_measure(first[2]) else 4.0
    anchor_note = first[3] if first[3] > 0 else 4.0
    timing_info.insert(0, (0, anchor_bpm, anchor_meter, anchor_note))

# 计算每个timing在全曲中的拍数并存储到一个数组中
timing_beats = []
current_beat = 16 / speed
last_timestamp = 0
last_bpm = timing_info[0][1]  # 初始的BPM为第一个timing的BPM

# 计算每个timing在全曲中的拍数并存储到一个数组中
for i, (timestamp, bpm, beats_per_measure, note_value_per_beat) in enumerate(timing_info):
    beat_per_minute = last_bpm / 60
    # 计算自上一个timing以来的拍数
    delta_time = timestamp - last_timestamp
    # 不四舍五入累计拍数，避免大量 BPM 变化时误差累积
    delta_beats = delta_time / 1000 * beat_per_minute
    current_beat += delta_beats
    next_timestamp = timing_info[i + 1][0] if i + 1 < len(timing_info) else timestamp
    next_delta_time = next_timestamp - timestamp
    next_delta_beats = round(next_delta_time / 1000 * bpm / 60, 2)
    timing_beats.append((current_beat, bpm, beats_per_measure, next_delta_beats, note_value_per_beat))
    last_timestamp = timestamp
    last_bpm = bpm  # 更新BPM

# 打印每个timing对应的拍数，并同时输出到下个timing有多少拍
if args.verbose:
    for i, (current_beat, bpm, beats_per_measure, next_delta_beats, note_value_per_beat) in enumerate(timing_beats):
        print(f"Timing {i}: {format_number(round(next_delta_beats, 2))}({format_number(round(current_beat, 2))}), {format_number(bpm)}, {format_number(beats_per_measure)}, {note_value_per_beat}")

# 读取节奏数组并预先计算音符位置，用于确定 SVG 的实际长度
rhythm_file_path = str(cfg.rhythm_file)
with open(rhythm_file_path, 'r', encoding='utf-8') as file:
    note_values_str = json.loads(file.read())

# 归一化音符时值
note_values = []
adjusted_note_values = []
prev_value = note_values_str[0].rstrip('!')
for value in note_values_str:
    current_value = value
    marked = False
    if value.endswith('!'):
        current_value = value.rstrip('!')
        marked = True
    base_value = float(current_value.rstrip('.')) / 1.5 if current_value.endswith('.') else float(Fraction(current_value)) if current_value != "-" else 1.0
    prev_base_value = float(prev_value.rstrip('.')) / 1.5 if prev_value.endswith('.') else float(Fraction(prev_value)) if prev_value != "-" else 1.0
    note_values.append(base_value)
    if base_value > prev_base_value:
        processed_value = current_value
    else:
        processed_value = prev_value
    if processed_value == '-':
        processed_value = '1'
    if marked:
        processed_value += "!"
    adjusted_note_values.append(processed_value)
    prev_value = current_value

# 计算每个音符的位置
measures_passed_time = start / 1000 * (timing_info[0][1] / 60) / timing_info[0][2]
current_position = 768 + measures_passed_time * timing_info[0][2] * 48
note_positions = []
for value in note_values:
    note_positions.append(current_position)
    current_position += 48 * 4 / value

# 原固定长度作为最短长度；长音频按最后一个音符自动延长，避免 SVG 被截断
legacy_total_length = 32640 if longchart == 0 else 57600
content_end_px = note_positions[-1] if note_positions else 0
tail_padding_px = 48 * 8  # 末尾至少留 8 拍
total_length = max(legacy_total_length, int(math.ceil((content_end_px + tail_padding_px) / 12.0)) * 12)
total_beats = total_length / (48 * speed)

# 过滤出合适的 timing
filtered_timings = []
last_beat = 16 / speed
last_beats_per_measure = timing_info[0][2]

for i, (current_beat, bpm, beats_per_measure, next_delta_beats, note_value_per_beat) in enumerate(timing_beats):
    # 用“整数个小节”判断对齐，避免浮点取模把 24.0 算成 1.999...
    delta_beats = current_beat - last_beat
    if measure_aligned(delta_beats, last_beats_per_measure):
        filtered_timings.append((current_beat, bpm, beats_per_measure, note_value_per_beat))
        last_beat = current_beat
    last_beats_per_measure = beats_per_measure  # 更新为当前的 beats_per_measure

# 确保 current_index 在有效范围内
current_index = 0  # 假设 current_index 从 0 开始
while current_index < len(filtered_timings):
    current_beat += filtered_timings[current_index][2]  # 确保 current_index 不会超出范围
    current_index += 1  # 增加 current_index 以继续循环
if len(timing_info) == 1:
    filtered_timings = timing_info

# 打印 filtered_timings
if args.verbose:
    for timing in filtered_timings:
        print(f"Filtered Timing: {format_number(round(timing[0], 1))}, {format_number(timing[1])}, {format_number(timing[2])}, {timing[3]}")

# 生成小节线位置数组
measure_positions = []
current_beat_forward = current_beat = 16 / speed
while current_beat_forward > 0:
    measure_positions.append(current_beat_forward)
    current_beat_forward -= timing_info[0][2]
measure_positions = sorted(set(measure_positions))
current_index = 0
while current_beat <= total_beats:
    measure_positions.append(format_number(round(current_beat, 2)))
    if current_index < len(filtered_timings) - 1 and current_beat >= filtered_timings[current_index + 1][0]:
        current_index += 1
    if current_index >= len(filtered_timings):
        current_beat += timing_info[-1][2]  # 使用最后一个 timing 的 beats_per_measure 继续扩展
    else:
        current_beat += filtered_timings[current_index][2]
print(f"Total Beats: {format_number(total_beats)}")
if args.verbose:
    print(measure_positions)
measure_position_set = set(measure_positions)

# 生成每一拍的竖线位置数组
beat_positions = []
current_beat = max(0, 16 - 8 * timing_info[0][2])

for i, timing in enumerate(filtered_timings):
    start_beat = timing[0]
    bpm = timing[1]
    beats_per_measure = timing[2]
    note_value_per_beat = timing[3]
    increment = 4 / note_value_per_beat

    # 确定下一个timing的起始拍数或者总拍数
    next_start_beat = filtered_timings[i + 1][0] if i + 1 < len(filtered_timings) else total_beats
    while current_beat < next_start_beat:
        beat_positions.append(format_number(current_beat))
        current_beat += increment

# 创建SVG绘图对象，设置黑色背景
# total_length 已在读取 rhythm 后按实际内容计算
svg_file_path = str(cfg.svg_file)
default_svg_file_path = str(cfg.chart_dir / f'default_{chart}.svg')
dwg = svgwrite.Drawing(svg_file_path, size=(f'{total_length}px', '48px'))
dwg.add(dwg.style(
    "@font-face { font-family: 'Edwin'; "
    "src: url('../../fonts/Edwin-BdIta.otf') format('opentype'); } "
    "@font-face { font-family: 'Exo'; "
    "src: url('../../fonts/Exo-VariableFont_wght.ttf') format('truetype'); "
    "font-weight: 100 900; }"
))
dwg.add(dwg.rect(insert=(0, 0), size=('100%', '32px'), fill='black'))

# 绘制时间轴，每12px一个小圆点
for i in range(0, int(total_length), 12):
    pos_beat = i / (48 * speed)
    if pos_beat not in measure_position_set:
        dwg.add(dwg.circle(center=(i, 12), r=0.4, fill='white'))

# 绘制小节线
for pos in measure_positions:
    pos_px = pos * 48 * speed
    dwg.add(dwg.line(start=(pos_px, 2.5), end=(pos_px, 21.5), stroke=svgwrite.rgb(255, 255, 255, '%'), stroke_width=1))

# 绘制每一拍的竖线
for beat in beat_positions:
    pos = beat * 48 * speed
    # 只在不是小节线的位置绘制
    if pos / (48 * speed) not in measure_position_set:
        dwg.add(dwg.line(start=(pos, 4.5), end=(pos, 7.5), stroke=svgwrite.rgb(255, 255, 255, '%'), stroke_width=0.4))
        dwg.add(dwg.line(start=(pos, 16.5), end=(pos, 19.5), stroke=svgwrite.rgb(255, 255, 255, '%'), stroke_width=0.4))

# 在图片最下方加上白底和黑线，并保存default.svg
dwg.add(dwg.rect(insert=(0, 24), size=(total_length, 8), fill='white'))
dwg.add(dwg.line(start=(0, 32.4), end=(total_length, 32.4), stroke='black', stroke_width=0.4))
dwg.save()
shutil.copyfile(svg_file_path, default_svg_file_path)











# 颜色函数
def get_color(value):
    color_map = {
        '2': 'darkblue',
        '3': '#006800',
        '4': 'darkblue',
        '5': '#5F0438',
        '6': '#006800',
        '7': '#492788',
        '8': 'red',
        '9': '#396E72',
        '10': '#8F2874',
        '12': '#ff7700',
        '14': '#7C3ED3',
        '16': '#0080ff',
        '18': '#009D6F',
        '20': '#FD4294',
        '24': '#33ff00',
        '28': '#ae70ff',
        '32': '#00ffff',
        '48': '#bbff77',
        '-': '#393939'
    }
    if value in color_map:
        return color_map[value]
    elif Fraction(value) > 2:
        return 'gray'
    else:
        return '#393939'

# 判断连音数函数
def tuplet_judge(m):
    n = 2 * m
    if n.is_integer():
        while n % 2 == 0:
            n //= 2
    else:
        n = 1
    return int(n)

# 绘制音符
for pos, value, adjusted_value in zip(note_positions, note_values_str, adjusted_note_values):
    color = get_color(adjusted_value.rstrip('!').rstrip('.'))

    if adjusted_value.strip('!').endswith('.'):  # 判断是否是附点音符
        if value.endswith('!'):  # 判断是否是标记的音符
            dwg.add(dwg.rect(insert=(pos - 4.6, 12 - 4.6), size=(9.2, 9.2), stroke='white', stroke_dasharray='1,1', stroke_width=0.5, transform='rotate(45, {0}, {1})'.format(pos, 12)))
            dwg.add(dwg.rect(insert=(pos - 4.1, 12 - 4.1), size=(8.2, 8.2), fill=color, stroke='black', stroke_width=0.5, transform='rotate(45, {0}, {1})'.format(pos, 12)))
        else:
            dwg.add(dwg.rect(insert=(pos - 4.6, 12 - 4.6), size=(9.2, 9.2), fill='white', stroke='white', stroke_width=0.5, transform='rotate(45, {0}, {1})'.format(pos, 12)))
            dwg.add(dwg.rect(insert=(pos - 4.1, 12 - 4.1), size=(8.2, 8.2), fill=color, stroke='black', stroke_width=0.5, transform='rotate(45, {0}, {1})'.format(pos, 12)))
    elif adjusted_value.strip('!') == '64/5': # 对5:3跳拍的特殊适配
        if value.endswith('!'):  # 判断是否是标记的音符
            dwg.add(dwg.circle(center=(pos, 12), r=5.75, stroke='#00CC00', stroke_width=0.7, fill='black', stroke_dasharray='1.004,1.003'))
        else:
            dwg.add(dwg.circle(center=(pos, 12), r=5.75, stroke='#00CC00', stroke_width=0.7, fill='black'))
        dwg.add(dwg.circle(center=(pos, 12), r=5, fill=color))
    else: # 不是附点音符
        if value.endswith('!'):  # 判断是否是标记的音符
            dwg.add(dwg.circle(center=(pos, 12), r=5.75, stroke='white', stroke_width=0.5, fill='black', stroke_dasharray='1.004,1.003'))
        else:
            dwg.add(dwg.circle(center=(pos, 12), r=5.75, stroke='white', stroke_width=0.5, fill='black'))
        dwg.add(dwg.circle(center=(pos, 12), r=5, fill=color))
    # 判断是否是连音符
    tuplet = tuplet_judge(float(Fraction(adjusted_value.rstrip('!').rstrip('.'))))
    if value.rstrip('!') != '-' and tuplet != 1:
        dwg.add(dwg.text(str(tuplet), insert=(pos, 14.4), text_anchor='middle', fill='white', font_size='6.4px', font_family='Edwin', font_weight='bold', font_style='italic'))

# 标注音符时值，使用Exo字体，白底黑字并根据条件设置不同的粗细和颜色
previous_note_value = note_values_str[0]  # 初始化前一个音符的时值用于判断
if version:
    note_values_str = adjusted_note_values
for pos, value, adjusted_value in zip(note_positions, note_values_str, adjusted_note_values):
    font_weight = '500'
    fill_color = 'black'
    font_size = '5.7px'
    y_position = 30.05
    display_value = value.rstrip('!')
    font_style = 'normal'
    # 附点音符标红
    if value.rstrip('!').endswith('.'):
        font_weight = '600'
        fill_color = '#dd1313'
        display_value = value.rstrip('!')
    # 如果是毫秒采音，保留三位有效数字，并使用灰色字体
    if '.' in value and value.rstrip('!').endswith('.') == False:
        if float(value) < 9.995:
            display_value = f"{float(value):.2f}"
        else:
            display_value = f"{float(value):.1f}"
        if float(value) < 1.4 or float(value) > 15:
            font_size = '5.4px'
            y_position = 29.98
        if float(value) > 18:
            font_size = '4.8px'
            y_position = 29.85
        if (18.7 <= float(value) <= 18.9) or float(value) > 20:
            font_size = '4.2px'
            y_position = 29.72
        if float(value) < 1:
            display_value = f"4/{4/float(value):.2f}"
        fill_color = '#7f7f7f'
    # 标记的软音符使用斜体
    if value.endswith('!'):
        font_style='italic'
    # 时值比 24 分更快时缩小字体为0.8x
    if value.rstrip('!') != '-' and Fraction(adjusted_value.rstrip('.').rstrip('!')) >= 25 and adjusted_value != '32.':
        font_size = '4.8px'
        y_position = 29.85
    # 附点32 分特别缩小字体为0.9x
    if value.rstrip('!') == '32.' or value.rstrip('!') == '28.':
        font_size = '5.4px'
        y_position = 29.98
    # 判断分数，使用灰色字体
    if '/' in value:
        numerator, denominator = map(int, value.rstrip('!').rstrip('.').split('/'))
        fill_color = '#7f7f7f'
        # 当前一个音符的时值快于 16 分时，分子大于 16 或分子分母同时为两位数时在开头添加空格
        if float(Fraction(previous_note_value.rstrip('.').rstrip('!'))) >= 17:
            if numerator >= 17 or (numerator >= 10 and denominator >= 10):
                display_value = '\u3000' + value.rstrip('!')  # 使用全角空格
        # 分子大于 32 且前一个音符的时值快于 32 分时在开头添加两个空格
        if numerator >= 33 and float(Fraction(previous_note_value.rstrip('.').rstrip('!'))) >= 33:
            display_value = '\u3000\u3000' + value.rstrip('!')  # 使用全角空格
        # 分子大于 24 时，若分子大于等于 56 或前一个音符的时值快于 16 分时缩小字体
        if numerator >= 25:
            if numerator >= 56 or float(Fraction(previous_note_value.rstrip('.').rstrip('!'))) >= 17:
                font_size = '4.8px'
                y_position = 29.85
    # 连音符设置
    if value.rstrip('!') != '-':
        tuplet = tuplet_judge(float(Fraction(value.rstrip('!').rstrip('.'))))
        if tuplet != 1:
            font_weight = '600'
            fill_color = '#7f7f7f'
        if tuplet == 3:
            fill_color = '#2020ff'
        if tuplet == 5:
            fill_color = '#8F2874'
        if tuplet == 7:
            fill_color = '#7C3ED3'
        if tuplet == 9:
            fill_color = '#396E72'

    # 更新前一个音符的时值
    previous_note_value = value

    dwg.add(dwg.text(display_value, insert=(pos, y_position), text_anchor='middle', fill=fill_color, font_family='Exo', font_size=font_size, font_weight=font_weight, font_style=font_style))

# 保存SVG文件
dwg.save()
print(f"SVG：{svg_file_path}")
