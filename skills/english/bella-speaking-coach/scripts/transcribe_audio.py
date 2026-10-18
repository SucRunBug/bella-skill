#!/usr/bin/env python3
"""Transcribe learner audio locally, retaining raw ASR and a separate editable copy."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def probe():
    info = {"python": sys.executable, "architecture": platform.machine(),
            "ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")), "backends": {}, "errors": {}}
    if importlib.util.find_spec("mlx_whisper"):
        try:
            import mlx.core as mx
            info["backends"]["mlx"] = bool(mx.metal.is_available())
        except Exception as exc:
            info["errors"]["mlx"] = str(exc)
    if importlib.util.find_spec("faster_whisper"):
        try:
            import ctranslate2
            info["backends"]["cuda"] = ctranslate2.get_cuda_device_count() > 0
            info["backends"]["cpu"] = True
        except Exception as exc:
            info["errors"]["faster_whisper"] = str(exc)
    return info


def local_model(backend, specified):
    if specified:
        path = Path(specified).expanduser().resolve()
        if not (path / "config.json").is_file():
            raise ValueError("--model requires a local model directory containing config.json")
        return path
    hub = Path.home() / ".cache/huggingface/hub"
    names = (["models--mlx-community--whisper-small-mlx", "models--mlx-community--whisper-medium-mlx"]
             if backend == "mlx" else ["models--Systran--faster-whisper-small", "models--Systran--faster-whisper-medium"])
    for name in names:
        for snapshot in sorted((hub / name / "snapshots").glob("*")):
            if (snapshot / "config.json").is_file():
                return snapshot
    raise ValueError("No cached local model found; supply --model. No model was downloaded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="?")
    parser.add_argument("--out")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--backend", choices=["auto", "mlx", "cuda", "cpu"], default="auto")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--language", default="auto")
    args = parser.parse_args()
    info = probe()
    if args.probe:
        return info
    if not args.audio or not args.out:
        parser.error("audio and --out are required")
    backend = args.backend
    if backend == "auto":
        backend = next((name for name in ("mlx", "cuda") if info["backends"].get(name)), None)
        if backend is None and args.allow_cpu and info["backends"].get("cpu"):
            backend = "cpu"
    if not backend or not info["backends"].get(backend):
        raise ValueError("Requested acceleration/backend unavailable; inspect --probe in an existing ASR environment")
    if backend == "cpu" and not args.allow_cpu:
        raise ValueError("CPU fallback requires --allow-cpu after probing available acceleration")
    if not info["ffmpeg"] or not info["ffprobe"]:
        raise ValueError("ffmpeg and ffprobe are required")
    source = Path(args.audio).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    out = Path(args.out).expanduser().resolve()
    if out == source.parent:
        raise ValueError("Use a separate output directory to preserve the source")
    # A new folder preserves every previous raw result, even if a preceding run was incomplete.
    model = local_model(backend, args.model)
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", str(source)], text=True).strip())
    out.mkdir(parents=True, exist_ok=False)
    wav = out / "asr_audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    language = None if args.language == "auto" else args.language
    if backend == "mlx":
        import mlx_whisper
        raw = mlx_whisper.transcribe(str(wav), path_or_hf_repo=str(model), language=language,
                                    word_timestamps=True, condition_on_previous_text=False, verbose=False)
    else:
        from faster_whisper import WhisperModel
        engine = WhisperModel(str(model), device="cuda" if backend == "cuda" else "cpu",
                              compute_type="float16" if backend == "cuda" else "int8", local_files_only=True)
        segments, metadata = engine.transcribe(str(wav), language=language, word_timestamps=True,
                                               condition_on_previous_text=False)
        rows = []
        for segment in segments:
            row = segment._asdict()
            row["words"] = [w._asdict() for w in segment.words or []]
            rows.append(row)
        raw = {"text": "".join(s["text"] for s in rows), "segments": rows, "language": metadata.language}
    text = raw.get("text", "").strip()
    (out / "asr_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "asr_raw.txt").write_text(text + "\n", encoding="utf-8")
    (out / "asr_clean.txt").write_text(text + "\n", encoding="utf-8")
    metadata = {"source": str(source), "backend": backend, "model": str(model), "duration": duration,
                "requested_language": args.language, "detected_language": raw.get("language"),
                "clean_copy_reviewed": False}
    (out / "transcription.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"folder": str(out), "backend": backend, "duration": duration, "raw_saved": True, "clean_copy_reviewed": False}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
