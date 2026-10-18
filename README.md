# ArcaeaRhythmAnalysis

对 @石原坂奈 的 ArcaeaRhythmAnalysis 的 AI 重写。

Arcaea 谱面节奏解析工具：清理连蛇/碎蛇、生成节奏数组、绘制节奏 SVG，并生成带按键音的网页预览。

## 环境

- Python **3.14+**
- 依赖见 [requirements.txt](requirements.txt)

```bash
python3.14 -m venv .venv
. .venv/bin/activate        # fish: . .venv/bin/activate.fish
pip install -r requirements.txt
pip install -e .            # 安装 arcaea-rhythm 命令
```

如果不想安装，也可以直接 `python -m arcaea_rhythm` 或 `python run.py`。

音频解码/编码使用 `soundfile`（内置 libsndfile），混音使用 NumPy，**不再需要 pydub、audioop 或 ffmpeg**。

## 快速开始

1. 把谱面文件夹放入 `charts/`，确保包含 `{chart}.aff` 和 `base.ogg`（也支持 `base.mp3` / `base.wav` / `base.flac`）。
2. 调整全局参数：可以继续编辑 [config.txt](config.txt)，或复制 [config.example.toml](config.example.toml) 为 `config.toml` 使用 TOML 格式。
3. 一条命令跑完；`build` 会自动扫描 `charts/`，交互选择谱面文件夹和难度：

```bash
arcaea-rhythm build
# 等价：python run.py

# 也可以直接指定，跳过选择
arcaea-rhythm build --folder KikaiNoTsubasa --chart 3
```

`--chart` 的 2/3/4 分别对应 ftr/byd/etr；程序只会列出实际存在 `{chart}.aff` 的难度。

完整流程默认会在阶段之间用 **Y/n** 询问是否已完成手动修改：

1. `1.py` 后：检查 `1.aff` / `0.aff` 和 `timing_{chart}.txt`；
2. `2.py` 后：检查 `rhythm_{chart}.txt`；
3. `3.py` 后：检查 SVG，继续生成音频和预览。

输入 `n` 会暂停并提示继续命令；修改完成后用 `--from` 从指定阶段继续：

```bash
arcaea-rhythm build --from rhythm   # 改完 1.aff/timing 后继续
arcaea-rhythm build --from svg      # 改完 rhythm 后继续
arcaea-rhythm build --from audio    # 检查完 SVG 后继续
```

自动化或不想确认时加 `-y/--yes`。非交互环境（管道、CI）中 Y/n 会自动继续；如果 `charts/` 下存在多个谱面或多个难度，需要用 `--folder/--chart` 指定。

也可以只跑某个阶段：

```bash
arcaea-rhythm build --stage svg          # 只重画 SVG
arcaea-rhythm build --stage audio --force # 只重建音频
arcaea-rhythm build --stage preview      # 只生成 HTML，不重新混音
```

`run.py` 会依次调用四个脚本；`4.py` 生成音频和 `index_{chart}.html`，并自动打开浏览器。预览页需要点击一次才能播放。

## 命令行

```bash
arcaea-rhythm build              # 完整流水线
arcaea-rhythm build --folder KikaiNoTsubasa --chart 3
arcaea-rhythm build --stage audio --force
arcaea-rhythm list               # 列出 charts/ 下的谱面与难度
arcaea-rhythm doctor             # 检查 Python、依赖、谱面、音频、字体
arcaea-rhythm migrate-config     # config.txt -> config.toml
```

`build` 与 `python run.py` 参数完全一致；`--folder/--chart` 可临时覆盖配置。

## 配置

- **旧格式**：[config.txt](config.txt)，键值对形式，继续完全兼容。
- **推荐格式**：复制 `config.example.toml` 为 `config.toml`：

```bash
cp config.example.toml config.toml
```

- 查找顺序：`--config PATH` > `config.toml` > `config.txt`。
- 配置只保存全局参数；**谱面文件夹和难度不再写进配置**，运行时选择或用 `--folder/--chart` 指定。
- 旧配置里如果仍有 `folder`/`chart`，仍可读取并作为选择默认值。
- 音频格式在 `[audio] format` 中设置。
- `offset` 是额外手动延迟（ms），会与谱面的 `AudioOffset` 相加后应用到音频和预览时间。
- `max_bpm` 默认 1000，自动忽略 `9999999` 等特效 BPM；设为 0 可关闭过滤。
- 四个脚本和 `run.py` 都支持 `--config`。

## 缓存

`run.py` 会按“输入文件哈希 + 配置指纹”缓存各阶段，缓存文件为：

```text
charts/<folder>/.arcaea-cache.json
```

- 输入没变时直接跳过 `2.py` / `3.py` / 音频生成；重复跑完整流程约 0.3 秒。
- 手动修改 `rhythm_{chart}.txt` 会触发 SVG 重建；修改 SVG/HTML 不会被覆盖（缓存命中时跳过）。
- `--force` 忽略缓存并重建；`--no-cache` 完全不读写缓存。
- 直接运行 `1.py`~`4.py` 不会更新缓存；之后建议用 `--force` 或 `--no-cache`。

## 脚本说明

### run.py：一键运行

- `--stage all|arcs|rhythm|svg|audio|preview`：只跑一个阶段
- `--from arcs|rhythm|svg|audio|preview`：从该阶段运行到结尾
- `--config PATH`：指定配置文件
- `--max-bpm N`：过滤高于 N 的特效 BPM（默认 1000，0=不过滤）
- `--keep-effect-bpm` / `--no-ignore-effect-bpm`：保留 `9999999` 等特效 BPM，等价于 `--max-bpm 0`
- `--ignore-effect-bpm`：兼容项；默认已按 `max_bpm=1000` 过滤 `9999999` 等特效 timing
- `-y/--yes`：跳过阶段间的 Y/n 确认
- `--force`：忽略缓存，强制重建 1.aff/0.aff 和按键音
- `--no-cache`：不读写阶段缓存
- `--refresh-timing`：重新提取 timing（会覆盖手动修改）
- `--no-audio` / `--no-open` / `--audio-format`
- `-v/--verbose`：显示 timing、节奏数组等详细中间结果

