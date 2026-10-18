# 安装与检查

## 完整安装

```bash
npx -y skills add SucRunBug/bella-skill -g --all
```

安装器会发现 9 个技能，包括主入口和 8 个成员。要指定宿主：

```bash
npx -y skills add SucRunBug/bella-skill -g --skill '*' --agent codex -y
npx -y skills add SucRunBug/bella-skill -g --skill '*' --agent claude-code -y
```

这是不同宿主的可选命令，不需要全部执行。安装后重开会话，使用 `$bella-skill` 描述任务；宿主的命令选择器可能显示 `/bella-skill`，以实际宿主支持的形式为准。也可让 Agent 直接读取已安装主入口的 `SKILL.md`。

## 按需安装

```bash
# 英语两项 + 主入口
npx -y skills add SucRunBug/bella-skill -g --skill bella-skill bella-speaking-coach bella-audio-listening

# 仅科研
npx -y skills add SucRunBug/bella-skill -g --skill bella-ai4s

# 查看可发现的技能
npx -y skills add SucRunBug/bella-skill --list
```

部分安装时，主入口会列出未安装成员。它只选择真正可用的技能，不自动下载缺失项。

## 直接读取仓库

```bash
git clone https://github.com/SucRunBug/bella-skill.git
cd bella-skill
python3 tools/check_collection.py
python3 skills/bella-skill/scripts/list_skills.py --check
```

也可以让 Agent 直接读取仓库中的 `skills/bella-skill/SKILL.md`。不要只复制这一份 Markdown；主入口还需要自己的 scripts 和 references，执行专项任务还需要相应的完整成员目录。

## 旧版本与迁移

| 原调用名称 | 当前名称 |
|---|---|
| `gbro-collage-broll` | `bella-ai-collage-maker` |
| `口播视频包装` | `talking-head-video-packaging` |
| 其他六项 | 沿用原 frontmatter 名称，包括 `bella-ai4s` |

旧名用于解释历史请求，新包只注册当前名称。原来的独立仓库不受本合集发布影响。若同时安装了两个版本，优先检查宿主实际加载的是哪一个；不要自动删除旧目录或用户的练习记录、风格档案、科研记忆和 3D 凭据。

源仓库内的分类层级用于维护；安装器通常把各技能放到同一个 skills 目录。主入口兼容两种布局，也会报告名称不匹配和定义冲突。

## 项目数据与环境

安装包包含规则和工具，不包含作者电脑上的音视频、学习记录、科研数据、凭据和写作档案。运行产物写到用户项目中，具体位置依各技能说明和用户要求。

各成员 README 保留原独立项目的详细说明；本页的合集安装方式为统一入口。需要 Python、媒体工具、ASR、ChatCut 或 Tripo 时，在相应任务开始时检查，不为安装合集而预装所有环境。
