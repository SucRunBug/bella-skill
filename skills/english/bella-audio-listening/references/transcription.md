# 转写环境

需要 Python、ffmpeg/ffprobe 和一个转写后端。网页生成脚本只使用 Python 标准库。

- Apple Silicon：已有 `mlx-whisper` 环境，`--probe` 返回 `mlx: true` 后使用 `--backend mlx`。
- NVIDIA：已有 `faster-whisper` 环境，探测到 CUDA 后使用 `--backend cuda`。
- CPU：GPU 不可用、准备成本高或音频很短时使用 `--backend cpu --allow-cpu`。

优先复用已有环境。使用 uv 时可运行 `uv run --with mlx-whisper python ...`；已缓存依赖可加 `--offline`。默认优先查本机模型缓存，可用 `--model 模型路径` 指定。没有缓存时需下载公开模型。

MLX 导入提示没有 Metal 设备时，区分设备访问受限与缺包。已有其他带时间的可靠转写结果可直接生成 `lesson.json`。

默认语言 `en`，其他语言用 `--language`。已有 ASR 文件时换输出目录，脚本不会覆盖原始结果。
