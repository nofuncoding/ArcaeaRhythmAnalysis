# ArcaeaRhythmAnalysis 升级分析与实施计划

> 状态：**Phase 1–3 完成；Phase 4 主要项完成；Phase 5 测试/CI 完成**
> 基线环境：Python 3.14.8（`.venv`），项目当前可运行
> 实测样本：`charts/KikaiNoTsubasa/3.aff`（3285 个按键音事件，base 音频 510 秒）

---

## 0. 已实施进展

- `4.py` 已用 **soundfile + NumPy** 替换 pydub：一次解码、采样级叠加、分块写出。
- 实测 510 秒 / 3285 事件：混音约 **0.16 秒**，完整 FLAC 输出约 **10.2 秒**（旧版外推约 44 分钟）。
- 新增 `--force`、`--no-audio`、`--no-open`、`--audio-format`；移除 `keyboard` 轮询。
- `config.txt` 新增 `audio_format`（默认 `flac`，可选 `wav` / `ogg` / `mp3`）。
- `1.py` 也用 `--force` 替代键盘轮询；默认保留已有 `timing_{chart}.txt`，只有 `--refresh-timing` 才重新提取，避免覆盖手工修正。
- `1.py` 弧线判定改为按颜色二分索引：`2.97 s → 0.33 s`，`1.aff` 与原实现逐字节一致。
- `2.py` 改用单调 timing 指针并移除无用的 `Fraction.limit_denominator()`：`2.49 s → 1.36 s`，timing/rhythm 输出一致。
- `3.py` 用 `json.loads` 替换 `eval`，小节线集合查找；SVG 输出逐字节一致。
- 新增 `run.py` 一键运行四个阶段，支持 `--stage`、`--from`、`--force`、`--no-audio`、`--no-open`、`--audio-format`。
- `run.py` 在 1.py/2.py/3.py 之后用 **Y/n** 确认手动修改是否完成；输入 `n` 暂停并提示 `--from rhythm|svg|audio` 继续；`-y/--yes` 可跳过（非 TTY 自动继续）。
- 完整强制流水线（含 FLAC 输出）实测约 **11.4 秒**。
- 新增 [arcaea_config.py](arcaea_config.py) 统一配置加载：支持 `config.toml`、旧 `config.txt`，四个脚本和 `run.py` 均支持 `--config`。
- 新增 [config.example.toml](config.example.toml)；查找顺序为 `--config` > `config.toml` > `config.txt`。
- 新增 [arcaea_cache.py](arcaea_cache.py) 阶段缓存：输入哈希 + 配置指纹，命中时跳过 rhythm/svg/audio/preview；完整重复运行约 **0.32 秒**。
- `run.py` 新增 `--no-cache`；`--force` 忽略缓存；手动修改 rhythm 会自动触发 SVG 重建。
- 新增 `arcaea_rhythm` 包和 [pyproject.toml](pyproject.toml)：`arcaea-rhythm build/list/doctor/migrate-config`，入口点已可通过 `pip install -e .` 安装。
- 新增 [arcaea_rhythm/selection.py](arcaea_rhythm/selection.py)：自动扫描 `charts/` 与可用难度，交互选择；`--folder/--chart` 可直接指定。
- `folder/difficulty` 已从 `config.txt`/示例 TOML 中移除，旧配置中的字段仍作为默认值兼容。
- `build` 通过环境变量把选择结果同步给四个阶段脚本。
- `4.py` 统一 offset 语义：音符时间 = 谱面时间 + `AudioOffset` + 手动 `offset`；HTML 使用同一个总 offset。
- 长音频结束位置：SVG 按最后音符自动延长，HTML 同时覆盖最后音符和 base 音频时长。
- 预览页：timing 改为 JSON 注入、点击开始遮罩、音频加载失败降级、1280×720 视口自适应、CSS 变量定位五边形、HTML/SVG @font-face。
- 修复 `1.py` 的 noinput 过滤顺序 bug：arc 按源文件顺序输出，noinput 段不再泄漏到 `1.aff`/rhythm/SVG；Kikai 的 100 条 effect arc 与 extradimensional 的 258 秒隐藏 arc 已移除。
- 新增 [arcaea_rhythm/timing.py](arcaea_rhythm/timing.py)：过滤 BPM<=0 与 999/1024 特效拍号；2.py 不再 ZeroDivision，3.py 不再产生负坐标。
- 新增 `max_bpm` 配置与 `--max-bpm` / `--ignore-effect-bpm` / `--keep-effect-bpm` 选项；默认 `1000`，自动过滤 9999999 等特效 BPM，`--keep-effect-bpm` 或 `max_bpm=0` 可关闭。
- 3.py 兼容 3 字段 timing 行，拍线起点钳制到 0；用 docs 的原版 Kikai timing 验证通过（0 个负坐标）。
- 3.py 修复 BPM 变化后小节线错位：0ms timing 锚点、拍线不叠加 AudioOffset、累计拍数不提前 round、浮点小节对齐判断。
- 预览结束时间不再强制 210/360 秒，改为 `max(最后音符 + 10s, base 音频时长 + 1s)`。
- 预览滚动改为 `requestAnimationFrame` + 音频时间轴边界；修正 BPM 变化时 `-previousBpm` 与固定 `+1000ms` 造成的音画偏移。
- 新增 [docs/extradimensional-validation.md](docs/extradimensional-validation.md) 对比记录：原版工具 timing 与当前完全一致，rhythm 仅删除 noinput 泄漏产生的 `2/195`；视频导出设计已放入 [TODO.md](TODO.md)。
- 新增 [arcaea_rhythm/audio.py](arcaea_rhythm/audio.py)，混音辅助函数可独立测试。
- 新增 [tests/test_audio.py](tests/test_audio.py)、[tests/test_cli.py](tests/test_cli.py)、[tests/test_selection.py](tests/test_selection.py)，测试共 30 个。
- 新增 [.github/workflows/ci.yml](.github/workflows/ci.yml)；pyproject 增加 dev extras（pytest/ruff/mypy）与工具配置。
- `1.py`~`4.py` 继续作为低层阶段入口/兼容入口；推荐使用 `arcaea-rhythm build`。
- 新增 [requirements.txt](requirements.txt)；移除 `pydub`、`audioop-lts`、`keyboard`。
- 已用 pydub 前 10 秒参考输出对比：峰值/RMS 一致，平均采样误差约 `7.7e-6`；最大差异仅出现在饱和裁剪点（新版为最后一次裁剪，旧版为每次 overlay 饱和）。

