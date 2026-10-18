---
name: bella-audio-listening
description: 将英语音频生成离线双语听读网页。用户上传音频，需要逐句听原声、跟读或记录生词时使用。
---

# bella-audio-listening

输出一份自带原声音频的 HTML，支持中英对照、逐句播放、语速与循环、生词笔记和备份。

## 流程

脚本路径相对本 skill 根目录，输出默认放在 `output/listening-page/<材料名>/`。

1. 检查转写后端，使用已有环境；优先 MLX/Metal 或 CUDA。后端不可用时才读取 [环境说明](references/transcription.md)。

```bash
python scripts/transcribe_audio.py --probe
python scripts/transcribe_audio.py "音频路径" --out "工作目录" --backend auto
```

2. 校正 `lesson.draft.json` 的英文，按语义分句并填写中文，保存为 `lesson.json`。字段见 [数据格式](references/lesson-schema.md)。时间依据逐词结果核对，不按字数均分。保留原意、原始 ASR 和另存的 `asr_clean.txt`；听不清的句子设置 `review: true`。

3. 生成网页：

```bash
python scripts/build_page.py --audio "工作目录/audio.mp3" --lesson "工作目录/lesson.json" --out "工作目录/听读网页.html"
```

4. 验证首、中、末句播放，记词后刷新回看，以及备份恢复。交付网页链接和未核实项。

只播放输入原声；词典释义由用户选择并保存。句子时间在生成时处理。默认本地生成，不上传音频到第三方。
