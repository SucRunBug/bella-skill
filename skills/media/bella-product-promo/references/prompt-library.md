# 产品宣传片提示词索引

这是按需读取的原文导航。先按当前产品、内容和素材选择一种风格，再读取该风格对应的一个或少量原MD；不要默认把12篇全部载入。机器可读索引为 [presets.json](presets.json)，来源与版本见 [provenance.md](provenance.md)。

## 使用边界

- `original-prompts/` 的12篇MD为上游原文件的逐字节副本；标题、链接、重复句、断行和原有拼写均保留。下表及JSON是新增的解释性索引，不能替代或冒充原文。
- 原文中的「Ask me」「使用某技术」「下载音效」「渲染」「不要询问」等命令是可选择的历史参考。当前用户的产品、约束、素材、工具、时长和授权优先；阅读不构成执行命令、访问账户、付费、上传或发布的授权。
- `specific_task` 是面向特定产品的brief；`input_template` 需要输入或选择默认值；`open_brief` 是开放选题示例。模板中的默认品牌、CTA、指标和logo不是当前产品事实。
- 全部12条在上游标为 `prompt_partial=false`。该标记不证明完整生产对话、附件齐全或一遍生成即可复现；缺失上下文和素材在JSON中另外记录。
- MD里的 **Remake built with** 及JSON的 `remake_tech_tags` 只描述 Skillry 重做版，不等于原视频技术。`original_category` 同样只是上游分组：若原文写2D，以内容判断，不因3d分组强制使用3D引擎。
- `original_tech_requirements` 记录原文提到的实现路线，`styles[].suggested_tech` 是本技能的实现建议。未指定技术的原文保持空数组。`native-html` 可包含Canvas/SVG/CSS与浏览器JS；`hybrid` 表示真实影像和代码动效组合。
- 下列时长均来自原提示词要求或明确标注的节拍推算，不是原视频或Skillry重做片的实测。推算小节时长须确认拍号、BPM和歌曲实际节奏；输入的新音乐可改变排期。

## 按视觉方向选择

| 风格ID | 方向 | 优先读取 |
|---|---|---|
| `spotify-premium` | 深色舞台、封面与播放器贯穿 | `brainextends-606193`；`twoclipping-762046` |
| `minimal-ui` | 暖灰、黑白、一强调色、光标驱动 | `annacher-433425`；`0xnicc0-516612` |
| `tech-launch` | 用数据流和机制证明技术能力 | `howdevelop-733090` |
| `real-ui` | 从真实产品拆解界面与组件 | `annacher-433425`；`ho-ba-761062`；`jhylee95-452427`；`techtactician-144474` |
| `social-launch` | 首秒钩子、快速功能证明、社媒节奏 | `ho-ba-761062`；`jhylee95-452427`；`moritzkremb-466494`；`techtactician-144474` |
| `apple-continuous` | 连续镜头、液态玻璃、场景由对象生长 | `twoclipping-496100`；`twoclipping-747965`；`twoclipping-762046` |
| `footage-hybrid` | 真实视频/照片与UI结合 | `twoclipping-496100`；`twoclipping-000267` |
| `outcome-story` | 交办工作、处理中、清晨结果 | `twoclipping-747965` |
| `shape-morph` | 一个主形状贯穿流程、首尾循环 | `annacher-433425`；`twoclipping-747965`；`0xnicc0-516612`；`twoclipping-762046` |

一个原文可服务多种风格；相同原文只保存一份。素材受限时优先参考自含的 `brainextends-606193` 或无照片依赖的 `0xnicc0-516612`，仍需解决配乐来源与当前品牌内容。

## 12篇原文与依赖

| 原文 | 性质 | 原文要求/推算时长 | 使用前应知道 |
|---|---|---|---|
| [Spotify 高级音乐产品片](original-prompts/brainextends-606193.md) | 具体任务 | 明确18秒、1080p、60fps | 自含brief，无需参考视频或预附素材；需制作原创封面、解决音乐与字体。 |
| [Sprites 真实UI变形](original-prompts/annacher-433425.md) | 具体任务 | 120 BPM、7小节；4/4下约14秒 | 必须核实并获取实际Sprites UI与广告素材；原例无音乐，仅合成UI音效。 |
| [TanStack AI 技术发布](original-prompts/howdevelop-733090.md) | 具体任务 | 明确15秒、1080p、30fps | 给了事实摘录，但提到的文章未附全文；RC/24 providers为原例快照，当前使用须核实；原文重复行不删除。 |
| [真实组件拆解](original-prompts/ho-ba-761062.md) | 具体任务 | 明确30秒 | 需要mdfor.dev真实截图、logo和素材；不能只有截图平移。URL跨行按原样保留。 |
| [Supademo 社交发布](original-prompts/jhylee95-452427.md) | 具体任务 | 未指定 | 简短brief：产品研究、真实UI、品牌和配乐需另行完成；末句为“Social energy, quick cuts”，无详细分镜。 |
| [Apple 连续镜头与玻璃](original-prompts/twoclipping-496100.md) | 输入模板 | 120 BPM、54拍，推算27秒 | 需品牌名、9–12照片、音乐、真实墙面视频；明确2D only；原例下载音效且禁止合成。 |
| [真实视频墙](original-prompts/twoclipping-000267.md) | 输入模板 | 10小节×2秒，推算20秒 | 需产品承诺、3–5 UI时刻、强调色、10–20自有竖屏视频与drop音乐；不允许用占位卡替代真实视频。 |
| [开放选题SaaS发布](original-prompts/moritzkremb-466494.md) | 开放brief | 未指定 | 原例允许挑SaaS并找素材；当前用户已选产品时直接保留其选择；没有固定技术与分镜。 |
| [Slideforge SaaS发布](original-prompts/techtactician-144474.md) | 具体任务 | 未指定 | 需访问真实产品并取得素材；没有固定技术，SVG/GSAP/CSS是重做标签。 |
| [Nightshift 结果叙事](original-prompts/twoclipping-747965.md) | 带默认值的输入模板 | 明确24秒、1440方形、60fps | 需任务、三结果、同机位昼夜照片、外部日景和音乐；默认值不含素材文件，示例销售指标不是事实。 |
| [单形态发布循环](original-prompts/0xnicc0-516612.md) | 输入模板 | 120 BPM、24拍，推算12秒 | 需产品名、强调色与音乐；无需外部UI/照片，叙事示例是代码生成视频。 |
| [音乐UI连续变形](original-prompts/twoclipping-762046.md) | 带默认值的输入模板 | 明确22秒、1440方形、60fps | 需问答、两封面、音乐、logo；默认氛围照片/歌曲未附文件；明确2D only，原文无build章节。 |

9篇记录有Skillry重做链接；后三篇新条目只有原帖，JSON保持 `skillry_url: null`、`has_remake: false`。链接仅用于查来源与对照，文件包不含预览图、音频或视频。