---

## 1. 结论摘要

1. **最大瓶颈不是谱面解析，而是 `4.py` 的 pydub 逐音符 overlay。**
   - 实测 510 秒音频上单次 overlay 约 **801.8 ms**；
   - 3285 个音符外推约 **44 分钟**，与 README 中“按键音生成较慢，需要等待”一致；
   - 改为 soundfile + NumPy 后，混音本体约 **0.16 秒**，完整生成 FLAC 约 **10 秒**。
2. **`sonance` 不能作为本项目的 pydub 替代品。**
   - 当前 PyPI 的 `sonance 0.1.0` 只有 PCM 基础操作，**没有 `from_file`、`export`、`overlay`**，无法直接替换本项目用到的 API。
3. **本项目不需要 librosa。**
   - 现有流程没有做音频分析/onset 检测，只是把谱面时间映射到音频采样点并叠加采样；
   - `librosa` 会引入 numba/scipy/scikit-learn 等重依赖，启动和安装成本高；
   - 正确的替代是 **soundfile（解码/编码）+ NumPy（混音）+ soxr（必要时重采样）**。
4. **Python 3.14 生态已就绪。**
   - `.venv` 已是 Python 3.14.8；
   - numpy 2.5.4、soundfile 0.14.0、soxr 1.1.0 均有 cp314 或通用 wheel；
   - 应移除 `pydub`、`audioop-lts`、`keyboard`。
