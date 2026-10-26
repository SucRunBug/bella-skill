# 原文来源与完整性

本技能选取上游 [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) 的12篇产品宣传片提示词作为按需读取参考。上游固定版本为 [`92aee2f586ac0715cb3cbcb6384834f98a33383d`](https://github.com/yihui-dev/awesome-opus5-5-videos/tree/92aee2f586ac0715cb3cbcb6384834f98a33383d)，提交日期2026-10-13；本地ZIP快照下载日期为2026-10-25。

`original-prompts/*.md` 从该本地快照逐字节复制，不以摘要替代，不改写原文，不去除原有链接、重复行或不规则断行。原文中的作者署名、X原帖和已有Skillry链接完整保留。固定版本的每篇上游链接及SHA-256记录在 [presets.json](presets.json) 的 `sources`；`tests/test_prompt_integrity.py` 另存12篇预期哈希，在没有源仓库的情况下也能检测改写或丢失。

来源选择包括：brainextends-606193、annacher-433425、howdevelop-733090、ho-ba-761062、jhylee95-452427、twoclipping-496100、twoclipping-000267、moritzkremb-466494、techtactician-144474、twoclipping-747965、0xnicc0-516612、twoclipping-762046。每篇原文仅保存一份，可被多个风格引用。

[上游MIT LICENSE](original-prompts/LICENSE) 随原文逐字节复制，版权行为 `Copyright (c) 2026 yihui-dev`；其固定版本来源为 [LICENSE](https://github.com/yihui-dev/awesome-opus5-5-videos/blob/92aee2f586ac0715cb3cbcb6384834f98a33383d/LICENSE)。原文指向的品牌、产品界面、字体、歌曲、照片与视频没有随本包复制；阅读原文或使用其结构不表示已经取得那些外部素材，也不扩大当前用户授权。上游README另注明每个视频和提示词属于对应创作者，故保留逐篇署名和原帖归属。

## 新增说明与原文的界线

[提示词索引](prompt-library.md) 与 `presets.json` 的中文标题、风格归类、需求、素材依赖、技术建议、局限及节拍推算均由本技能新增，用于选择参考；不是原作者补充，也不是原视频技术、质量或制作时长的保证。

- `original_tech_requirements` 只来自原提示词中的技术路线；`styles[].suggested_tech` 是本技能建议。`remake_tech_tags` 沿用上游JSON，表示Skillry重做版技术。原文写2D时，不根据上游3d分类擅自改为三维制作。
- `original_duration.kind=exact` 表示原文规定的成片长度；`beat_derived` 表示由拍数/BPM或小节推算；`unspecified` 表示没有规定。没有从重做片测量时长，也没有原作者实际制作耗时字段。
- 全部12条上游记录的 `prompt_partial` 均为false。索引仍显式记录材料缺口：真实产品UI、未附文章、照片、封面和音轨不会因该标记而变得可用。
- 原文中的默认指标、默认品牌、素材下载和工具调用命令只是历史实例。采用何种约束以当前用户意图、可用素材和授权为准，不因读取提示词而自动执行。

本包仅收录文字和LICENSE，不包含或下载任何外部媒体。需要查看原作时，按索引中的原帖或已有Skillry链接访问；三个无单条重做页的记录保持空值，不虚构页面。
