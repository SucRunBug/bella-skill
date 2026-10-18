# 近期题库检索与缓存

## 何时查新

首次考试训练、用户要“最新／最近／当季”、当前快照超过七天、考试版本／地区／来源适用时段改变时，使用当前 Agent 可用的联网搜索和网页读取工具。七天是本 skill 的检索默认值，不是考试官方周期，也不创建后台定时任务。用户只要快速用旧题练习时，可直接用注明日期的缓存。

1. 根据用户时区的今天、考试日期与类别，查官方题型和样题。优先 IELTS、ETS、Pearson 官网；原页面有更新则使用更新内容。
2. IELTS 近期话题查两个以上公开来源，按来源实际披露区分考生回忆、机构汇编和预测。PTE／TOEFL 优先官方练习与最新格式素材；找不到可信近期回忆时明确“未取得近期回忆题”，不生成一份假真题库。
3. 打开来源原文核对，不用搜索摘要直接建库。保存页面实际更新时间（有则记）、检索日期、适用时段、地区和题型。页面今天被访问不等于每道题今天被考过；没有具体考试／回忆日期时留空。
4. 只整理本次训练够用的题目和话题。官方样题、公开回忆、按话题改编及原创题分别标记。保留来源链接；不批量搬运整套付费材料。无法读取的来源记录为访问失败，不称已取得。
5. 用 `question_bank.py save` 缓存快照。明确告知“截至哪天检索、来自哪里、覆盖什么”，不能保证命中、完整或等于官方在用题库。

可从以下实际读过的入口查起，使用前核对页面是否仍适用：

- [IELTS 官方口语形式与样题入口](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking)
- [IELTSVega 2026年9至10月公开话题汇编](https://www.ieltsvega.com/blog/recent-ielts-speaking-questions-september-october-2026)
- [Joe Speaking 2026年9至12月公开话题汇编](https://joespeaking.com/ielts-speaking-questions/2026-sep-dec)
- [PTE Academic 当前题型](https://www.pearsonpte.com/pte-academic/test-format/speaking-writing/)、[官方练习素材](https://www.pearsonpte.com/teachers/pte-academic-updates-partners-and-teachers/)
- [TOEFL 当前口语题型](https://www.ets.org/toefl/test-takers/ibt/about/content/speaking.html)

两个第三方列表有重合，仅说明两处收录；转载或共同上游不算独立核实。若只是同一话题下自行设计了新问题，应标 `adapted`，不能说题干是原题。

## 本地快照

脚本使用标准库。缓存位置是学习记录根目录下的 `question-banks/`；不写进用户的练习 session。随 skill 附有 `references/starter-bank.json`，它是 **2026年10月15日核对的少量话题与原创练习示例**，使用它并不表示刚完成联网更新，也不是全量题库。

```bash
python3 scripts/question_bank.py save --root "output/speaking-coach" --input "bank-snapshot.json" --as-of 2026-10-15
python3 scripts/question_bank.py read --root "output/speaking-coach" --format ielts-speaking --as-of 2026-10-15 --task part2 --limit 5
# 无缓存时可直接读随 skill 的样例，不冒充最新检索
python3 scripts/question_bank.py read --file "本skill路径/references/starter-bank.json" --format ielts-speaking --as-of 2026-10-15 --limit 5
```

`read` 返回来源、检查日期、缓存是否需要更新及题目类别，给 Agent 用。指定题型时选择含该题型的最近快照；最新快照缺这一题型时仍可找到较早的有效快照。不要在模考出题时把隐藏素材、示范或整套后续题目一起展示给用户。

## 快照格式

顶层字段：`version: 1`、`id`、`checked_on`（ISO 日期）、`sources` 列表、`questions` 列表，以及可选 `search_log`。一个快照可含多个考试，但每题必须有 `format_id` 和合法 `task`，读取时严格筛选。

来源项：`id`、`url`、`title`、`kind`（`official` / `third_party`）、`checked_on`；可选 `published_on`、`updated_on`、`period`、`region`。页面明确给出的适用时段可另存 `applicable_from`、`applicable_until`；这是来源声明，不表示官方保证。检索词与访问失败可放 `search_log`；不能把来源没有给出的日期补成今天。每题来源的实际核对日期用于判断是否过期，不能只改顶层日期给旧题“续新”。用户给考试日期时，read 加 `--for-date 日期` 检查来源时段是否适用，不能拿已过期的话题冒充该次考试的近期题库。

题目项：`id`、`format_id`、`task`、`topic`、`prompt`、`provenance`、`source_ids`。可选 `reported_on`、`materials`、`stimulus_text`、`notes`。

| provenance | 含义 |
| --- | --- |
| official_sample | 已实际读取的官方公开样题，题干未改写 |
| reported | 第三方公开收录的回忆／汇编题，未经官方确认 |
| adapted | 依据来源话题重新组织的练习题，题干和提示为自制 |
| generated | 根据核对过的考试形式创作的模拟题，来源仅用于形式核对 |

`official_sample` 的关联来源必须是官方；`reported` 至少关联一个第三方来源。题干修改过就用 `adapted`。`materials` 记录音频／图片引用，缺失素材的相关题不用于声称还原完整模考。`stimulus_text` 是教练或播放工具使用的内容，听后复述的考生首答前不显示它。

快照 ID 是历史引用。重复保存相同快照不增加副本；同 ID 内容有变时换新 ID，以免旧练习引用的题目被覆盖。用户无法联网时可以练缓存与原创题，但明确显示核对日期与范围。
