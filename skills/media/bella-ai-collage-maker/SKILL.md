---
name: bella-ai-collage-maker
description: 将口播文案、观点或抽象概念生成半调纸拼贴 B-roll 静帧及视频制作包。用户需要纸拼贴配画面、拼贴动画设计或从空场组装的首尾帧时使用；默认交付制作包，不生成 MP4。
---

# Bella 拼贴 B-roll

把口播压成一个 sharp visual idea，再做成高级编辑风纸拼贴组装动画制作包。

## 默认行为：一键自动完成

用户只需提供：

- 口播文案
- 目标时长（如 `5 秒`、`8s`）

收到输入后连续完成以下步骤，中途不询问、不展示候选方案、不等待“可以 / 通过 / 全部通过”：

1. 自动确定一个最清晰的视觉隐喻
2. 自动写 visual spec 和 imagegen prompt
3. 自动生成拼贴静帧并做 QA；所有合理方案默认通过
4. 自动准备纯色首帧、统一尺寸尾帧、视频提示词和参数
5. 一次性展示 contact sheet，并交付完整项目目录

只有以下情况允许暂停：

- 用户明确说“先给我看方案”“先别生图”或要求逐步确认
- 缺少图片生成能力且无法用当前环境的等效工具替代
- 缺少处理交付文件所必需的工具且无法安全绕过
- 输入彼此冲突，继续执行会明显偏离用户意图

不要因为颜色、构图、物件或隐喻存在多个合理选择而询问用户。直接按本 skill 的规则做最佳判断。用户未给时长时不要追问，默认 `5 秒`；时长表达模糊时取最合理的秒数并在 `brief.md` 记录假设。

本 skill 的“最终结果”默认指可直接用于双关键帧图生视频的完整制作包，不是 MP4。不要自动调用 Gemini、Veo 或其他外部视频服务，不要提交付费任务。只有用户另行明确要求自动生成视频，并且可用模型、凭据和目标平台都已确定时，才进入视频生成。

## 环境自检

每次触发后先运行：

```bash
bash <本skill目录>/scripts/check_setup.sh
```

自检通过则静默继续。失败时先尝试当前环境已有的等效能力；确实无法继续时，只报告缺失项和最短修复方式，不输出需要用户“确认配置完成”的审批话术。

- ffmpeg / ffprobe 缺失：
  - macOS：`brew install ffmpeg`
  - Debian/Ubuntu：`sudo apt install ffmpeg`
- 没有 `image_gen` 或等效图片生成能力：说明无法生成最终静帧，并指出用户可提供一张静帧后继续制作交接包

## 成功标准

- 一条口播只表达一个清晰隐喻
- 同一批画面有统一设计语言，但不强制全部蓝底
- 背景是强烈、平坦、均匀的色场，可按语意变化
- 主体以黑白 halftone photographic cut-outs 为骨架
- 关键卡片、按钮、胶片、规则册等允许使用红、黄、青、橙、紫、奶油白彩色纸张
- 所有纸片有清晰裁切边、奶油白 keyline、低透明度柔和阴影和纸张颗粒
- 动作是 assemble-from-empty，不是轻微漂移、晃动或慢 zoom
- 无字幕、无口播全文、无 logo、无水印、无 UI
- 默认 9:16、720×1280、24fps、无声；时长使用用户给定值

## 时长规则

- 目标时长写入所有提示词、参数和操作说明，不得再硬编码为 5 秒
- `3–10 秒`：默认做成一个连续镜头
- `<3 秒`：减少到 2–3 个组装动作，保证能在目标时长内读懂
- `>10 秒`：按语义拆为多个连续片段，每段优先 `4–8 秒`，总时长尽量等于用户目标；每段独立生成一套首尾帧和提示词
- 批量输入时，每条文案可有独立时长；只给一个总时长时，按口播字数和语义密度自动分配，并把分配写入 `brief.md`

## 什么时候不要用

- 需要精确控制图层、遮挡、镜头穿越或可编辑时间线：改用分层动画工具
- 只需要视频提示词，且不需要隐喻设计和静帧：直接写 prompt
- 需要真实人物产品广告或口播演员：不要走本拼贴流程
- 用户明确要可逐层修改的透明素材：本 skill 默认不拆透明图层

## 默认项目目录

使用北京时间 `Asia/Shanghai` 命名：

```text
~/hyperframes-projects/YYYY-MM-DD-collage-broll-标题/
```

项目结构：

