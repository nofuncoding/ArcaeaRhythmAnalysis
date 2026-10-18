# TODO

## 网页预览导出视频

**目标**：把 `index_{chart}.html` 的节奏预览导出为 MP4/WebM，音画同步，支持片段与不同分辨率。

**方案**：不要录实时播放；先把预览改成可寻址的 `renderAt(t)`，再用 Playwright 逐帧截图 + ffmpeg 编码。

- [x] 预览内已实现 `renderAt(elapsed)` 与统一的音频时间轴（BPM 变化/offset 不再漂移）。
- [ ] 暴露 `window.__arcaea.renderAt(t)`，播放和导出共用同一时间轴。
- [ ] `?render=1` 模式：隐藏开始遮罩、禁用 CSS transition、不播放实时音频。
- [ ] 新增 `arcaea_rhythm/render/`：
  - `timeline.py`：timing -> 时间段、scroll 距离
  - `browser.py`：Playwright 启动/截图循环
  - `encode.py`：ffmpeg 封装
- [ ] 新增命令：
  ```bash
  arcaea-rhythm render --folder KikaiNoTsubasa --chart 3 --output preview.mp4 --fps 30 --width 1920 --height 1080
  ```
- [ ] 音频混入：`note_*.flac` + `adelay`（lead-in），支持 `--no-audio`、`--trim-lead-in`。
- [ ] 片段导出：`--from` / `--to`。
- [ ] 性能：默认 1280×720/24fps；支持 JPEG 帧、`--keep-frames`、后续并行分段。
- [ ] 依赖：可选 extra `render = ["playwright>=1.50"]`；`doctor` 检查 ffmpeg/Chromium。
- [ ] 测试：timeline 单元测试、1 秒短片 smoke test、`ffprobe` 校验时长/帧率/音轨。

**备选**：如果追求速度，可后续改为 Canvas/WebCodecs 或“长 SVG 裁剪 + ffmpeg”离线渲染；接口保持 `renderAt(t)` 不变。

## 其他待办

- [ ] P4 批量模式：`build --all` / `--jobs`。
- [ ] `scenecontrol(...,hidegroup,...)` 的普通 timinggroup 是否应完全忽略，需谱面数据确认。
- [ ] 拍号检测/显示；小节数显示
- [ ] Debug overlay
- [ ] 修 bug
