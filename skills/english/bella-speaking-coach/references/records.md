# 学习记录格式与命令

## 文件与身份

`coach_records.py` 只使用标准库，Python 3.10+ 可运行。默认档案为记录目录内的 `records.json`。脚本保存时验证格式并原子替换；数据损坏或版本不支持时停止，不用空档案覆盖。读命令不会创建空记录。

Agent 将本次实际内容写成一个临时 session JSON，调用保存；不要直接覆盖 `records.json`。同一练习修改或补充时沿用 `id`；保存是整份 session 替换，先读旧记录，保留仍需保留的字段。录音/文件导入使用 `fingerprint` 生成 `source.key`，相同来源再次保存会更新原 session，不新增练习。

新 session ID 可用 UUID 或日期加短随机串，日期使用用户时区的 ISO 8601 时间（必须带时区）。表达 ID 默认根据表达和语境含义生成；如果来自已有词句库，沿用返回的 ID。单次回考的 attempt ID 在该 session 内固定，避免同次补充重复累计。

## Session 格式

以下是假想练习示例，不可直接作为用户实际数据保存：

```json
{
  "id": "practice-20261012-demo",
  "started_at": "2026-10-12T18:00:00+08:00",
  "mode": "topic",
  "input_type": "text",
  "topic": "昨天的一件事",
  "source": {"coverage": "complete"},
  "turns": [
    {"id": "t1", "role": "user", "text": "Yesterday I go to the park.", "stage": "initial"},
    {"id": "t2", "role": "assistant", "text": "Yesterday I went to the park. 再讲一遍昨天做的事。", "stage": "help"},
    {"id": "t3", "role": "user", "text": "Yesterday I went to the park.", "stage": "retry"}
  ],
  "feedback": [
    {"id": "f1", "turn_id": "t1", "kind": "error", "tag": "past-tense", "original": "Yesterday I go to the park.", "suggestion": "Yesterday I went to the park.", "reason": "昨天的动作使用过去式。", "retry_turn_id": "t3"}
  ],
  "expressions": [
    {"phrase": "went to the park", "meaning": "去过公园，描述过去的动作", "selection": "user", "example": "I went to the park yesterday.", "notes": "用户愿意再练过去的经历。"}
  ],
  "attempts": [
    {"id": "a1", "phrase": "went to the park", "meaning": "去过公园，描述过去的动作", "prompt": "再讲一遍昨天做的事。", "answer_turn_id": "t3", "result": "with_hint", "hint": "answer", "transfer": false}
  ],
  "next_task": "用过去式讲一次不同的经历。"
}
```

- `mode`：`topic`、`description`、`retell`、`review`、`expression` 或 `exam`。
- `input_type`：`voice`、`audio`、`text` 或 `transcript`。`voice` 仅用于真实语音互动；粘贴转写为 `transcript`。
- `source`：`coverage` 为 `complete`、`partial` 或 `summary`；可加 `key`（文件指纹/稳定来源 ID）、`reference`、`asr_raw`、`asr_clean`。录音与转写导入必须给稳定 `key`；文件用指纹命令，无文件的粘贴稿也可指纹化保存的原文文件。复练录音是新的回答，作为原 session 的复练 turn 补入，不覆盖最初来源。
- `turns`：实际可获得的发言。角色是 `user` 或 `assistant`；`stage` 可为 `initial`、`dialogue`、`help`、`retry`、`review`。无法获得 AI 原话时不要编造，不混淆转写说话人。
- `feedback`：`original` 必须能在对应用户 turn 中定位。`kind` 为 `error`、`optional` 或 `uncertain`；只有 `error` 计入重复问题。用户没复练时省略 `retry_turn_id`。
- `expressions`：需要保存时加入，`phrase` 与 `meaning` 必填。`selection` 为 `user`（用户明确选择）、`coach`（AI 推荐）或 `unspecified`（未标注，兼容旧数据）；按实际来源填写。`example` 是示例，不能单凭它认定用户会用。可带现有 `id`，同词不同含义可分别保存。用户不记词时用空列表。报告区分当次作答与当前跨次状态。
- `attempts`：目标用 `expression_id`，或用 `phrase` 加 `meaning` 引用。`answer_turn_id` 指向实际用户回答；没有回答不新增 attempt。`hint` 为 `none`、`clue`、`answer`，`result` 为 `independent`、`with_hint`、`retry`；提示后成功必须为 `with_hint`，`independent` 必须 `hint: none`。`transfer` 标记是否在不同情境使用。
- `next_task`：具体可执行的一项；没安排时可用空字符串。

`feedback`、`expressions`、`attempts` 可省略或为空。脚本验证身份、发言引用与状态的一致性；回答是否正确、是否独立及提示量由 Agent 根据真实对话判断，不由关键词匹配打分。

## 命令

下面使用 `python3 scripts/coach_records.py`，实际应解析成本 skill 的绝对脚本路径。根目录可换成用户指定位置。