```text
<project>/
├── brief.md
├── visual-spec.json
├── imagegen-prompts.md
├── still-qa.md
├── still-contact-sheet.jpg
├── manual-video-guide.md
├── 01-概念名/
│   ├── video-prompt.txt
│   ├── video-settings.json
│   └── frames/
│       ├── last-frame-original.png
│       ├── first-frame.png
│       └── last-frame.png
└── 02-概念名/...
```

## Phase 1：自动设计视觉隐喻

把文稿压成一个视觉命题，提取：

- 核心意思：观众最终要看懂什么
- 情绪：冷静、惊讶、紧迫、豁然开朗、荒诞、反讽
- 动作动词：打开、连接、漏掉、装订、归档、点亮、压缩、分叉、组装
- 可视化隐喻：机器、时钟、胶片、档案柜、控制台、规则册、漏斗、轨道、棋子

不要把文稿逐字放进画面。默认一条文稿只做一个隐喻，控制在 3–6 个关键物件；短于 3 秒时减少物件，长于 10 秒时按“问题 → 转折 → 结果”拆片。

直接选择语义最准确、构图最容易一眼读懂、组装动作最稳定的方案。把核心意思、情绪、视觉命题、关键物件、色彩和组装顺序写入 `brief.md`，然后立刻进入 Phase 2，不向用户展示备选项。

批量文案优先形成前后叙事，例如先表现手工消耗与经验流失，再表现规范沉淀与人机分工。

## Phase 2：自动生成并 QA 彩色拼贴静帧

先写自包含的 `visual-spec.json`：

```json
{
  "script_meaning": "",
  "target_duration_seconds": 5,
  "visual_metaphor": "",
  "style_signature": "flat bold color field, mixed black-and-white halftone cut-outs and colored cardstock accents, crisp cut edges, cream keylines, soft paper shadows, editorial paper collage",
  "aspect_ratio": "9:16",
  "color_field": {
    "background_hex": "",
    "accent_colors": [],
    "paper_grain": "fine uncoated-paper fiber"
  },
  "elements": [
    {
      "what": "",
      "role": "",
      "motion": "",
      "placement": ""
    }
  ],
  "composition": {
    "layout": "",
    "negative_space": "",
    "final_frame": ""
  },
  "motion_plan": "structure first, subject or cards second, action and result last",
  "avoid": "typography, readable letters, numerals, logos, watermark, UI, subtitles, glossy 3D, photoreal environment"
}
```

示例中的 `5` 只是字段示意，实际必须替换成用户时长或自动分配的片段时长。

### 色彩规则

根据语意挑选强色场，并在同一批作品中保持“同设计语言、不同底色”：

- 焦橙 / 红：时间消耗、劳动、紧迫
- 芥末黄：工具、警示、经验漏失
- 墨绿：认知、审美、系统重置
- 深紫：规范、沉淀、长期记忆
- 青绿：判断、协作、自动执行

主体可以黑白半调为主，但局部彩色纸张必须服务信息层级。

### Imagegen prompt 模板

使用 Codex 内置 `image_gen`；本地存在 `imagegen` skill 时一并遵守：

```text
Use case: ads-marketing
Asset type: final still frame for a 9:16 image-to-video B-roll clip
Primary request: Create a finished editorial paper-collage image expressing [一句话视觉命题].
Scene/backdrop: perfectly flat [颜色] paper field [hex] with subtle uncoated paper fiber.
Style/medium: premium editorial stop-motion paper collage; black-and-white halftone photographic cut-outs mixed with selective [点色] colored cardstock.
Composition/framing: vertical 9:16 locked poster frame; central subject within the middle 70 percent; generous clean color-field negative space; 3–6 large separable paper groups for later assemble-from-empty animation.
Materials/textures: visible printed halftone dots, crisp machine-cut edges, thin warm-cream paper keylines, soft low-opacity physical drop shadows.
Constraints: [本条隐喻必须一眼看懂的关系].
Avoid: no typography, no readable letters, no numerals, no logos, no watermark, no UI, no subtitles, no glossy 3D, no photoreal environment, no clutter.
```

### 自动静帧 QA

检查：

- 隐喻是否一眼看懂
- 主体是否集中
- 是否有假字、logo、水印或 UI
- 是否保留足够纯色场，方便从空场组装
- 是否是 3–6 个清晰大组，而不是满屏碎片
- 同一批是否统一质感但有色彩变化

所有满足成功标准的静帧默认通过，不征求用户确认。若有明显失败，自动重生该条，最多两轮；仍有轻微瑕疵但不影响隐喻和后续使用时，选择最佳版本继续，不停下来审批。只有假字、logo、水印、严重构图错误或隐喻不可读等阻断性问题仍存在时，才报告失败。