5. **易用性问题的根因是四个脚本各自解析配置、依赖键盘轮询、没有统一 CLI。**
   - 建议改为一个 Python 包 + 一个命令，保留 `1.py`~`4.py` 兼容入口；
   - 用 `--force / --skip-existing` 替代“按回车/空格”，支持批量、缓存和阶段选择。

---

## 2. 项目现状

### 2.1 四阶段流水线

| 阶段 | 文件 | 输入 | 输出 | 作用 |
|---|---|---|---|---|
| 1 | `1.py` | `{chart}.aff`、`config.txt` | `1.aff` / `0.aff`、`timing_{chart}.txt` | 将连蛇/碎蛇的 `trace=false` 改为黑线；提取顶层 timing；移除 noinput 段 |
| 2 | `2.py` | `1.aff`、`timing_{chart}.txt` | `rhythm_{chart}.txt`、更新 timing | 把音符时间差换算成拍数，量化成 4/8/12/16… 节奏数组 |
| 3 | `3.py` | timing、rhythm | `rhythm_{chart}.svg`、`default_{chart}.svg` | 绘制时间轴、小节线、拍线、音符形状与时值标注 |
| 4 | `4.py` | 1.aff、timing、base 音频、采样 | `note_{chart}.wav`、`index_{chart}.html` | 逐音符叠加按键音；生成播放预览并打开浏览器 |

### 2.2 数据格式

- timing 文件：`start=...`、`offset=...`、`timing(ms,bpm,beats_per_measure,note_value_per_beat);`
- rhythm 文件：JSON 风格数组，元素如 `"4."`、`"8/13"`、`"12"`、`"-"`，后缀 `!` 表示绿蛇标记
- aff：Arcaea 文本谱面，包含 `AudioOffset`、`timinggroup`、`timing`、tap/hold/arc/arctap

### 2.3 实测基线

| 项目 | 现状 | 说明 |
|---|---:|---|
| `1.py` 弧线判定（仅核心 O(n²) 循环） | **2.97 s** | 12617 条 arc，3122 条 false；对每条 false arc 扫描全部 arc 两遍 |
| `2.py` 节奏数组 | **2.49 s** | 该样本只有 1 个 timing；timing 数增多时是 O(音符数 × timing 数) |
| `3.py` SVG 生成 | **3.39 s** | 约 4800 个时间轴圆点 + 大量 SVG 元素；输出 1.3 MB |
| `4.py` 单次 overlay（510 s 音频） | **801.8 ms** | pydub 每次 overlay 都复制整段前缀/后缀 |
| `4.py` 3285 音符混音（外推） | **≈ 44 min** | 仅混音，不含解码和导出 |
| base.ogg 解码（soundfile） | **1.66 s** | 510 s / 44.1 kHz / 双声道 |
| NumPy 混音 5000 音符（510 s） | **0.116 s** | 约 23 µs/音符 |
| soundfile 写 510 s FLAC（分块） | **3.16 s** | 66.2 MB |
| soundfile 写 510 s WAV（分块） | **2.07 s** | 85.8 MB |
| soundfile 写 510 s OGG（分块） | **46.56 s** | 6.5 MB |
| soundfile 写 510 s MP3（分块） | **30.45 s** | 8.6 MB |
| ffmpeg 转 OGG / MP3（可选） | **17.3 s / 10.4 s** | 已安装 ffmpeg；仅作为可选加速路径 |

> 注：`soundfile.write()` 一次性写 510 s 大数组在本机触发过段错误；**分块写入（`SoundFile.write`）稳定**。实现时必须分块写，不能直接整段 `sf.write`。

---

## 3. 主要问题清单

### 3.1 性能