### 1.py：清理连蛇/碎蛇

- 输入 `{chart}.aff`，输出 `1.aff`（chart=3/4）或 `0.aff`（chart=2）。
- 同时提取顶层 `timing` 到 `timing_{chart}.txt`。
- 按源文件顺序过滤 `timinggroup(noinput...)`，noinput 段里的 arc 不会混入输出。
- 与原版工具输出（`docs/`）对比：timing 完全一致，rhythm 仅少一条 `2/195`（258 秒隐藏 arc 造成）。
- 已存在输出时默认跳过；强制重建：

```bash
python 1.py --force
```

> `--force` 默认保留已有 `timing_{chart}.txt`，避免覆盖手动修正；需要重新提取时加 `--refresh-timing`。

### 2.py：生成节奏数组

- 读取 `1.aff` / `0.aff` 和 `timing_{chart}.txt`，输出 `rhythm_{chart}.txt`。
- 自动跳过 BPM<=0 的 timing，并默认过滤 BPM>1000 的特效值（`max_bpm=1000`），避免除零和异常时长。
- 如果出现未预设的细分（如 11 连音），在 `2.py` 的 `allowed_denominators` 中添加。

### 3.py：生成节奏 SVG

- 输出 `rhythm_{chart}.svg` 和 `default_{chart}.svg`。
- 长音频会按最后一个音符自动延长画布，不再固定截断在 680/1200 拍。
- 过滤 BPM<=0 与 999/1024 特效拍号，拍线起点钳制到 0，避免负坐标崩溃。
- 0ms timing 锚点保证开头 BPM 正确；拍线只按谱面时间计算，不叠加 `AudioOffset`；用整数小节判断避免浮点误差累积。
- 兼容 3 字段 timing 行（自动补 `note_value_per_beat=4`）。
- SVG 内嵌 `@font-face`，加载 `fonts/` 下的 Exo/Edwin 字体。

### 4.py：生成音频与网页预览

```bash
python 4.py                      # 生成音频 + HTML，并打开浏览器
python 4.py --force              # 强制重新生成音频
python 4.py --no-audio           # 只生成 HTML（复用已有音频）
python 4.py --no-open            # 不自动打开浏览器
python 4.py --audio-format wav   # 覆盖 config.txt 的输出格式
python 4.py --folder KikaiNoTsubasa --chart 3
```

预览页现在包含：

- 点击开始的遮罩，解决浏览器自动播放限制；
- timing 数据以 JSON 注入，不再用正则解析大字符串；
- 1280×720 设计稿按窗口等比缩放，五边形位置由 CSS 变量计算；
- 音频缺失时仍可点击开始查看 SVG 动画；
- BPM 变化时用统一的音频时间轴和 `requestAnimationFrame` 滚动，避免偏移累积。

输出格式在 `config.txt` 的 `audio_format` 中设置：

| 格式 | 510 秒音频体积 | 编码耗时（实测） | 说明 |
|---|---:|---:|---|
| `flac` | 约 65 MB | 约 8 秒 | 默认，无损、编码快 |
| `wav` | 约 86 MB | 约 2 秒 | 兼容性最好，体积最大 |
| `ogg` | 约 6.5 MB | 约 47 秒 | 体积小，适合分享 |
| `mp3` | 约 8.6 MB | 约 30 秒 | 兼容旧设备 |

> 音频混音本身约 0.2 秒；主要耗时在解码 base 音频和编码输出。

## 输出文件

```text
charts/<folder>/
  0.aff / 1.aff
  timing_<chart>.txt
  rhythm_<chart>.txt
  rhythm_<chart>.svg
  default_<chart>.svg
  note_<chart>.flac
  index_<chart>.html
```

## 注意事项

- 预览会按窗口自动适配 1280×720 设计稿；`config.txt` 的 `width` 作为额外缩放系数，默认 1280（即 1.0）。
- `rhythm_{chart}.txt`、`timing_{chart}.txt` 是中间结果，可手动修正；重跑对应脚本前注意备份。
- 字体放在 `fonts/`。如果 SVG 中文字体没有正确显示，请确认浏览器能访问该目录。
- 文件夹中提供了《多次元宇宙融合論》的 ETR 节奏解析预览；为避免版权问题，未提供原始谱面和音乐音频。

## 测试

```bash
python -m unittest discover -s tests -v
```

当前覆盖配置加载、缓存、CLI、谱面/难度选择、音频混音辅助函数、noinput 过滤、timing 清洗，共 30 个测试。

## 开发

```bash
pip install -e .[dev]
python -m pytest
ruff check .
mypy arcaea_rhythm
```

CI 配置见 [.github/workflows/ci.yml](.github/workflows/ci.yml)，在 Python 3.14 上运行单元测试。

## 性能

在 510 秒、约 3300 个按键音事件的样本上：

- 旧版 pydub 混音：约 44 分钟（外推）
- 新版 soundfile + NumPy：混音约 0.2 秒；完整 FLAC 输出约 10 秒

更完整的升级计划见 [UPGRADE_PLAN.md](UPGRADE_PLAN.md)，数据对比记录见 [docs/extradimensional-validation.md](docs/extradimensional-validation.md)，待办见 [TODO.md](TODO.md)。
