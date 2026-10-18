# extradimensional 数据对比与修复记录

对比对象：

- **当前 docs/ 中的 Kikai 原版失败输出**：`timing_3.txt`、`timing_3_edited.txt`、`rhythm_3_after_edited.txt`
- **历史对照**：对比时 `docs/` 中曾有 extradimensional 原版工具输出（`rhythm_4.txt` / `timing_4.txt`，后来被 Kikai 输出替换）；对比结论保留在下方
- **旧谱面 reference**：`charts/extradimensional/`（更早的 rhythm/timing/SVG/预览）
- **新谱面数据**：`charts/extradimensional_chart/4.aff` + `base.ogg`

## 结论摘要

1. **发现并修复了 noinput 段过滤的顺序 bug。**
   - 旧 `1.py` 先收集所有 arc，再把 arc 行追加到输出末尾，导致 noinput 过滤器看不到 arc 所属的 timinggroup。
   - 结果：noinput 段里的 arc 仍然进入 `1.aff`、`rhythm_*.txt`，甚至影响 SVG/预览长度。
   - 新实现保留源文件行号，按原顺序处理 arc 与 noinput，`timinggroup(noinput...)` 内的 arc 现在会被正确移除。

2. **extradimensional 的 258 秒隐藏 arc 已消失。**
   - 新谱面的 `timinggroup(noinput)` 里包含 `arc(258308,...)`，而 base 音频只有 159.49 秒。
   - 修复前 `rhythm_4.txt` 末尾出现 `2/195`，SVG 宽度被拉到 73224px，预览会滚动到 258 秒以后。
   - 修复后这些 arc 不再进入 1.aff；末尾恢复为 `-`，SVG 宽度 57600px，预览结束时间 168.308 秒。

3. **预览结束时间不再被 210/360 秒的旧常量强行拉长。**
   - 现在取 `max(最后一个有效音符 + 10s, base 音频时长 + 1s)`。
   - extradimensional：168.308 秒（base 159.49 秒）。
   - KikaiNoTsubasa：约 511 秒（noinput 修复后，203-211/695 秒附近的效果 arc 不再计入；base 510 秒）。

4. **KikaiNoTsubasa 也受 noinput 修复影响。**
   - `rhythm_3.txt` 从 2774 条变为 2674 条，减少的 100 条来自原 `1.aff` 中错误保留的 noinput arc。
   - `1.aff` 的行顺序恢复为源谱面顺序；arc 内容与修改数量不变。
   - 音频中对应 noinput 段的多余 arc 按键音也被移除。

## KikaiNoTsubasa 原版失败复现与修复

原版 1.py 会从 Kikai 的 3.aff 中提取全部顶层 timing，其中包括：

- `timing(...,0.00,...)`：BPM 0；
- `timing(...,-19800.00,...)`：负 BPM；
- `timing(...,9999999.00,...)`：特效 BPM；
- `timing(0,200.00,999.00);` / `beats_per_measure=1024`：特效拍号。

### 2.py 的 ZeroDivisionError

原版 2.py 对每个 timing 直接计算：

```python
beat_duration = 60000 / bpm
```

遇到 BPM 0 时崩溃。当前 2.py 在进入计算前过滤：

```text
BPM <= 0 或 BPM > max_bpm（默认 1000）的 timing 直接跳过
负 BPM 行本身不匹配 2.py 的正数正则
```

用 `docs/timing_3.txt`（原版未编辑 timing）验证：

```text
忽略 263 个特效 timing。
rhythm_3.txt：2674 个节奏值
```

不再出现除零错误，而且 2674 与手动整理 timing 后的 Kikai rhythm 完全一致，说明过滤没有改变正常节奏。

### 3.py 的负坐标 TypeError

原版 3.py 用第一个 timing 的拍号初始化拍线：

```python
current_beat = 16 - 8 * timing_info[0][2]
```

当 `beats_per_measure=999` 时得到约 `-7976`，后续绘制出 `x1=-382848`，被 svgwrite 的 tiny profile 拒绝。

当前 3.py 做了三处修复：

1. 过滤 BPM<=0、BPM>max_bpm（默认 1000）、拍号不在 1..64 的特效 timing；
2. `current_beat = max(0, 16 - 8 * timing_info[0][2])`，不再产生负拍线；
3. 兼容 3 字段 timing 行（`timing(ms,bpm,beats);` 自动补 `note_value_per_beat=4`）。

