# 录音处理

仅收到实际录音时使用。`scripts/transcribe_audio.py --probe` 检查 Python、ffmpeg/ffprobe、MLX Metal 与 faster-whisper CUDA/CPU。优先复用已有环境，Apple Silicon 优先 MLX/Metal，NVIDIA 优先 CUDA；GPU 不可用、安装成本高或任务很短时可选择 CPU。

```bash
python3 scripts/transcribe_audio.py --probe
python3 scripts/transcribe_audio.py "录音路径" --out "记录目录/audio/本次录音id" --backend auto
```

后端缺失时查已有虚拟环境；已有 uv 缓存可用 `uv run --offline --with mlx-whisper python ...`。优先本地缓存模型，`--model` 可指定本地模型目录。脚本不会自动下载模型或向远程服务上传录音；环境不可用就说明缺少哪项，仍可用用户提供的转写练习，不将未处理录音说成已转写。

Metal 探测因沙箱无法访问设备失败时，区分权限与依赖缺失，可使用现有授权机制重试。不要在没有探测加速后端时默认 CPU。

- 默认自动识别语言，用户主要说英语时可加 `--language en`，中文为主时可用 `zh`。中英混说可能漏词或被转成另一种语言，需要结合原音频/用户确认，不当作确定的原话。
- `asr_raw.json` 和 `asr_raw.txt` 为原始识别结果；`asr_clean.txt` 初始原样复制，由 Agent 另行修正明确识别错误。保留用户实际语法错误和原意，不能把 ASR 清洗当作语言润色。
- 听不清或可能识别错误时注明并请用户确认，再决定是否列为语言问题。整段给的是他人演讲、参考视频或播客时，不能当作用户口语表现。
- `transcription.json` 保留来源、后端、模型、语言设置与时长。相同输出目录已有原始结果时停止，换目录保留原文件。
- 转写只能给出识别内容；首版不产生专业发音评分，也不据此评定考试分数。
