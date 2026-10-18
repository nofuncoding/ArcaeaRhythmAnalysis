import argparse
import bisect
import os
import re

from arcaea_config import load_config
from arcaea_rhythm.selection import SelectionError, resolve_selection

parser = argparse.ArgumentParser(description='清理 Arcaea 谱面中的连蛇/碎蛇')
parser.add_argument('--config', help='配置文件路径（默认 config.toml 或 config.txt）')
parser.add_argument('--folder', help='谱面文件夹名（覆盖配置/交互选择）')
parser.add_argument('--chart', type=int, choices=(2, 3, 4), help='难度（覆盖配置/交互选择）')
parser.add_argument('--force', action='store_true', help='强制重新生成 1.aff/0.aff')
parser.add_argument('--refresh-timing', action='store_true',
                    help='重新提取 timing_{chart}.txt（会覆盖手动修改）')
args = parser.parse_args()

try:
    cfg = load_config(args.config)
    folder_name, chart = resolve_selection(cfg, args.folder, args.chart)
    cfg.folder, cfg.chart = folder_name, chart
    cfg.__post_init__()
except (OSError, ValueError, SelectionError) as exc:
    raise SystemExit(str(exc)) from exc

folder = str(cfg.chart_dir)
chart = cfg.chart

# 确定aff文件路径
input_file = f"{chart}.aff"
output_file = cfg.aff_name

input_aff_path = os.path.join(folder, input_file)
output_aff_path = os.path.join(folder, output_file)
timing_file_path = str(cfg.timing_file)

# 检查是否已经存在处理后的谱面文件
generate_chart = args.force or not os.path.exists(output_aff_path)
if not generate_chart:
    print(f"{output_file} 和 timing_{chart}.txt 已存在，跳过（--force 可重新生成）。")

# 执行谱面处理
if generate_chart:
    # 定义arc语句的正则表达式模式
    arc_pattern = re.compile(r"arc\((\d+),(\d+),.*?,.*?,.*?,.*?,.*?,(\d),.*?,(true|false)\);")

    with open(input_aff_path, 'r') as aff_file:
        lines = aff_file.readlines()

    arc_lines = []  # [start, end, color, trace, line, source_index]
    line_items = []  # [(source_index, line)]
    timing_lines = []  # 存储timing语句
    modified_count = 0  # 计数器
    inside_timing_group = False  # 标记是否在timinggroup内部

    # 逐行处理输入文件
    for source_index, line in enumerate(lines):
        line = line.strip(' ')

        # 处理timinggroup
        if line.startswith('timinggroup('):
            inside_timing_group = True
        elif line.startswith('}') and inside_timing_group:
            inside_timing_group = False
        elif line.startswith('timing(') and not inside_timing_group:
            timing_lines.append(line)

        # 使用正则表达式匹配arc语句
        arc_match = arc_pattern.search(line)
        if arc_match:
            start_time, end_time, color, trace = arc_match.groups()
            start_time, end_time, color = int(start_time), int(end_time), int(color)
            trace = trace == 'true'

            arc_lines.append([start_time, end_time, color, trace, line, source_index])
        else:
            line_items.append((source_index, line))

    # 检查需要改成黑线的arc
    # 按颜色建立 start/end 索引，用二分查找替代 O(n²) 全量扫描
    tails_by_color = {}
    for other_start, other_end, other_color, other_trace, _, _ in arc_lines:
        if not other_trace and other_start != other_end:
            tails_by_color.setdefault(other_color, []).append((other_start, other_end))

    ends_by_color = {
        color_key: sorted(end for _, end in tails)
        for color_key, tails in tails_by_color.items()
    }
    starts_by_color = {
        color_key: sorted(start for start, _ in tails)
        for color_key, tails in tails_by_color.items()
    }

    for start_time, end_time, color, trace, line, source_index in arc_lines:
        if trace:
            line_items.append((source_index, line))
            continue

        # 连着的蛇后续段落改为黑线：存在 end ∈ [start-3, start+3]
        ends = ends_by_color.get(color, [])
        idx = bisect.bisect_left(ends, start_time - 3)
        connected = idx < len(ends) and ends[idx] <= start_time + 3

        # 同色碎蛇后续段落改为黑线（阈值100ms）：存在 start ∈ [start-100, start-4]
        starts = starts_by_color.get(color, [])
        idx = bisect.bisect_left(starts, start_time - 100)
        broken = idx < len(starts) and starts[idx] <= start_time - 4

        if connected or broken:
            line_items.append((source_index, line.replace('false', 'true')))
            modified_count += 1  # 增加计数器
        else:
            line_items.append((source_index, line))

    # 保存 timing 语句；默认保留已有文件，避免覆盖手工修正的 timing
    refresh_timing = args.refresh_timing or not os.path.exists(timing_file_path)
    if refresh_timing:
        if os.path.exists(timing_file_path):
            print(f"注意：将覆盖 {os.path.basename(timing_file_path)}，其中手动修改的 timing 会丢失。")
        with open(timing_file_path, 'w') as timing_file:
            timing_file.writelines(timing_lines)
    else:
        print(f"保留已有 {os.path.basename(timing_file_path)}（--refresh-timing 可重新提取）。")

    # 保存处理后的内容到输出aff文件；按源文件顺序过滤 noinput 段
    line_items.sort(key=lambda item: item[0])
    inside_noinput = False
    aff_lines = []
    for _, line in line_items:
        if line.startswith('timinggroup(noinput'):
            inside_noinput = True
        elif line.startswith('}') and inside_noinput:
            inside_noinput = False
        elif not inside_noinput:
            aff_lines.append(line)
    with open(output_aff_path, 'w') as aff_file:
        aff_file.writelines(aff_lines)

    # 输出总共修改的行数
    count = 0
    for line in lines:
        count += line.count('false')
    print(f"Total arc lines with trace false: {count}")
    print(f"Total lines modified to true: {modified_count}")
