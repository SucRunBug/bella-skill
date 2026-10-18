# 拼贴画 B-roll

本目录属于 [bella-skill](https://github.com/SucRunBug/bella-skill) 合集。安装完整合集：

```bash
npx -y skills add SucRunBug/bella-skill -g --all
```

也可用 `--skill bella-ai-collage-maker` 代替 `--all` 只装本项。安装后可直接调用 `$bella-ai-collage-maker`。原仓库独立安装说明保留在下方。

---

# bella-ai-collage-maker

把一段口播或一个观点交给 Codex，自动做成纸拼贴风格的 B-roll 制作包。

<p align="center">
  <img src="assets/demo-purple.gif" width="220" alt="紫色背景的工厂与大门逐步组装成形">
  <img src="assets/demo-yellow.gif" width="220" alt="黄色背景的工具箱与创作工具逐步组装成形">
  <img src="assets/demo-teal.gif" width="220" alt="青绿色背景的手提箱与内容模块逐步组装成形">
</p>

你只需要提供文案和目标时长。它会自己理解这句话想表达什么，设计一个合适的视觉比喻，再生成静帧、首尾帧、视频提示词和操作说明。

默认不会调用外部视频模型，也不会产生付费任务。使用 Codex 自带的图片生成能力即可，**不需要配置 API Key**。

## 它会帮你做什么

输入一段文案后，它会自动完成：

1. 提炼文案的核心意思，确定一个直观的拼贴画面。
2. 生成 9:16 的纸拼贴静帧，并检查画面是否清楚、有没有假字或水印。
3. 准备纯色首帧和完整尾帧。
4. 写好图生视频提示词、建议参数和操作说明。
5. 把所有文件整理到一个项目文件夹里，一次性交付。

整个过程默认连续执行，不需要反复确认。如果你只想先看画面方案，可以在开头说明“先别生图”或“先给我看方案”。

## 最终会得到什么

默认交付的是一套可以直接拿去生成视频的制作包，主要包括：

- 文案理解和画面思路
- 拼贴静帧与预览图
- 纯色首帧和完整尾帧
- 可直接复制的视频提示词
- 时长、比例、帧率等建议参数
- 简单的手工生成说明

项目默认保存在：

```text
~/hyperframes-projects/YYYY-MM-DD-collage-broll-标题/
```

> 说明：这个 skill 默认不直接生成最终 MP4。你可以把它准备好的首尾帧和提示词放进支持双关键帧的图生视频工具中继续生成。

## 安装

### Codex

在终端运行：

```bash
git clone https://github.com/SucRunBug/bella-ai-collage-maker.git ~/.codex/skills/bella-ai-collage-maker
```

安装后重新打开一个 Codex 任务即可使用。

如果你已经安装过，可以进入目录更新：

```bash
cd ~/.codex/skills/bella-ai-collage-maker
git pull
```

也可以把整个仓库放进其他兼容的 skills 目录，例如 `~/.agents/skills/`。

## 环境要求

- Codex，以及其中可用的图片生成能力
- `ffmpeg` 和 `ffprobe`

检查本机环境：

```bash
bash scripts/check_setup.sh
```

macOS 没有安装 FFmpeg 时，可以运行：

```bash
brew install ffmpeg
```

不需要 Gemini API Key，也不需要配置其他视频模型的密钥。

## 怎么用

直接对 Codex 说：

```text
把下面这段口播做成 6 秒的纸拼贴 B-roll：
很多人以为 AI 是来替你思考的，其实它更像一面镜子，会把你问题里的漏洞照出来。
```

下面这些说法也可以：

- “把这句话做成拼贴风格画面，5 秒。”
- “给这段口播配一个半调纸拼贴 B-roll。”
- “先给我看拼贴画面方案，暂时不要生图。”

没有写时长时，默认按 5 秒处理。一次提交多段文案也可以，每段可以设置不同的时长。

## 适合哪些内容

- 观点口播
- 抽象概念解释
- AI、科技、商业类视频
- 需要视觉比喻的过场画面
- 想统一做成纸拼贴风格的一组 B-roll

如果你需要真人产品广告、写实场景，或者必须精确控制每一层素材和动画时间线，这个 skill 就不太适合。

## 常见问题

### 需要 API Key 吗？

不需要。默认流程使用 Codex 自带的图片生成能力，不会调用外部付费视频接口。

### 为什么没有直接给我 MP4？

不同视频模型支持的时长、参数和首尾帧方式并不一样。这个 skill 会先把最通用的首尾帧、提示词和参数准备好，你可以再放进自己常用的视频工具中生成。

### 中途需要确认画面吗？

默认不需要。它会自动选择最合适的方案并继续执行。只有你明确要求先预览时，才会停下来等你确认。

### 仓库里的旧视频脚本有什么用？

`scripts/generate_video.py`、`scripts/generate_veo_first_last.py` 和 `scripts/upload_file.py` 是为旧项目保留的兼容脚本，默认流程不会调用，也不需要为它们配置 API Key。

## 主要文件

```text
bella-ai-collage-maker/
├── SKILL.md                 # 完整工作流程和画面规则
├── agents/openai.yaml       # Codex 显示与调用配置
├── evals/evals.json         # 行为测试样例
├── assets/                  # README 演示素材
└── scripts/                 # 环境检查与兼容脚本
```

## License

[MIT](LICENSE)
