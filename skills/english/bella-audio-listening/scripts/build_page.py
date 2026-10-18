#!/usr/bin/env python3
"""Embed reviewed bilingual lesson data and original audio into one offline HTML file."""
import argparse
import base64
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path


def validate(lesson, duration):
    if lesson.get("version") != 1 or not str(lesson.get("title", "")).strip():
        raise ValueError("Lesson requires version=1 and a title.")
    sentences = lesson.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        raise ValueError("Lesson requires at least one reviewed sentence.")
    ids, last_end = set(), 0.0
    for i, row in enumerate(sentences):
        sid = row.get("id")
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ValueError(f"Sentence {i+1}: id must be a unique nonempty string.")
        ids.add(sid)
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("en", "zh")):
            raise ValueError(f"Sentence {i+1}: English and Chinese text must both be filled.")
        start, end = row.get("start"), row.get("end")
        if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in (start, end)):
            raise ValueError(f"Sentence {i+1}: invalid numeric timestamps.")
        if not (0 <= start < end <= duration + .05) or start < last_end - .001:
            raise ValueError(f"Sentence {i+1}: times overlap or exceed the audio.")
        last_end = end
    return lesson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--lesson", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    audio, source = Path(args.audio), Path(args.lesson)
    data = audio.read_bytes()
    if audio.suffix.lower() not in (".mp3", ".wav", ".m4a", ".ogg"):
        raise ValueError("Convert unsupported audio to MP3 first.")
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "default=noprint_wrappers=1:nokey=1", str(audio)], text=True).strip())
    lesson = validate(json.loads(source.read_text(encoding="utf-8")), duration)
    lesson["duration"] = duration
    lesson["id"] = hashlib.sha256(data + json.dumps([(r["id"], r["en"]) for r in lesson["sentences"]],
                                                   ensure_ascii=False).encode()).hexdigest()[:24]
    mime = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}[audio.suffix.lower()]
    lesson["audio"] = {"mime": mime, "base64": base64.b64encode(data).decode(), "name": audio.name}
    encoded = json.dumps(lesson, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = (Path(__file__).resolve().parents[1] / "assets/listening-page.html").read_text(encoding="utf-8")
    if template.count("__LESSON_DATA__") != 1:
        raise ValueError("Template data placeholder must appear exactly once.")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__LESSON_DATA__", encoded), encoding="utf-8")
    print(json.dumps({"html": str(output.resolve()), "bytes": output.stat().st_size,
                      "sentences": len(lesson["sentences"]), "duration": duration}, ensure_ascii=False))


if __name__ == "__main__":
    main()
