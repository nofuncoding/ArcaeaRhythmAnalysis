import os
import re
import keyboard

# 读取配置文件
config_file_path = os.path.join(os.path.dirname(__file__), 'config.txt')
with open(config_file_path, 'r', encoding='utf-8') as config_file:
    config_lines = config_file.readlines()
for line in config_lines:
    if line.startswith('folder='):
        folder = os.path.join(os.path.dirname(__file__), 'charts', f'{line.strip().split('=')[1].strip()}')
    if line.startswith('chart='):
        chart = int(line.strip().split('=')[1].strip())

# 确定aff文件路径
input_file = f"{chart}.aff"
if chart == 3 or chart == 4:
    output_file = '1.aff'
elif chart == 2:
    output_file = '0.aff'
else:
    raise ValueError("Invalid chart value. Chart must be 2, 3, or 4.")

input_aff_path = os.path.join(folder, input_file)
output_aff_path = os.path.join(folder, output_file)
timing_file_path = os.path.join(folder, f'timing_{chart}.txt')

# 检查是否已经存在处理后的谱面文件
generate_chart = True
if os.path.exists(output_aff_path):
    print("timing.txt 和", output_file, "已经存在。")
    print("按回车重新生成，按空格跳过。")
    while True:
        if keyboard.is_pressed('enter'):
            break
        if keyboard.is_pressed('space'):
            generate_chart = False
            break

# 执行谱面处理
if generate_chart:
    # 定义arc语句的正则表达式模式
    arc_pattern = re.compile(r"arc\((\d+),(\d+),.*?,.*?,.*?,.*?,.*?,(\d),.*?,(true|false)\);")

    with open(input_aff_path, 'r') as aff_file:
        lines = aff_file.readlines()

    arc_lines = []  # 存储匹配到的arc语句
    timing_lines = []  # 存储timing语句
    processed_lines = []  # 存储处理后的行
    modified_count = 0  # 计数器
    inside_timing_group = False  # 标记是否在timinggroup内部

    # 逐行处理输入文件
    for line in lines:
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

            arc_lines.append([start_time, end_time, color, trace, line])  # 存储匹配结果
        else:
            processed_lines.append(line)

    # 检查需要改成黑线的arc
    for start_time, end_time, color, trace, line in arc_lines:
        if trace:
            processed_lines.append(line)
        else:
            duration = end_time - start_time
            # 连着的蛇后续段落改为黑线
            modify_trace = any(
                abs(other_end_time - start_time) <= 3 and other_color == color
                for other_start_time, other_end_time, other_color, other_trace, _ in arc_lines if not other_trace and other_start_time != other_end_time
            ) or (
             # 同色碎蛇后续段落改为黑线（阈值100ms）
                any(
                    4 <= (start_time - other_start_time) <= 100 and other_color == color
                    for other_start_time, other_end_time, other_color, other_trace, _ in arc_lines if not other_trace and other_start_time != other_end_time
                )
            )
            if modify_trace:
                new_line = line.replace('false', 'true')
                processed_lines.append(new_line)
                modified_count += 1  # 增加计数器
            else:
                processed_lines.append(line)

    # 保存timing语句到timing文件
    with open(timing_file_path, 'w') as timing_file:
        timing_file.writelines(timing_lines)

    # 保存处理后的内容到输出aff文件
    input = True
    aff_lines = []
    for line in processed_lines:
        if line.startswith('timinggroup(noinput'):
            input = False
        elif line.startswith('}') and input == False:
            input = True
        elif input:
            aff_lines.append(line)
    with open(output_aff_path, 'w') as aff_file:
        aff_file.writelines(aff_lines)

    # 输出总共修改的行数
    count = 0
    for line in lines:
        count += line.count('false')
    print(f"Total arc lines with trace false: {count}")
    print(f"Total lines modified to true: {modified_count}")
