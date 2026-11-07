# 内容数据与交付

`内容数据.json` 是任务状态，不是生图授权。确认字段只记录用户实际说过的确认，不能把false改true来绕过等待。

## 数据字段

| 字段 | 内容 |
|---|---|
| topic、publish_date | 本次主题、YYYY-MM-DD发布日期 |
| plan_version、stage | 如v1；proposal/approved/complete |
| mode | products或editorial |
| item_count、per_page | 默认9、3；用户可改 |
| title、title_candidates | 推荐标题、含推荐在内5个候选 |
| cover_question、caption、tags、first_comment | 本次完整文字与6–10个话题 |
| viral_logic、seasonal_hook | 爆款逻辑；节点是否相关及依据，弱相关可说明不使用 |
| visual | palette、layout、typography、ip、decorations五项具体规范 |
| approval | confirmed布尔值、plan_version、user_confirmation实际确认摘要 |
| constraints | 可选unit_budget、title_max_chars（默认20） |
| items | 各条id、name、page；商品再有spec、price、price_basis、buy_url、source_urls |
| files | plan、copy；完成时再有prompts、sources、research的相对路径 |
| images | 完成时有cover相对路径和interiors数组 |

方案阶段设置 `approval.confirmed: false`，不提供伪造成品图。`price_basis` 在有硬预算时使用 `single_purchasable_unit`，指该份实际最低起购总商品价，运费条件另注。元/克、每根折算或大盒均价不能填成该字段。

所有交付路径相对任务目录，文件内容完整可读。商品源图可以存在独立工作素材目录，最终包至少含封面、内页、方案、文案、来源表、来源说明、提示词和JSON。未请求Word时不额外生成长报告。

## 方案阶段回复

展示本次视觉规范、封面与内页文字，链接方案和发布文案，询问是否确认。不给完整成品包的假链接，不先运行图片生成工具。

## 完成阶段

先目视检查图片和核对来源，再运行 `pack_delivery.py validate`。确认版本必须与本次方案一致、stage必须complete、图片数量和每页条目分配必须匹配。CSV替代Excel时明确说明，不能把后缀改成xlsx。

`package` 只把清单内文件及JSON放入压缩包，不扫描整个工作区。它不联网，不生成图片，不修改批准状态，也不替你核实网络事实。通过脚本不等于已验证最新价格或图内每个字。