- `4.py`：pydub `overlay` 每次都会 `seg1[:position]` + `seg1[position:]` 复制整段音频，复杂度 O(音符数 × 音频长度)；510 s 音频上单次约 0.8 s。
- `1.py`：对每条 false arc 做两次全量 `any()` 扫描，O(n²)。
- `2.py`：每个音符从 timing 列表头重新扫描，O(n×m)；`processed_fraction` 还对每个分母重复构造 `Fraction`。
- `3.py`：`pos_beat not in measure_positions` 是列表线性查找；大量 svgwrite 对象创建；`shutil.copyfile` 复制 1.3 MB SVG。
- `3.py` / `4.py`：预览长度写死为 680/1200 拍（短/长谱面），长音频会截断。实测 KikaiNoTsubasa/3 最后音符 x=112000px，而 SVG 画布只有 57600px；`4.py` 的 `longtime=360000ms` 也会让动画在第 6 分钟提前结束。
- `4.py`：pydub 解码/导出依赖 ffmpeg 子进程；导出 MP3 默认 64 kbps，且文件名是 `.wav`。

### 3.2 正确性

- `4.py` 先读 config 的 `offset`，随后在解析 aff 时被 `offset = 0` 和 `AudioOffset` 覆盖，**config 的 offset 实际不生效**。
- `4.py` 把 MP3 数据写进 `note_{chart}.wav`，靠浏览器猜格式；部分播放器/工具会失败。
- `2.py` 对同一时间点的 tap 与绿 arc 排序后只保留第一个，可能丢失 `!` 标记；空谱面会 `IndexError`。
- `2.py` 的 `processed_fraction` 中 `Fraction(...).limit_denominator()` 结果未被使用，死代码。
- `3.py` 用 `eval()` 读 rhythm 文件；应改为 `json.loads`。
- `3.py` 用浮点相等判断小节线位置；`measure_positions` 中混有 int/float。
- `3.py` 的固定 `total_beats/total_length` 与 `4.py` 的固定 `longtime` 没有共享同一套“实际结束位置”计算，长音频必然在两侧同时截断。
- `4.py` 按 BPM 字符串去重（`"200.00"` 与 `"200"` 不相等）；`start` 解析后未使用。
- `1.py` 统计 `false` 时扫描所有行，不是只统计 arc。
- 多处 `folder is None` 检查发生在变量未定义时，配置缺失会直接 `NameError`。

### 3.3 易用性

- 必须依次运行 `1.py`~`4.py`，且 `1.py`/`4.py` 用 `keyboard` 轮询回车/空格。
  - `keyboard` 在 Linux 通常需要 root，在 Wayland 下不可靠，Windows/macOS 行为也不一致。
- 四个脚本各自重复解析 `config.txt`，没有默认值、校验和错误提示。
- 没有单命令、批量、缓存、阶段选择、静默/详细日志。
- 预览宽度依赖手调 `width`，右侧五边形位置写死 1224/1231.2/1238.4；README 让用户“调整 width 直到对齐”。
- HTML 用 f-string 拼接，timing 内容直接注入 JS 模板字符串；容易受反引号/特殊字符影响。
- 字体文件在 `fonts/`，但 HTML/SVG 没有 `@font-face`，实际可能回退字体。
- 没有测试、打包、类型检查、CI。

### 3.4 可维护性

- 全局变量、顶层脚本、魔法数字（680/1200 拍、32640/57600 px、768、14850、4*48*4-218/4）。
- `slow` 配置被读取但 `slowtime=1` 写死；`version` 逻辑与 rhythm 归一化耦合。
- `1.py` 使用内建名 `input` 作为变量；`3.py` 重复读取 speed。
- 无类型标注、无 docstring、无单元测试。

---

## 4. 技术选型

### 4.1 Python 3.14

- 项目 `.venv` 已是 3.14.8；`pyproject.toml` 设 `requires-python = ">=3.14"`。
- 使用标准库 `tomllib` 读 TOML、`pathlib` 统一路径、`dataclasses` + `slots` 建模。
- 不依赖 3.14 实验性 free-threading；普通 CPython 即可。

### 4.2 音频栈：soundfile + NumPy（+ soxr）