验证结果：

```text
docs/timing_3.txt（4 字段，含 BPM 0）:
  忽略 415 个特效 timing
  Total Beats: 1609.75
  负坐标数量: 0

docs/timing_3_edited.txt（3 字段）:
  忽略 88 个特效 timing
  Total Beats: 1683.5
  负坐标数量: 0
```

### 仍未自动修复的部分

- **特效 timing 不是真实歌曲 timing**：过滤只能避免崩溃和负坐标，不能还原人工整理后的精确 BPM 序列。
- 对 Kikai 这种包含大量变速/暂停/timing 特效的谱面，仍建议按 README 手动检查 `timing_{chart}.txt`，或者使用 `docs/timing_3_edited.txt` 这类已整理数据。
- 默认 `max_bpm=1000`，会自动忽略 9999999 等特效 BPM；设为 0 可关闭过滤，`--ignore-effect-bpm` 为兼容项。
- 当前拍号过滤阈值是 1..64；超过范围的特殊写法需要再调整阈值。

## 预览 BPM 变化时的音画偏移修复

KikaiNoTsubasa 的 `timing_3.txt` 有大量 BPM 变化，而且 `AudioOffset=200`；extradimensional 的 offset 为 0，所以问题在 Kikai 更明显。

旧预览 JS 有三个问题：

1. 对所有 timing 先减 `offset`，再只给 `i > 0` 的 timing 加固定 lead-in，导致第一个 timing 变成负数，BPM 变化边界与音频时间不一致；
2. 滚动距离使用：

   ```js
   scrollDistance += (duration * bpm - previousBpm) * 0.8
   ```

   `previousBpm` 是 BPM 数值，不是距离，BPM 每次变化都会造成一次跳变；
3. 每段 CSS transition 使用 `duration + 1s`，但 `setTimeout` 按真实段长推进，段与段之间会累积漂移。

现在的实现：

- 时间轴边界统一为 `leadIn + (chartTimestamp + offset) / 1000`；
- 每段距离严格为 `时长 × BPM × 0.8`；
- 使用 `requestAnimationFrame` 按真实时间计算位置，不再依赖递归 `setTimeout` 和 transition 链；
- 音频在 `leadIn` 时启动，滚动从点击时刻开始。

Kikai 验证：

```text
offset = 200ms
leadIn = 4.455s
第一个 BPM 变化: 4.455 + (10800 + 200)/1000 = 15.455s
音频中该变化: 10.8s + 0.2s + 4.455s = 15.455s
```

extradimensional：

```text
offset = 0ms
leadIn = 3.808s
第一个 BPM 变化: 3.808 + 71.538 = 75.346s
```

## BPM 变化后小节线错位修复

除了预览滚动，3.py 还有三处会让 Kikai 的小节线在 BPM 变化后错位：

1. **拍线错误地叠加了 AudioOffset**

   旧代码：

   ```python
   last_timestamp = -offset
   ```

   Kikai 的 `offset=200`，导致所有 timing 拍数偏移 `200ms × BPM`，第一个 BPM 变化偏移约 0.667 拍；extradimensional 的 offset=0，所以看不出来。

   现在拍线只使用谱面时间：

   ```python
   last_timestamp = 0
   ```

2. **0ms timing 被特效拍号过滤后没有锚点**

   旧 timing 第一行是 `timing(0,200,999)`，拍号 999 被过滤，第一个有效 timing 变成 `timing(10800,100,2)`，于是开头 11 秒被错误地按 BPM 100 计算。

   现在补一个 0ms 锚点：

   ```text
   Timing 0: 36(16), 200, 4
   Timing 1: 24(52), 100, 2
   ```

   BPM 变化落在第 52 拍，正好是小节线位置。

3. **浮点取模与累计四舍五入**

   旧代码：

   ```python
   (current_beat - last_beat) % last_beats_per_measure
   ```

   当差值是 `23.99999999999999` 时会被误判为未对齐；同时每个 timing 的 `delta_beats` 都先 `round(..., 2)`，大量 BPM 变化会累积误差。

   现在用整数小节判断：

   ```python
   measure_aligned(delta_beats, beats_per_measure)
   ```

   并且累计拍数保留完整精度，只在显示时取整。

验证：

