# Bella Skill

英语学习、科研、自媒体和 3D 游戏资产的 Skill 合集。把任务交给 **`bella-skill` 主入口**，它会根据目标、已有材料和当前阶段选择合适的技能，在当前对话继续执行。

## 安装

需要 Node.js / npm 和 Git：

```bash
npx -y skills add SucRunBug/bella-skill -g --all
```

这会安装 **1 个主入口 + 10 个专项技能**。重开会话后，直接说：

> 使用 $bella-skill，我想练十分钟日常英语口语。

> 使用 $bella-skill，把这份英语音频做成能逐句听原声的双语网页。

> 使用 $bella-skill，读取这个对标视频，按讲述顺序整理原话和画面线索。

> 使用 $bella-skill，这是我的音乐和歌词，帮我做成可以继续修改的二维动画 MV。

> 使用 $bella-skill，这是我的产品网址，帮我选风格并制作一支产品宣传片。

> 使用 $bella-skill，我已经有论文草稿，帮我检查贡献与证据是否对应。

也可以直接调用 `$bella-speaking-coach` 等专项技能。只想安装某一项：

```bash
npx -y skills add SucRunBug/bella-skill -g --skill bella-speaking-coach
```

`--all` 会选中全部技能和全部受支持的宿主。需要交互选择时移除它；只装到某个宿主时，用 `--skill '*' --agent codex -y` 或将宿主改为 `claude-code`。**只装 `bella-skill` 主入口不会连带安装其他成员**。安装说明见 [docs/installation.md](docs/installation.md)。

## 四类技能

| 分类文件夹 | 技能 | 主要交付 |
|---|---|---|
| `english/` 英语 | [bella-speaking-coach](skills/english/bella-speaking-coach/SKILL.md) | 日常口语、复述、IELTS / PTE / TOEFL 口语训练与复练记录 |
| `english/` 英语 | [bella-audio-listening](skills/english/bella-audio-listening/SKILL.md) | 内嵌原声、逐句播放、中英对照的离线听读网页 |
| `research/` 科研 | [bella-ai4s](skills/research/bella-ai4s/SKILL.md) | 文献、研究方案、实验复现、分析、论文、科研图表与汇报 |
| `media/` 自媒体 | [bella-ai-collage-maker](skills/media/bella-ai-collage-maker/SKILL.md) | 半调纸拼贴 B-roll 静帧、首尾帧与视频制作包 |
| `media/` 自媒体 | [bella-music-mv](skills/media/bella-music-mv/SKILL.md) | 从音乐和歌词制作可编辑的程序化二维动画 MV、成片与检查材料 |
| `media/` 自媒体 | [bella-product-promo](skills/media/bella-product-promo/SKILL.md) | 产品宣传与发布片；9 种风格、6 条技术路线、完整参考提示词与可编辑成片 |
| `media/` 自媒体 | [talking-head-video-packaging](skills/media/talking-head-video-packaging/SKILL.md) | 口播精剪、字幕、抠像、配图和时间线包装 |
| `media/` 自媒体 | [bella-writer](skills/media/bella-writer/SKILL.md) | 从主题、资料、大纲或已有稿件进入文案创作与修订 |
| `media/` 自媒体 | [yanmai-video-reading](skills/media/yanmai-video-reading/SKILL.md) | 对标视频读取、转写、顺序拆解和画面备注 |
| `game-3d/` 3D 游戏 | [tripo-3d](skills/game-3d/tripo-3d/SKILL.md) | 文字 / 图片建模、绑定、动画、模型检查与游戏资产接入 |

## 主入口怎样路由

1. 接住用户当前目标，确认已有材料与本轮交付物。
2. 从维护中的技能目录找到可用成员，核对实际安装的 `SKILL.md`。
3. 默认选择一个最匹配的技能，同一轮开始执行。
4. 当前分工完成后，只有原请求还需要下一步时才重新判断并衔接。

已有大纲就从大纲继续，已有粗剪就从包装继续。不会固定串起“拆解 → 写稿 → 配图 → 剪辑”的整条流程。分类文件夹负责整理，选择技能由主入口完成。

设计参考 [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) 的动态发现、接手边界与上下文交接；本合集独立运行，无需安装 dbskill。详见 [路由设计](docs/routing.md)。

## 仓库结构

```text
skills/
├── bella-skill/                       # 唯一主路由
├── english/                           # 英语合集
│   ├── bella-speaking-coach/
│   └── bella-audio-listening/
├── research/                          # 科研
│   └── bella-ai4s/
├── media/                             # 自媒体
│   ├── bella-ai-collage-maker/
│   ├── bella-music-mv/
│   ├── bella-product-promo/
│   ├── talking-head-video-packaging/
│   ├── bella-writer/
│   └── yanmai-video-reading/
└── game-3d/                           # 3D 游戏
    └── tripo-3d/
```

每个成员自带 `SKILL.md` 和实际需要的 scripts、references、assets，可独立安装。安装器将成员放在同级目录时，主入口仍能定位它们。

## 使用条件

- 基础脚本使用 Python 3.10+；媒体处理按需使用 ffmpeg / ffprobe 和可用的转写后端。
- 拼贴需要宿主提供图片生成能力；默认交付制作包，自动生成视频要有用户明确要求和可用模型。
- 音乐 MV 自带程序化二维动画起步工程和新手引导；需要 Node.js、可运行的 Chrome / Chromium、ffmpeg / ffprobe。提供音乐与歌词即可开始，Agent 完成分镜、场景代码、渲染检查和 MP4 导出；精确歌词对齐按可用工具和人工校正处理。
- 产品宣传片先引导产品、受众、卖点与发布规格，按需选择 HTML/Canvas/SVG、GSAP、Remotion、Three.js、Blender 或混合制作；保留 12 份完整原始提示词。内置浏览器起步工程与逐帧渲染协议，其他路线依实际工具执行；安装技能不会预装所有引擎。
- 口播包装需要可连接的 ChatCut Desktop 与对应编辑能力。本合集不捆绑 ChatCut、所有配套技能、用户模板或项目素材。
- 3D 建模需要用户自己的 Tripo API Key；Blender 和游戏引擎按任务配置，资产能力不等于完整游戏开发环境。
- 安装 Skill 不会自动安装模型、专业软件或付费服务。工具缺失时应如实说明可完成的范围。

## 验证与来源

```bash
python3 tools/check_collection.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

源版本、命名迁移与整合改动见 [SOURCES.md](SOURCES.md)。各子目录保留原有许可证；未声明许可证的部分没有在本次整合中另行授予统一许可证。
