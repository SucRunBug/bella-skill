# 英语听力与双语听读

本目录属于 [bella-skill](https://github.com/SucRunBug/bella-skill) 合集。安装完整合集：

```bash
npx -y skills add SucRunBug/bella-skill -g --all
```

也可用 `--skill bella-audio-listening` 代替 `--all` 只装本项。安装后可直接调用 `$bella-audio-listening`。原仓库独立安装说明保留在下方。

---

# bella-audio-listening

将英语音频生成自带原声的离线 HTML 听读网页。

提供音频后调用：

```text
使用 $bella-audio-listening，把这段音频生成双语听读网页。
```

支持逐句播放、中英对照、语速、循环、生词笔记及备份恢复。转写与翻译由 Agent 完成，页面由脚本生成。

环境：Python、ffmpeg，以及 MLX Whisper 或 faster-whisper；已有带时间的转写结果也可复用。
