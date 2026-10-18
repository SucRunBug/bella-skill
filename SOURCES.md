# 来源与整合记录

本合集将以下公开仓库的当前快照纳入四类目录，保留运行需要的脚本、参考文件、模板与现有许可证。原仓库和历史提交不作修改；此处采用单仓库快照，安装后不依赖 Git submodule 或再次克隆。

导入日期：2026-10-18。提交固定为下表，不使用无法复现的“最新版”作为来源记录。

| 合集位置 | 来源 | 导入提交 |
|---|---|---|
| `skills/english/bella-speaking-coach/` | [bella-speaking-coach](https://github.com/SucRunBug/bella-speaking-coach) | [`dc3f21dbb3fb`](https://github.com/SucRunBug/bella-speaking-coach/commit/dc3f21dbb3fbc37f3149454e58361bde7356b466) |
| `skills/english/bella-audio-listening/` | [bella-audio-listening](https://github.com/SucRunBug/bella-audio-listening) | [`6da92b917b8d`](https://github.com/SucRunBug/bella-audio-listening/commit/6da92b917b8d9b6609aa1b200f62ce7d5e2b8518) |
| `skills/research/bella-ai4s/` | [bella-AI4S](https://github.com/SucRunBug/bella-AI4S) | [`1d5e23106f03`](https://github.com/SucRunBug/bella-AI4S/commit/1d5e23106f03c2747b60a183e48f67c66ba1c8ac) |
| `skills/media/bella-ai-collage-maker/` | [bella-ai-collage-maker](https://github.com/SucRunBug/bella-ai-collage-maker) | [`22d3c3cd9b0f`](https://github.com/SucRunBug/bella-ai-collage-maker/commit/22d3c3cd9b0f150901f0b78f0710d51a957a6b5a) |
| `skills/media/talking-head-video-packaging/` | [talking-head-video-packaging](https://github.com/SucRunBug/talking-head-video-packaging) | [`2a7e5e513ce1`](https://github.com/SucRunBug/talking-head-video-packaging/commit/2a7e5e513ce11220d0789e560ea9b9600b88a4d7) |
| `skills/media/bella-writer/` | [bella-writer](https://github.com/SucRunBug/bella-writer) | [`f11458a0256f`](https://github.com/SucRunBug/bella-writer/commit/f11458a0256fb4fdf34c9780a60a964b66010161) |
| `skills/media/yanmai-video-reading/` | [yanmai-video-reading](https://github.com/SucRunBug/yanmai-video-reading) | [`9e441e71481e`](https://github.com/SucRunBug/yanmai-video-reading/commit/9e441e71481ecf311f88d1458b5720b2b2b4ff95) |
| `skills/game-3d/tripo-3d/` | [tripo-3d](https://github.com/SucRunBug/tripo-3d) | [`2162e925f1ed`](https://github.com/SucRunBug/tripo-3d/commit/2162e925f1ed88e00e66346ba2b534237b710c9c) |

## 路由参考

参考 [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/fe58a23f93203989ad6a1aef88c1cbb533491efc) 的动态候选发现、接手边界与上下文交接思路。主入口、目录脚本、集合检查与文档为本次整合编写，没有复制其商业诊断方法或完整编排实现。

## 本次适配

- 新增 `bella-skill` 主入口和技能目录，支持分类仓库与平铺安装；对缺失、名称不符和定义冲突作明确报告。
- 拼贴名称由 `gbro-collage-broll` 统一为 `bella-ai-collage-maker`；中文名称 `口播视频包装` 统一为 `talking-head-video-packaging`。旧名保留在目录别名和迁移说明里，未另外安装同内容副本。
- 统一 9 项技能的 Codex 界面元数据与调用提示。
- 文案技能允许从已有大纲、草稿或定向修改进入，不强制重跑热点和选题；原作者公开风格单独保留为可选示例，新的个人偏好写到用户项目。
- 口播包装补充 ChatCut 与配套能力的可用性检查，明确模板不随包提供；在编辑前复制时间线，需要抠像时先整条抠像再应用精剪。
- 增加合集安装说明、来源记录和自动检查；保留各成员原有的独立项目说明作为补充。
- 原仓库的 `evals/` 不进入公开运行包；Tripo 的历史机器测试证据改为固定上游提交链接，未复制运行记录。离线单元测试保留，测试用假凭据改为简短的显式测试值。

## 许可证

拼贴和视频读取目录保留各自原有 `LICENSE`。其他源仓库在导入提交中未声明许可证，本合集不将它们擅自改为统一的开源许可证。公开可访问与许可证授权是不同事项。

## 验证范围

结构、目录发现、脚本语法、引用与资源完整性可以离线验证；真实口语体验、ASR 质量、联网内容检索、科研任务效果、ChatCut 成片和付费模型生成依赖具体环境与实际任务。未用本次打包测试声称这些任务都已完成。