```bash
# 最近记录、偏好、表达库与问题统计；不会自动创建目录
python3 scripts/coach_records.py context --root "output/speaking-coach" --limit 5
# 读取指定练习再补充，以免整份替换丢失原内容
python3 scripts/coach_records.py context --root "output/speaking-coach" --session "实际session-id"
# 文件指纹用于避免重复导入
python3 scripts/coach_records.py fingerprint "原始记录或录音路径"
# 保存实际练习，返回记录路径与实际 session ID
python3 scripts/coach_records.py save --root "output/speaking-coach" --input "session.json"
# 推荐复习条目；输出给 Agent，先别把示例展示给用户
python3 scripts/coach_records.py review --root "output/speaking-coach" --limit 3
# 按用户时区的日期筛选实际记录
python3 scripts/coach_records.py context --root "output/speaking-coach" --since 2026-10-05 --until 2026-10-12
# 保存用户明确表达的偏好，JSON 是局部更新
python3 scripts/coach_records.py profile --root "output/speaking-coach" --input "preferences.json"
# 导出事实记录；再依据记录给简短复盘，不虚构成长结论
python3 scripts/coach_records.py report --root "output/speaking-coach" --out "output/speaking-coach/练习记录.md"
# 用户请求修改释义、例句或笔记；ID 沿用原条目
python3 scripts/coach_records.py expression --root "output/speaking-coach" --id "实际expression-id" --input "expression-edit.json"
# 用户请求删除词句库条目，原始练习仍保留；不会在重导入时又出现
python3 scripts/coach_records.py expression --root "output/speaking-coach" --id "实际expression-id" --delete
```

可编辑字段为 `meaning`、`example`、`notes`；更换表达本身时新增另一条并按用户意思删除旧条目。profile 仅保存用户要求或明确给出的目标与偏好，不把推断水平写成自述。

`context` 默认只返回最近五次匹配的练习与二十项表达。返回的 `matching_sessions`、`total_expressions` 大于实际列表长度时，增大 `--limit`、`--library-limit` 继续读取，再作完整范围的总结。问题统计覆盖全部匹配的练习；表达库是跨期状态，周复盘中的当周表现须依据筛选出的 session 作答。

状态由实际 attempts 重建：无回答是 `pending`；最近一次分别对应 `independent`、`with_hint`、`retry`。一次成功不会成为永久“已掌握”。回考排序优先后三种中需要帮助的状态，再按最近复习时间从旧到新；剩余条目可由 Agent 做少量随机抽查。删除仅移出表达库，不删除练习原文；用户请求删除原始记录时另按其明确范围处理。

## 首次偏好与多考试设置

首次明确选择用 `profile` 保存，之后读取已有偏好，不反复问入口。用户没作选择前不写默认值。以下是设置示例，不是当前用户已选的偏好：

```json
{
  "practice_goal": "exam",
  "active_exam": "ielts-speaking",
  "exam_preferences": {
    "ielts-speaking": {"practice": "drill", "target_score": "口语7", "exam_date": "2026-11-08"},
    "pte-academic-2025": {"practice": "drill", "target_score": "待定"}
  }
}
```

`practice_goal` 为 `daily` 或 `exam`。`active_exam` 使用 [版本表](exam-formats.json) 中的 ID。`exam_preferences` 按考试分别局部合并，更新一个目标不会清掉另一个考试；切回日常也保留它们。目标分和日期均可省略。其他既有反馈偏好字段继续使用，不用改写旧档案。

## 考试 Session 扩展

`mode: exam` 时必须给 `exam`，例如：

```json
{
  "format_id": "ielts-speaking",
  "practice": "mock",
  "scope": "task",
  "completed": true,
  "fidelity": "untimed",
  "rules_checked_on": "2026-10-15",
  "bank_id": "starter-20261015",
  "question_ids": ["ielts-waiting-card"],
  "timing": {"method": "none"},
  "answers": [
    {"question_id": "ielts-waiting-card", "task": "part2", "answer_turn_id": "t1", "help_used": false}
  ],
  "assessment": "仅依据首答评价内容组织、用词和语法；没有音频，不评发音或实际口语流利度，也不计算完整band。"
}
```

这是 session 内的 `exam` 对象，仍需外层实际日期、话题、输入方式和发言。`answers` 仅关联实际用户首答；同一题的后续重说留在普通 retry turn，不能覆盖首答或补高模考表现。无作答的题不填一条假答案。

- `practice`：`drill` 为题库练习，`mock` 为模拟。
- `scope`：`task` 为专项，`speaking_section` 才是完整口语部分，均不表示做完听说读写全套考试。
- `completed`：实际完成声明范围时为 true；提前退出或尚在作答时 false。完整口语的 true 会核对所有所需题型，TOEFL 还核对七道复述与四道访谈，避免把单项标成全节完成。
- `fidelity`：`voice_timed` 要有真实语音／录音、宿主计时、`elapsed_seconds` 和 `evidence`（实际计时依据）；自行计时为 `self_timed`，且 timing.method 为 `self`；没有实测计时为 `untimed`。模考里用了提示或示范则为 `assisted`。
- `bank_id` 与 `question_ids` 对应实际使用的缓存快照和题目；临时自创题也先存带 `generated` 来源的快照。
- `assessment` 是注明证据与未评估项目的文字反馈，不是脚本自动计算的官方分数。

```bash
python3 scripts/coach_records.py context --root "output/speaking-coach" --goal daily
python3 scripts/coach_records.py context --root "output/speaking-coach" --exam ielts-speaking --limit 20
python3 scripts/coach_records.py report --root "output/speaking-coach" --exam pte-academic-2025 --out "output/speaking-coach/PTE练习记录.md"
```

`--exam` 严格按版本筛选练习和错误统计。表达库仍可跨场景共享；需要判断本考试的表现时，必须回到筛选后的实际首答，不把跨场景词句状态当作考试成绩。

保存考试记录前，先把实际使用的题库快照放到同一记录根目录的 `question-banks/`。脚本会核对快照存在、题目属于该考试、答题题型与题目一致；不得用另一个考试的题目 ID 占位。用户暂不保存学习记录时可以只出题，不要求先建立档案。
