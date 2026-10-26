"""Parse lyric files without inventing word-level alignment."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re


def stamp(value: str) -> float:
    parts = value.replace(",", ".").strip().split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid timestamp: {value}")
    nums = [float(p) for p in parts]
    if any(not math.isfinite(n) or n < 0 for n in nums):
        raise ValueError(f"Invalid timestamp: {value}")
    return sum(n * 60 ** i for i, n in enumerate(reversed(nums)))


def validate(lines: list[dict], duration: float) -> list[dict]:
    if not isinstance(lines, list) or not lines:
        raise ValueError("歌词不能为空；需要非空的歌词数组或文本。")
    clean = []
    for i, item in enumerate(lines):
        if not isinstance(item, dict):
            raise ValueError(f"Lyric {i + 1} must be an object")
        start, end = float(item["start"]), float(item["end"])
        text = str(item.get("text", "")).strip()
        if not text or not all(math.isfinite(n) for n in (start, end)) or not 0 <= start < end <= duration + .05:
            raise ValueError(f"Lyric {i + 1}: invalid text/time or outside audio ({duration:.3f}s)")
        if clean and start < clean[-1]["end"] - .001:
            raise ValueError(f"Lyric {i + 1}: overlapping/out-of-order lines; resolve duet layout explicitly")
        timing = item.get("timing", "provided")
        if timing not in {"provided", "approximate", "aligned", "exact"}:
            raise ValueError(f"Lyric {i + 1}: unknown timing provenance {timing}")
        source = item.get("source") or ("weighted-active-audio-estimate" if timing == "approximate" else "user-timestamps")
        row = {"start": round(start, 4), "end": round(min(end, duration), 4), "text": text, "timing": timing, "source": str(source)}
        if (timing == "exact" or item.get("wordTiming") == "exact") and not item.get("words"):
            raise ValueError(f"Lyric {i + 1}: exact word timing requires words")
        if "words" in item:
            words, prev = [], start
            for w in item["words"]:
                a, b, txt = float(w["start"]), float(w["end"]), str(w["text"])
                if not txt or not all(math.isfinite(n) for n in (a, b)) or a < prev - .001 or b <= a or b > end + .001:
                    raise ValueError(f"Lyric {i + 1}: invalid word timing")
                words.append({"start": a, "end": b, "text": txt})
                prev = b
            if "".join("".join(w["text"].split()) for w in words) != "".join(text.split()):
                raise ValueError(f"Lyric {i + 1}: words do not preserve the provided lyric text")
            row["words"] = words
            if item.get("wordTiming") == "exact":
                row["wordTiming"] = "exact"
        clean.append(row)
    return clean


def read_lyrics(path: Path, duration: float, active: tuple[float, float] | None = None) -> tuple[list[dict], dict]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("歌词文件为空。")
    warnings = []
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data.get("lyrics") if isinstance(data, dict) else data
        return validate(rows, duration), {"format": "json", "warnings": []}
    if "-->" in text:
        rows = []
        for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
            ls = block.splitlines()
            for idx, line in enumerate(ls):
                match = re.match(r"\s*([\d:.,]+)\s*-->\s*([\d:.,]+)", line)
                if match:
                    lyric = " ".join(re.sub(r"<[^>]*>", "", x).strip() for x in ls[idx + 1:]).strip()
                    if lyric:
                        rows.append({"start": stamp(match[1]), "end": stamp(match[2]), "text": lyric, "timing": "provided"})
                    break
        return validate(rows, duration), {"format": "vtt" if text.startswith("WEBVTT") else "srt", "warnings": []}
    timed, offset, untimed = [], 0., []
    for line in text.splitlines():
        meta = re.fullmatch(r"\s*\[offset:([+-]?\d+)\]\s*", line, re.I)
        if meta:
            offset = float(meta[1]) / 1000
            continue
        tags = re.findall(r"\[(\d+:\d+(?:[.,]\d+)?)\]", line)
        body = re.sub(r"\[[^\]]*\]", "", line).strip()
        if tags and body:
            timed.extend((stamp(t), body) for t in tags)
        elif body:
            untimed.append(body)
    if timed:
        if untimed:
            raise ValueError("歌词混合了有时间戳与无时间戳的正文；请补齐时间戳，或统一为纯文本。")
        timed.sort()
        if any(t + offset < 0 for t, _ in timed):
            raise ValueError("LRC offset makes a lyric start negative")
        rows = [{"start": t + offset, "end": timed[i + 1][0] + offset if i + 1 < len(timed) else duration,
                 "text": body, "timing": "provided", "source": "lrc-starts;ends-inferred-next-start-or-audio-end"}
                for i, (t, body) in enumerate(timed)]
        return validate(rows, duration), {"format": "lrc", "warnings": ["LRC只有句子起点；结束点暂取下一句起点，末句取音频结束。"]}
    # Section labels help the director but are not sung lyrics.
    plain = [x.strip() for x in text.splitlines() if x.strip() and not re.fullmatch(r"\[[^]]+\]", x.strip())]
    if not plain:
        raise ValueError("歌词中没有可演唱的正文。")
    a, b = active or (0., duration)
    a, b = max(0., a), min(duration, b)
    if b <= a:
        a, b = 0., duration
    weights = [max(1, len(re.findall(r"[\u3400-\u9fff]|[A-Za-z0-9]+|[^\W\s]", x))) for x in plain]
    total, acc, rows = sum(weights), 0, []
    for line, weight in zip(plain, weights):
        start = a + (b - a) * acc / total
        acc += weight
        end = a + (b - a) * acc / total
        rows.append({"start": start, "end": end, "text": line, "timing": "approximate"})
    warnings.append("纯文本按字词权重分配到非静音音频区间；这不是人声检测、ASR或精确对齐。制作时须听查并修正，不能声称逐词同步。")
    return validate(rows, duration), {"format": "plain", "warnings": warnings}
