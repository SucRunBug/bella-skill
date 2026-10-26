---
name: bella-music-mv
description: 根据用户提供的音乐和歌词，自主制作有统一角色、叙事、节奏和转场的完整二维动画 MV，交付含原曲与歌词字幕的 MP4、可编辑代码工程和视觉验收记录。适用于“上传歌曲和歌词做 MV”“按歌词做动画音乐视频”及已有该类工程的修改；不用于普通口播包装或仅分析视频。
---

# Bella 音乐 MV

把音乐和歌词做成完整动画作品。使用随包的 p5.js / p5.brush 底座，由编码 agent 编写镜头，再用 Chrome 与 ffmpeg 渲染；渲染过程不需要调用文本生成视频模型。

## 开始与默认值

- 找到用户上传的音频和歌词。歌词可以是对话文本、纯文本、LRC、SRT、VTT 或 JSON；对话文本先保存到项目输入文件。缺少音频或歌词时，一次只补问缺少的材料，已有内容不重复索取。
- 两项齐备就开始：默认完整原曲、16:9 横版、1920×1080、24 fps、歌词 karaoke、柔和水彩与墨线的二维叙事动画。沿用用户指定的画幅、风格、角色和字幕；未指定的创作选择由总导演决定，不列问卷。
- **先写分镜，再直接实施。** 写好 `STORYBOARD.md` 后用简短中文告知主题、风格和制作方向，不等待分镜批准。用户明确要求先审分镜、只要方案或只改局部时，按其范围执行。
- 原曲贯穿全片，包括前奏、间奏与尾奏；不把已完成的开头、示例或预览片当作完整 MV 交付。只有用户要求时才缩短歌曲。
- 上游的“先让用户对分镜反馈”不构成本技能的审批门槛；“不写字”针对场景里的解释性文字，本技能的歌词字幕是明确例外。

首次执行时读 [MV 工作流](references/mv-workflow.md)。设计镜头和检查动作时读 [动画导演规则](references/animation-direction.md)。用户不熟悉制作时，用 [新手指引](references/novice-guide.md) 的第一层解释即可，不要求其学习命令。

## 执行入口

以下命令从本技能目录运行，`scripts/mv.py` 不依赖当前项目恰好是模板目录。输入和项目路径使用绝对路径，含空格时保留引号。

```bash
python3 scripts/mv.py doctor
python3 scripts/mv.py init --audio "/path/to/song.mp3" --lyrics "/path/to/lyrics.txt" --project "/path/to/mv-project"
python3 scripts/mv.py install --project "/path/to/mv-project"
python3 scripts/mv.py analyze --project "/path/to/mv-project"
```

`init` 可接收 `--bpm`、`--offset`、`--fps`、`--aspect landscape|portrait|square`、`--captions karaoke|line|off`。默认使用上述设置；节拍未知时先分析，再由 agent 根据结果调整。音频探测和波形分析在本地执行；无需为基础流程自动安装大型语音模型或上传原曲。

`init` 只生成工作底座与未实现的 `src/scenes/video.js`。**初始化成功不等于 MV 已完成。** 必须根据歌曲写分镜、实现覆盖全曲的章节，再渲染正式成片。

`install` 在项目内安装锁定的 Node 依赖，已有依赖时无需重复。`src/config.js` 的 `const PROJECT = {...};` 对象保持合法 JSON，供包装器读取；完成全部实际镜头后才将其 `status` 改为 `authored`，并更新 `video.js` 的完成元数据。改动 `lyrics.json` 后运行 `python3 scripts/mv.py sync --project "/path/to/mv-project"` 同步浏览器歌词。

## 总导演与章节分工

总导演先统一故事线、角色模型、调色盘与色彩变化、反复出现并得到回报的视觉母题、歌词节拍、字幕安全区和章节边界。以主歌、副歌、桥段和间奏组织章节；重复副歌复用视觉主题并升级动作、规模或情绪，不复制同一段静态画面。

有并行 agent 时，将已明确接口的章节分配出去；没有时按同一计划顺序实现。总导演负责共享文件与最终整合。每个章节作者只编辑指定的 `src/scenes/cXX_*.js`，IIFE 隔离私有辅助函数，通过 `chapter(name, start, end, shots)` 注册；镜头函数为 `fn(t, lt, dur)`。共享角色、道具和接口的修改由总导演处理，不能让多个 agent 同时改同一文件。

`src/scenes/video.js` 是总导演入口，可承载装配说明或公共元数据；章节脚本按序挂入 `studio.html`。以实际加载与注册的镜头核对全片覆盖，不要求把所有镜头堆在一个文件里。

## 三个不能跳过的约束

1. **时间可信。** `lyrics.json` 使用 `start/end/text`，逐词时间可选。`provided` 表示用户提供；`aligned` 表示有实际对齐过程与依据；纯文本按长度分配只能记为 `approximate`。记录每行 `timing` 与 `source`；只有真实词级对齐并核对后才设 `wordTiming: "exact"` 开启逐词高亮，句级 `aligned` 不等于词级精准。估算词进度不能称为精确逐字同步。检查开头、中段、结尾和章节边界；音频结构与节拍候选也不能冒充精确识别。
2. **每帧独立。** 镜头必须绘制完整背景和画面，是时间的纯函数。帧会并行、乱序渲染；禁止依赖前一帧的累计状态、`Math.random()` 或逐帧积分。稳定布局用 `hash()`，手绘抖动用 `boilSeed()`、`jit()`，角色与道具使用稳定标识。
3. **视觉验收。** 每镜至少检查首、中、尾关键帧；关键表演与转场检查逐帧条；脸、手、脚接触和发光检查局部裁剪；各章检查带音频短片，再检查全片。必须打开图像或预览检查结果，不能以“命令成功”代替看画面。

## 完整交付

```bash
python3 scripts/mv.py check --project "/path/to/mv-project"
python3 scripts/mv.py render --project "/path/to/mv-project"
python3 scripts/mv.py verify --project "/path/to/mv-project" --video out/video.mp4
```

- `render --draft` 用于草稿；`render --sheet=...` 等视觉检查参数包装原 Node 渲染器，详细用法见工作流。正式渲染前修复占位镜头、时间空洞、脚本加载与覆盖问题。
- 检查最终 MP4 的视频/音频流、画幅、时长与输入原曲的关系；打开全片抽样及最终帧，确认无空白、截断、错字、遮挡和突然结束。脚本检查通过不能证明动画表演或歌词语义已合格。
- 交付 `out/video.mp4`、完整可编辑工程、`STORYBOARD.md` 及实际生成的检查记录。用中文说明画幅、时长、字幕方式；若时间仍为估算，明确标注。只有实际存在且通过检查的文件才标成“已完成”。
- 依赖或运行环境阻断时先定位并尝试适用的本地修复与软件 WebGL；保留已完成工程，说明具体阻断与剩余工作，不用样例片替代歌曲成片，也不假称导出成功。

## 参考来源与适用规则

本包新增的章节、歌词、草稿检查、缓存和导出参数见 [MV 引擎接口](references/engine-api.md)。继承的完整绘画与角色 API 见 [上游动画指南](references/upstream-animation-guide.md)，按需查阅绘画、时间、角色和纯时间函数章节。本技能的输入、字幕、默认自主执行与交付约定优先于其中面向演示短片的流程。版本与许可见 [来源记录](references/provenance.md)。

PDoomVideo 只提供了“统一分镜后按章节协作、叙事转场、重复主题递进、歌词安全区”的方法启发；不复制其未明确许可的代码、歌曲、角色组合或原分镜。新的歌曲应有自己的故事与镜头。