| 包 | 版本 | Python 3.14 | 用途 |
|---|---|---|---|
| numpy | >=2.5.4 | cp314 wheel | 采样级混音、增益、裁剪 |
| soundfile | >=0.14.0 | py2.py3 wheel，内置 libsndfile 1.2.2 | 解码 OGG/MP3/WAV/FLAC，写 WAV/FLAC/OGG/MP3 |
| soxr | >=1.1.0 | cp314 wheel | 采样率不一致时重采样 |
| svgwrite | >=1.4.3 | 纯 Python，已实测可运行 | 生成 SVG |
| tqdm | >=4.70 | 纯 Python | 进度条（可选） |

- **移除**：`pydub`、`audioop-lts`、`keyboard`。
- **不引入**：`librosa`、`numba`、`scipy`（除非后续做 onset 检测）。
- **sonance 结论**：0.1.0 的 wheel 中 `AudioSegment` 只有 PCM 基础方法，缺少 `from_file` / `export` / `overlay`，不能替换 `4.py`；不作为依赖。
- 若未来要做“自动 offset 对齐/onset 检测”，再增加可选 extra：
  ```toml
  [project.optional-dependencies]
  analysis = ["librosa>=1.0", "soxr>=1.1"]
  ```
  不让主流程承担 librosa 的安装体积和启动成本。

### 4.3 音频输出格式取舍

| 格式 | 510 s 体积 | soundfile 编码 | 浏览器支持 | 建议 |
|---|---:|---:|---|---|
| WAV | 85.8 MB | 2.1 s | 全部 | 兼容性优先 |
| FLAC | 66.2 MB | 3.2 s | 现代浏览器 | **本地预览推荐默认** |
| OGG | 6.5 MB | 46.6 s | 现代浏览器 | 分享/小体积可选 |
| MP3 | 8.6 MB | 30.5 s | 全部 | 兼容旧设备可选；不再伪装成 .wav |

- 默认建议 `flac`：无损、编码快、浏览器兼容性足够；
- 若更在意磁盘体积，选 `ogg`，代价是编码约 47 s；
- 若系统有 ffmpeg，可提供 `--ffmpeg-encode` 加速 OGG/MP3，但不作为必需依赖。

### 4.4 混音算法（替换 pydub）

```python
base, sr = sf.read(base_path, dtype="float32", always_2d=True)  # (frames, channels)
base *= volume                                                   # 等价于原 +20*log10(volume) dB
for start_ms in note_positions:
    i = round(start_ms * sr / 1000)
    n = min(len(tap), len(base) - i)
    if n > 0:
        base[i:i + n] += tap[:n]
np.clip(base, -1.0, 1.0, out=base)                               # 复刻 audioop.add 的饱和
with sf.SoundFile(out_path, "w", samplerate=sr, channels=base.shape[1],
                  format="FLAC") as f:
    for chunk in np.array_split(base, max(1, len(base) // 1_000_000)):
        f.write(chunk)                                           # 必须分块，避免大数组写入崩溃
```

要点：
- 采样率不一致时先用 `soxr.resample` 统一到 base 的采样率；
- 位置超出音频末尾的音符跳过（与原 pydub 行为一致）；
- 负位置裁剪到 0；
- 单声道/多声道统一到 base 的声道数；
- 混音复杂度 O(音符采样数)，与音频总长度基本无关。

---

## 5. 目标架构