保存原图，生成带编号 contact sheet，把 QA 结论写入 `<project>/still-qa.md`，然后直接进入 Phase 3。重生时保留旧版 contact sheet 为 `still-contact-sheet-v2.jpg`、`v3.jpg`。

## Phase 3：自动准备视频制作包

### 1. 准备首尾帧

保留 imagegen 原图，再统一尾帧：

```bash
ffmpeg -y -i <item>/frames/last-frame-original.png \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  <item>/frames/last-frame.png
```

首帧默认是与尾帧相同底色的纯色空纸面：

```bash
ffmpeg -y -f lavfi -i color=c=0x<HEX>:s=1080x1920 \
  -frames:v 1 <item>/frames/first-frame.png
```

只有用户明确要求不从完全空白开始时，首帧才保留一个基础物件。

### 2. 写模型中立的视频 prompt

动作顺序默认采用：

```text
基础结构 → 人物或关键卡片 → 连接件 → 动作 → 最终结果
```

按目标时长控制动作数量和节拍，保存为 `<item>/video-prompt.txt`：

```text
Paper-collage stop-motion assembly lasting exactly [目标时长] seconds, using Image 1 as the exact empty first frame and Image 2 as the exact completed last frame. In one continuous locked-off vertical shot, open on the empty flat [color] paper field.

Assemble the scene piece by piece with crisp physical stop-motion timing: [按顺序描述元素如何滑入、卡位、连接和完成动作，并给出大致时间段]. End by holding the supplied completed composition until the exact target duration.

Preserve the exact 9:16 framing, [hex] color field, colored cardstock accents, uncoated paper grain, halftone dots, cream keylines, crisp cut edges and soft shadows. Restrained tactile 2D paper craft only.

No scene cuts, no camera movement, no zoom, no morphing, no new objects, no text, no letters, no numbers, no logos, no watermark, no UI, no sound.
```

明确 Image 1 是空首帧、Image 2 是完成帧。最终构图必须贴近 Image 2。用户指定目标模型时，额外提供适配版提示词与真实支持的参数，不编造能力。

### 3. 写建议参数

为每条创建 `<item>/video-settings.json`：

```json
{
  "mode": "first-and-last-frame image-to-video",
  "first_frame": "<item>/frames/first-frame.png",
  "last_frame": "<item>/frames/last-frame.png",
  "prompt_file": "<item>/video-prompt.txt",
  "aspect_ratio": "9:16",
  "duration_seconds": "<使用用户目标时长或本片段分配时长>",
  "target_resolution": "720x1280",
  "target_fps": 24,
  "audio": "off",
  "camera": "locked-off",
  "motion": "assemble-from-empty"
}
```

`duration_seconds` 写数值，不写说明文字。

### 4. 写手工操作说明

将以下内容写入 `<project>/manual-video-guide.md>`，并替换为实际时长：

1. 在目标视频工具中进入首尾帧或双关键帧图生视频模式。
2. 将 `first-frame.png` 设为首帧，将 `last-frame.png` 设为尾帧。
3. 粘贴对应的 `video-prompt.txt`。
4. 按 `video-settings.json` 设置 9:16、目标时长、固定镜头、关闭声音；平台不支持的参数跳过。
5. 生成后检查组装动作、最终落位和文字污染；失败时只调整对应条目的提示词或静帧。

### 5. 一次性交付

最终只发一次完整结果，不补发中间审批消息。展示 contact sheet，并提供可点击路径：

- 项目目录
- `brief.md`
- `still-contact-sheet.jpg`
- `last-frame-original.png`
- `first-frame.png`
- `last-frame.png`
- `video-prompt.txt`
- `video-settings.json`
- `manual-video-guide.md`

同时用一句话说明每条文稿如何转成视觉隐喻，并说明：“已按默认自动通过完成全部阶段；本 skill 未调用外部视频模型，交付物是可直接生成视频的制作包。”

## 手工生成后自查

- 首帧接近纯色空场
- 中段能看到结构、人物或卡片逐步进入，不是整体淡入
- 没有切镜、zoom、3D 化或写实场景漂移
- 没有假字、logo、水印或 UI
- 最终帧与完成静帧一致；轻微细节漂移不影响隐喻时可通过
- 成片为 720×1280、24fps、用户目标时长、零音轨；以平台实际支持为准

用户稍后交回手工生成的视频并明确要求 QA 时，再生成视频 contact sheet、首帧检查和尾帧对比。

## 旧视频脚本

`scripts/generate_video.py` 和 `scripts/generate_veo_first_last.py` 仅为旧项目兼容保留。默认流程禁止调用。只有用户另行明确要求自动生成视频，并且已确定模型、凭据、平台和可能产生的费用时，才可使用对应脚本。
