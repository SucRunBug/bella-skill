#!/usr/bin/env python3
"""Prepare an uploaded audio file and word-timed draft for the listening-page skill."""
import argparse
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def probe():
    result = {"architecture": platform.machine(), "python": sys.executable,
              "ffmpeg": bool(shutil.which("ffmpeg")), "backends": {}}
    if importlib.util.find_spec("mlx_whisper"):
        try:
            import mlx.core as mx
            result["backends"]["mlx"] = bool(mx.metal.is_available())
        except Exception as exc:
            result["backends"]["mlx_error"] = str(exc)
    if importlib.util.find_spec("faster_whisper"):
        import ctranslate2
        result["backends"]["cuda"] = ctranslate2.get_cuda_device_count() > 0
        result["backends"]["cpu"] = True
    return result


def local_model(backend):
    hub = Path.home() / ".cache/huggingface/hub"
    names = (["models--mlx-community--whisper-small-mlx"] if backend == "mlx" else
             ["models--Systran--faster-whisper-small", "models--Systran--faster-whisper-medium"])
    for name in names:
        snapshots = hub / name / "snapshots"
        if snapshots.exists():
            for path in sorted(snapshots.iterdir()):
                if (path / "config.json").exists():
                    return str(path)
    return "mlx-community/whisper-small-mlx" if backend == "mlx" else "small"


def sentence_draft(raw, duration):
    words = [word for segment in raw["segments"] for word in segment.get("words", [])
             if str(word.get("word", "")).strip()]
    if not words:
        raise ValueError("No word timestamps returned. Use an ASR backend with word timestamps.")
    groups, group = [], []
    for word in words:
        group.append(word)
        tail = word["word"].strip().rstrip('\"\u201d\u2019\')')
        abbreviation = tail.lower() in {"mr.", "mrs.", "ms.", "dr.", "prof.", "e.g.", "i.e."}
        if (re.search(r"[.!?]$", tail) and not abbreviation) or len(group) >= 65:
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    rows = []
    for i, group in enumerate(groups):
        start = max(0, float(group[0]["start"]) - .06)
        end = min(duration, float(group[-1]["end"]) + .1)
        if i + 1 < len(groups):
            following = float(groups[i + 1][0]["start"])
            end = min(end, (float(group[-1]["end"]) + following) / 2)
        if rows:
            start = max(start, rows[-1]["end"])
        if end <= start:
            raise ValueError(f"Invalid word timing near sentence {i + 1}; review the ASR output.")
        text = "".join(w["word"] for w in group).strip()
        rows.append({"id": f"s{i+1:03}", "start": round(start, 3), "end": round(end, 3),
                     "en": text, "zh": ""})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", nargs="?")
    parser.add_argument("--out")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--backend", choices=["auto", "mlx", "cuda", "cpu"], default="auto")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--language", default="en")
    parser.add_argument("--title")
    args = parser.parse_args()
    info = probe()
    if args.probe:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    if not args.audio or not args.out:
        parser.error("audio and --out are required")
    backend = args.backend
    if backend == "auto":
        backend = next((b for b in ("mlx", "cuda") if info["backends"].get(b)), None)
        if backend is None and args.allow_cpu and info["backends"].get("cpu"):
            backend = "cpu"
    if not backend or not info["backends"].get(backend):
        raise RuntimeError("No requested ASR backend is available. Check --probe and choose a compatible Python environment.")
    source = Path(args.audio).resolve()
    out = Path(args.out).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "asr_raw.json").exists():
        raise FileExistsError("Use a new output folder; existing raw ASR is never overwritten.")
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "default=noprint_wrappers=1:nokey=1", str(source)], text=True).strip())
    wav = out / "asr_audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    playback = out / "audio.mp3"
    if source.suffix.lower() == ".mp3":
        shutil.copyfile(source, playback)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vn", "-c:a", "libmp3lame",
                        "-b:a", "128k", str(playback)], check=True)
    model = args.model or local_model(backend)
    if backend == "mlx":
        import mlx_whisper
        raw = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model, language=args.language,
                                    word_timestamps=True, condition_on_previous_text=False, verbose=False)
    else:
        from faster_whisper import WhisperModel
        engine = WhisperModel(model, device="cuda" if backend == "cuda" else "cpu",
                              compute_type="float16" if backend == "cuda" else "int8")
        segments, _ = engine.transcribe(str(wav), language=args.language, word_timestamps=True,
                                        condition_on_previous_text=False)
        rows = []
        for segment in segments:
            row = segment._asdict()
            row["words"] = [w._asdict() for w in segment.words or []]
            rows.append(row)
        raw = {"text": "".join(s["text"] for s in rows), "segments": rows, "language": args.language}
    (out / "asr_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "asr_raw.txt").write_text(raw["text"].strip() + "\n", encoding="utf-8")
    draft = {"version": 1, "title": args.title or source.stem, "subtitle": "逐句听原声，把词留在语境里。",
             "source": source.name, "sourceUrl": "", "duration": duration,
             "sentences": sentence_draft(raw, duration)}
    (out / "lesson.draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "transcription.json").write_text(json.dumps({"backend": backend, "model": model,
          "source": str(source), "duration": duration, "language": args.language}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(out), "backend": backend, "sentences": len(draft["sentences"]), "duration": duration}))


if __name__ == "__main__":
    main()
