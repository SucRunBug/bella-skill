"""Local audio inspection and deliberately conservative beat/energy estimates."""
from __future__ import annotations

from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


def binary(name: str, required: bool = True) -> str | None:
    override = os.environ.get(name.upper())
    found = shutil.which(override or name)
    if not found and override and Path(override).is_file():
        found = str(Path(override).resolve())
    if required and not found:
        raise RuntimeError(f"缺少 {name}。安装后放入 PATH，或通过 {name.upper()} 指定可执行文件。")
    return found


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    proc = subprocess.run([binary("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode:
        raise RuntimeError(f"ffprobe无法读取媒体：{proc.stderr.strip()[-1500:]}")
    return json.loads(proc.stdout)


def audio_duration(info: dict) -> float:
    streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise ValueError("媒体中没有音轨。")
    duration = float(streams[0].get("duration") or info.get("format", {}).get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("无法取得有效音频时长。")
    return duration


def analyze(path: Path) -> dict:
    info = probe(path)
    duration = audio_duration(info)
    if duration > 1800:
        raise ValueError("单次分析上限30分钟；请先指定本次要制作的歌曲片段。")
    proc = subprocess.run([binary("ffmpeg"), "-v", "error", "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "8000",
                           "-f", "s16le", "-"], capture_output=True, timeout=max(60, duration * 2))
    if proc.returncode:
        raise RuntimeError(f"音频解码失败：{proc.stderr.decode(errors='replace')[-1500:]}")
    samples = array("h")
    samples.frombytes(proc.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    hop = 160  # 20 ms; this measures energy, never identifies vocals.
    energy = [math.sqrt(sum(float(x) * x for x in samples[i:i + hop]) / len(samples[i:i + hop])) / 32768
              for i in range(0, len(samples), hop)]
    peak = max(energy, default=0)
    gate = max(.002, peak * .045)
    active = [i for i, e in enumerate(energy) if e >= gate]
    span = [active[0] * .02, min(duration, (active[-1] + 1) * .02)] if active else [0., duration]
    novelty = [0.] + [max(0., energy[i] - energy[i - 1]) for i in range(1, len(energy))]
    scored = []
    for lag in range(17, 76):  # roughly 40..176 BPM, with double/half-time ambiguity.
        count = len(novelty) - lag
        if count < lag * 4:
            continue
        dot = sum(novelty[i] * novelty[i - lag] for i in range(lag, len(novelty)))
        denom = math.sqrt(sum(x * x for x in novelty[lag:]) * sum(x * x for x in novelty[:-lag]))
        scored.append((dot / denom if denom else 0., 60 / (lag * .02)))
    candidates = []
    for score, bpm in sorted(scored, reverse=True):
        if all(abs(bpm - c["bpm"]) > 4 for c in candidates):
            candidates.append({"bpm": round(bpm, 2), "score": round(score, 4)})
        if len(candidates) == 5:
            break
    strong = max(novelty[:min(len(novelty), 600)], default=0)
    onset = next((i * .02 for i, n in enumerate(novelty[:600]) if strong > 0 and n >= strong * .65), 0.)
    secs = [{"time": i, "rms": round(sum(energy[i * 50:(i + 1) * 50]) / max(1, len(energy[i * 50:(i + 1) * 50])), 5)}
            for i in range(math.ceil(duration))]
    return {"schema_version": 1, "duration": round(duration, 6), "active_audio_span": span,
            "tempo": {"bpm": candidates[0]["bpm"] if candidates and candidates[0]["score"] > .08 else 120,
                      "offset": round(onset, 3), "provenance": "estimated", "candidates": candidates,
                      "warning": "RMS/onset自相关仅供候选：伴奏也会触发，可能半速或倍速；不是人声/乐句识别，需结合试听核对。"},
            "energy_seconds": secs, "silent_or_near_silent": not active,
            "audio": {"sha256": sha256(path), "sample_rate": next(s for s in info["streams"] if s.get("codec_type") == "audio").get("sample_rate")},
            "limitations": ["非静音范围不代表演唱范围。", "节拍候选不代替音乐听查；自由速度和节拍变化需单独编排。"]}
