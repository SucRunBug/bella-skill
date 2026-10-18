# 数据格式

UTF-8 JSON：

```json
{
  "version": 1,
  "title": "Listening practice",
  "sentences": [
    {"id": "s001", "start": 0.5, "end": 2.8, "en": "Let's take a walk.", "zh": "我们去散步吧。"}
  ]
}
```

句子标识不重复；起止时间以秒计，满足 `0 ≤ start < end ≤ 音频时长`，按时间排序且不重叠。英文保留原话，中文不能为空。

可选：`subtitle`、`source`、真实 HTTP/HTTPS `sourceUrl`；句子可用 `review: true` 标记存疑。生成脚本自动填写材料标识、实际时长和内嵌音频。
