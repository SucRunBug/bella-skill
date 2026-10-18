# 英语口语陪练

本目录属于 [bella-skill](https://github.com/SucRunBug/bella-skill) 合集。安装完整合集：

```bash
npx -y skills add SucRunBug/bella-skill -g --all
```

也可用 `--skill bella-speaking-coach` 代替 `--all` 只装本项。安装后可直接调用 `$bella-speaking-coach`。原仓库独立安装说明保留在下方。

---

# bella-speaking-coach

Bella 英语口语私教：从日常聊天到 IELTS、PTE、TOEFL 口语练习，把「先说、反馈、再说、积累、回考」连成持续练习。

当前版本：**0.2.0**。这是供支持 Skill 的 AI Agent 使用的指令与工具包。

## 可以做什么

- **先选择练习目标**：首次目标不明时，引导选择「随便聊聊」或「针对考试练习」，保存偏好，以后也能切换。
- **日常口语陪练**：兴趣话题、生活描述、材料复述，一次一个问题；允许中文补位，卡壳时给几种自然表达。
- **聚焦反馈与复练**：保留用户原话，每次优先改一至两个问题，随后邀请重说或换情境使用。
- **考试专项与模拟**：支持 IELTS Speaking、PTE Academic／Core、TOEFL iBT；区分题库练习与模拟考试，模拟结束后统一反馈。
- **按需检索近期题目**：使用宿主的联网能力核对当前题型、读取公开题目来源，保存来源、核对日期与适用时段。
- **积累与回考**：保存少量词句，区分独立完成、提示后完成和待复练；可按实际记录做阶段复盘。

## 安装

在 Codex 中，首次安装可将仓库克隆到 Skill 目录；目标文件夹须尚不存在：

```bash
git clone https://github.com/SucRunBug/bella-speaking-coach.git "${CODEX_HOME:-$HOME/.codex}/skills/bella-speaking-coach"
```

也可以下载仓库，将文件夹命名为 `bella-speaking-coach`，放入宿主的 Skill 目录。核心文件是 `SKILL.md`、`agents/`、`references/` 和 `scripts/`。安装后在宿主中重新加载 Skill。

## 开始使用

```text
用 $bella-speaking-coach 带我开始口语练习。
```

首次未明确目标时，会先让你选择日常或考试。已经说明目标，就直接进入相应练习：

```text
用 $bella-speaking-coach，聊聊今天发生的事，最后再纠错。

用 $bella-speaking-coach，查一下近期雅思口语话题，带我练 Part 2。

用 $bella-speaking-coach，进行一次 PTE Core 情景回答专项模拟。

用 $bella-speaking-coach，按当前 TOEFL iBT 题型练口语面试。
```

可以随时说「今天随便聊聊」「切到雅思练习」「复习上次的表达」。考试名称、版本和练题／模拟方式明确后即可开始；目标分数和考试日期可选。

## 题目、语音与反馈

题型和题目会按需联网核对；脚本本身不联网，宿主需要提供搜索与网页读取工具。离线时可用注明日期的缓存。随附的 `starter-bank.json` 是 **2026 年 10 月 15 日核对的少量话题与原创练习示例**，不是完整题库，也不代表刚完成更新。

每道题区分官方样题、第三方公开回忆、按话题改编和原创模拟。近期汇编不等于官方在用真题，不保证命中考试。

实时语音依赖宿主能力。只有文字时，练习和反馈限于可观察的内容、用词、语法等；发音和实际口语流利度需要音频证据。训练估计不等于官方成绩。涉及听后复述或图片描述的模拟，需要实际音频或图片素材，并说明计时方式。

## 环境与记录

- 对话由 Agent 完成；本地记录与题库脚本使用 Python 3.10+ 标准库。
- 处理录音时另需 `ffmpeg`／`ffprobe` 与可用的 MLX Whisper 或 faster-whisper 环境。优先检测 Metal／CUDA，再选择后端；转写脚本只使用本地缓存模型，不自动下载模型或上传录音。
- 学习记录默认保存在当前练习项目的 `output/speaking-coach/`，也可指定其他目录。用户原话、反馈、首答和复练分别保留；学习记录不写入 Skill 仓库。

## 维护与验证

```bash
python3 -m unittest discover -s tests -p 'test_speaking*.py' -v
```

测试覆盖记录去重、复习状态、偏好切换、考试版本隔离、题库来源与时效、模拟首答和辅助状态等。录音转写环境可用 `python3 scripts/transcribe_audio.py --probe` 检查。

详细流程与数据格式见 [SKILL.md](SKILL.md) 及其中引用的文档。

## 方法来源

日常训练方法整理自施吾、Evablue、蔡不菜与 Lindsey 的公开分享：兴趣话题、中文补位、生活描述、材料复述、多版本表达、少量积累和后续回考。反馈后复练与可追溯记录由本 Skill 整合设计。

考试规则与评分依据见 [考试流程](references/exams.md)，题目来源与更新方式见 [题库说明](references/question-bank.md)。本仓库仅包含 Skill、练习样例与合成测试数据。