```
ArcaeaRhythmAnalysis/
├── pyproject.toml
├── uv.lock / requirements.lock
├── src/arcaea_rhythm/
│   ├── __init__.py
│   ├── __main__.py          # python -m arcaea_rhythm
│   ├── cli.py               # build/list/doctor/migrate-config
│   ├── config.py            # Config dataclass，TOML + 旧 config.txt
│   ├── aff.py               # AFF 解析（timing/timinggroup/noinput/arc）
│   ├── models.py            # TimingPoint / Note / Chart
│   ├── timing.py            # 时间↔拍数、前缀和、量化
│   ├── pipeline.py          # 阶段编排、缓存、计时
│   ├── stages/
│   │   ├── arcs.py          # 原 1.py
│   │   ├── rhythm.py        # 原 2.py
│   │   ├── svg.py           # 原 3.py
│   │   ├── audio.py         # 原 4.py 混音
│   │   └── preview.py       # 原 4.py HTML
│   └── templates/preview.html
├── tests/
│   ├── fixtures/
│   ├── test_aff.py
│   ├── test_arcs.py
│   ├── test_rhythm.py
│   ├── test_audio.py
│   ├── test_svg.py
│   └── test_cli.py
├── charts/                  # 保持原位置
├── note_sounds/
├── fonts/
└── README.md
```

保留 `1.py`~`4.py` 作为薄包装（解析旧 config 后调用对应阶段），并在启动时打印弃用提示；旧用户无需改命令。

### 5.1 CLI 设计

```bash
# 一次跑完（读取 config.txt 或 config.toml）
arcaea-rhythm build

# 显式指定
arcaea-rhythm build --folder KikaiNoTsubasa --chart 3

# 只跑某阶段
arcaea-rhythm build --stage audio
arcaea-rhythm build --stage svg --force

# 批量
arcaea-rhythm build --all --jobs 2
arcaea-rhythm list
arcaea-rhythm doctor
arcaea-rhythm migrate-config
```

常用参数：
- `--force` / `--skip-existing`（替代键盘轮询）
- `--no-open`（默认打开预览，可关闭）
- `--audio-format flac|wav|ogg|mp3`
- `--root PATH`、`--config PATH`
- `--quiet` / `--verbose`（每个阶段耗时、输出文件、警告）
- `--dry-run`
- `--jobs N`（批量时限制并发，避免多个 170 MB 混音同时占内存）

### 5.2 配置

新增 `config.toml`（推荐），并继续兼容 `config.txt`：

```toml
# 谱面文件夹/难度在运行时选择，或使用 --folder/--chart
[chart]
speed = 1.0
version = 0
offset = 0              # 额外手动延迟（ms），与 aff 的 AudioOffset 分开
longchart = 1

[audio]
volume = 0.7
format = "flac"         # flac | wav | ogg | mp3
slow = 0

[preview]
width = 1280
```

优先级：CLI 参数 > `config.toml` > `config.txt` > 默认值。
`folder/chart` 不写入配置文件；运行时扫描 `charts/` 并交互选择，或通过 `--folder/--chart` 指定。
所有全局配置在启动时校验：volume ∈ [0,4]、width > 0、音频格式合法。

### 5.3 缓存

- 按“输入文件 mtime + size + 配置哈希”判断阶段是否可跳过；
- 默认跳过已是最新的输出，`--force` 全量重建；
- 缓存清单可放 `.arcaea-cache.json`（chart 目录）或 `build/.cache.json`；
- 不改变现有输出文件名，避免破坏用户在浏览器中的收藏/书签。

---

## 6. 分阶段实施计划

### Phase 0 — 基线与回归保护（0.5 天）

- 记录旧版 1.aff、timing、rhythm、SVG、音频的基准输出；
- 写一个无键盘的测试入口，能在 CI 中跑完四阶段；
- 固化基准数据：KikaiNoTsubasa/3 与 extradimensional/4；
- 建立 benchmark 脚本（音频混音、弧线扫描、SVG）。

**验收**：能在不上键盘、不打开浏览器的情况下复现旧输出。

### Phase 1 — 包化、配置、CLI（1 天）

- 建 `pyproject.toml`、`src/arcaea_rhythm`；
- 实现 `Config`、TOML/旧 txt 解析、参数校验；
- 实现 `build/list/doctor/migrate-config`；
- 用 `--force/--skip-existing` 替换 `keyboard`；
- `1.py`~`4.py` 改为兼容包装。

**验收**：`arcaea-rhythm build` 一条命令完成四阶段；无键盘依赖；错误信息可读。