```text
Filtered Timing: 16, 200, 4
Filtered Timing: 52, 100, 2
Filtered Timing: 76, 150, 3
Filtered Timing: 82, 200, 4
Filtered Timing: 410, 200, 4
```

小节线 x 坐标对应：

```text
beat 52  -> x = 2496
beat 76  -> x = 3648
beat 82  -> x = 3936
beat 410 -> x = 19680
```

这些位置现在都能在 SVG 中精确找到。

## 历史对照：extradimensional 原版工具输出

### timing

- `docs/timing_4.txt` 与当前 `charts/extradimensional_chart/timing_4.txt` **完全相同**。
- 说明 1.py 的 timing 提取、2.py 的 timing 字段更新都没有引入差异。

### rhythm

- `docs/rhythm_4.txt`：994 项。
- 当前修复后：993 项。
- 用 `difflib.SequenceMatcher` 对比，唯一差异是删除索引 992 的 `2/195`：

```text
docs:   [..., "16", "16", "2/195", "-"]
current:[..., "16", "16", "-"]
```

- `2/195` 正是 noinput 段 `arc(258308,...)` 造成的超长间隔；原版工具把它泄漏进了 rhythm，修复后正确移除。
- **其余 992 项完全一致**，说明本次修复没有改变正常音符的节奏结果。

### SVG / 预览

- 原版工具因为 258308 的隐藏 arc，SVG 宽度会扩到 73224px，预览结束时间会到 268 秒左右。
- 修复后 SVG 宽度 57600px，最后音符 x=54112px，预览结束时间 168.308 秒。

## 与旧 charts/extradimensional reference 的差异

### timing

- 旧 `charts/extradimensional/timing_4.txt`：60 条人工整理的 timing。
- 新谱面：49 条，包含 `9999999` / `58.50` 等特效 timing。
- 旧 reference 针对的是更早的谱面版本/人工 timing，与新谱面不是同一份 timing 数据。

### rhythm

- 旧 `charts/extradimensional/rhythm_4.txt`：989 项。
- 新谱面修复后：993 项。
- 前 **271 项完全一致**；从索引 271（约 48.2 秒）开始不同。
- 原因：新谱面在 `arc(48204,48289,...,true)` 之后多了一段 `arc(48289,48353,...,false)`，旧 reference 对应的位置没有产生这条 12 分音符。由于 `docs/` 的原版工具输出与当前结果在此处一致，这属于新旧谱面版本差异，不是本次 1.py/2.py 修复造成的回归。

### SVG

| 项目 | 旧 reference | 新谱面（修复后） |
|---|---:|---:|
| 宽度 | 32640 px（longchart=0） | 57600 px（longchart=1） |
| 最后音符 x | 28559.85 px | 54112.25 px |
| 是否截断 | 否 | 否（x < 宽度） |

> 若把新谱面配置改成 `longchart=0`，3.py 的动态扩展会把画布加宽到最后音符之后，不会截断。

### 音频

- 旧 reference：`note_4.wav`，实际是 MP3，159.49 秒。
- 新谱面：`note_4.flac`，159.49 秒。
- 混音事件数会因 noinput 过滤而变化；Kikai 的按键音事件数减少。

## 验证

- `python -m unittest discover -s tests -q`：30 个测试通过。
- 历史对照（extradim 原版工具输出）：timing 哈希一致；rhythm 与当前只差删除 `2/195`（noinput 隐藏音符）。
- extradimensional：`1.aff` 中不再包含 258308；`rhythm_4.txt` 末尾为 `-`；预览 `nextTimestamp = 168308`。
- Kikai：用 `docs/timing_3.txt` 复现原版失败后，当前 2.py/3.py/4.py 均可继续；`rhythm_3.txt` 2674 项；3.py 负坐标 0。
- Kikai：用 `docs/timing_3_edited.txt`（3 字段）验证 3.py 兼容，负坐标 0。
- 1.py 弧线优化后的输出在无 noinput 段时仍保持内容一致。

## 仍待确认

- `charts/extradimensional/` 是更早谱面版本的 reference，不能作为新谱面的逐项基准；当时 `docs/` 中的 extradim 原版工具输出已作为历史对照。
- `scenecontrol(...,hidegroup,...)` 的普通 timinggroup 是否也应完全忽略；目前只严格处理 `timinggroup(noinput...)`。