### Phase 2 — 音频管线替换（0.5 天）

- soundfile 解码 base/tap/arc；
- NumPy 混音、音量、裁剪、分块写出；
- 可选 soxr 重采样；
- 修复 config offset 与 `AudioOffset` 的语义；
- 输出格式可配，默认 FLAC；HTML 使用新扩展名。

**验收**：3285 音符、510 s 音频完整生成 < 10 s（FLAC）；音符位置误差 ≤ 1 采样；无 pydub/ffmpeg 必需依赖。

### Phase 3 — 算法优化与正确性（1 天）

- `1.py`：按颜色建立排序的 start/end 索引，二分查找替代 O(n²)；输出逐字节回归；
- `2.py`：timing 前缀拍数 + `bisect`；O(n log m)；修正同时间点绿蛇标记合并、空谱面、最终 `-`；
- `3.py`：`json.loads` 替代 `eval`；小节线用集合/四舍五入键；去掉重复 speed 读取；
- `3.py` / `4.py`：引入统一的 `preview_end_ms = max(最后一个音符, base 音频时长, 旧版最小长度)`，由它同时计算 SVG 的 `total_length/total_beats` 和 HTML 的 `longtime`，避免两侧各自截断（当前脚本已做最小修复：Kikai/3 的 SVG 宽度从 57600px 扩展到 112392px，HTML 结束时间延长到 `longtime`）；
- 统一 offset 语义，timing 文件字段保持兼容；
- 增加缓存。

**验收**：`1.aff`、`rhythm_*.txt`、`timing_*.txt` 与旧版语义一致（有意修复项单独记录）；弧线扫描 < 0.1 s；节拍生成 < 1 s。

### Phase 4 — 预览与易用性（主要项已完成）

- HTML 模板化：timing 数据用 `json.dumps` 注入 `<script type="application/json">`；
- 点击开始遮罩 + `<audio>` 预加载，明确自动播放策略；
- 宽度自适应：五边形/六边形位置由 CSS 变量或 `width` 计算，不再写死 1224；
- `@font-face` 加载 `fonts/` 下的字体；
- 可选：用 Web Audio API 在浏览器实时调度 tap/arc 采样，彻底省去离线混音；
- 批量模式、`--jobs`、清晰的阶段进度与耗时汇总。

**验收**：改 `width` 不再需要手工对齐；预览一次点击即可播放；批量处理可用。

### Phase 5 — 测试、文档、打包（已完成）

- pytest：解析、弧线、节奏量化、音频采样位置、SVG 结构、CLI；
- 回归：旧版 vs 新版对比（音频比较时长/峰值/RMS/onset，不做字节比较）；
- README 重写：安装、快速开始、CLI、配置、故障排查、从四脚本迁移；
- ruff + mypy（可选）+ GitHub Actions（3.14，Linux/Windows/macOS）；
- 发布方式：`uv sync` / `pip install -e .`；提供 `arcaea-rhythm` 入口。

**总工期估计：约 3.5–4.5 个工作日**（不含可选的 Web Audio 播放模式）。

---

## 7. 性能目标

| 指标 | 现状 | 目标 |
|---|---:|---:|
| 510 s / 3285 音符音频混音 | ≈ 44 min | < 5 s（混音本体 < 0.5 s） |
| 完整 build（FLAC） | > 44 min | < 15 s |
| 完整 build（WAV） | > 44 min | < 10 s |
| 弧线判定 | 2.97 s | < 0.1 s |
| 节奏数组 | 2.49 s（单 timing） | < 1 s（多 timing 也不退化） |
| SVG 生成 | 3.39 s | < 1.5 s |
| 峰值内存 | 多次整段复制，峰值高 | < 1 GB（510 s 样本） |
| 用户操作 | 4 条命令 + 键盘确认 | 1 条命令 |

---

## 8. 兼容性与回归策略

- **保持输出文件名与格式**：`1.aff`/`0.aff`、`timing_*.txt`、`rhythm_*.txt`、`rhythm_*.svg`、`default_*.svg`、`index_*.html`。
- 音频扩展名会从 `.wav`（实际 MP3）改为真实格式；HTML 内引用同步更新。若用户依赖旧文件名，提供 `--legacy-audio-name`。
- `1.aff` 的“arc 行内容 + 顺序 + noinput 过滤”必须逐字节一致；缩进/换行风格在测试中固定。
- `rhythm_*.txt` 的字符串序列必须一致；允许实现内部用 Fraction/前缀和，但输出格式不变。
- SVG 不要求字节一致；用 XML 解析后比较元素数量、关键坐标、文本内容。
- 音频不要求字节一致；比较时长、采样率、声道、峰值、RMS、指定音符位置的能量。
- 所有“有意改变行为”的修复（config offset、绿蛇标记、空谱面、MP3 后缀）在 CHANGELOG 和迁移文档中列出。

---

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| soundfile 一次性写大数组段错误 | 实测确认；强制分块写（1M 帧/块），并加回归测试 |
| libsndfile 对 MP3/OGG 的支持随 wheel 变化 | 使用官方 0.14.0 wheel（内置 libsndfile 1.2.2）；启动时用 `sf.available_formats()` 检查并给清晰错误 |
| 浏览器不支持 FLAC/OGG | 提供 `--audio-format wav` 兜底；默认 FLAC，文档标注 |
| 输出与旧版有细微差异 | 先建 golden 回归，再改实现；量化/浮点处保留旧算法语义 |
| 批量并发导致内存峰值 | `--jobs` 默认 1；每个任务 170 MB 级，限制并发 |
| Windows 路径/编码/CRLF | 全程 `pathlib.Path`、UTF-8、`newline=""`；CI 覆盖 Windows |
| `svgwrite` 维护不活跃 | 当前可用；若成为瓶颈，改为轻量字符串构建器（Phase 3 可选） |
| 自动播放被浏览器拦截 | 点击遮罩启动 + `audio.play()` 的 Promise 错误提示 |
| 配置迁移破坏旧用户 | 旧 `config.txt` 永久兼容；`migrate-config` 只生成新文件，不删除旧文件 |

---

## 10. 待确认决策

1. **是否保留 `1.py`~`4.py` 兼容入口？**
   建议保留为薄包装，同时提供统一 CLI。
2. **配置格式**
   建议新增 `config.toml`，继续兼容 `config.txt`；还是只保留 `config.txt`？
3. **默认音频格式**
   建议 `flac`（约 66 MB / 3 s 编码）；可选 `wav`、`ogg`、`mp3`。
4. **是否加入浏览器 Web Audio 实时播放模式？**
   加入后可完全省去离线混音（最大瓶颈直接消失），但 JS 预览逻辑需要重写；建议作为 Phase 4 可选增强，先交付离线混音优化。
5. **输出兼容级别**
   建议 `1.aff`/rhythm/timing 保持旧格式；音频扩展名和 offset 语义按修复后行为。若必须逐字节兼容，需要增加 `--compat` 开关。

---

## 11. 建议的下一步

1. **Phase 3 收尾**：`2.py` 的精确有理数量化、同时间点绿蛇标记合并；`3.py` 直接字符串构建 SVG（当前 svgwrite 仍占约 3 s）；`4.py` 的 config offset 语义。
2. **Phase 1 包化**：把 `run.py` 升级为 `arcaea_rhythm` 包和 `arcaea-rhythm` 入口，新增 `config.toml`、缓存、批量。
3. **Phase 4 预览**：HTML 模板化、字体注入、宽度自适应；Web Audio 实时发声作为可选模式。
4. **Phase 5 测试**：把当前的“逐字节/峰值/RMS”对比固化为 pytest，覆盖短谱面、长谱面、空谱面、异常配置。

当前已经可以直接使用 `python run.py`；后续改造会保持 `1.py`~`4.py` 兼容入口。
