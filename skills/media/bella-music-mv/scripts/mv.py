#!/usr/bin/env python3
"""Portable project intake, checks, rendering and delivery verification for Bella MV."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from audio import analyze as analyze_audio, audio_duration, binary, probe, sha256
from lyrics import read_lyrics, validate as validate_lyrics

SKILL = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL / "assets/animation-base"
ASPECTS = {"landscape": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)}


def dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not (path / "project.json").is_file():
        raise ValueError(f"不是Bella MV项目：{path}（缺少project.json）")
    return path


def settings(path: Path) -> dict:
    text = (path / "src/config.js").read_text(encoding="utf-8")
    match = re.search(r"const\s+PROJECT\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not match:
        raise ValueError("config.js应保留 const PROJECT = JSON对象; 的可检查格式。")
    return json.loads(match[1])


def write_settings(path: Path, data: dict) -> None:
    (path / "src/config.js").write_text("// Project settings; keep the object valid JSON.\nconst PROJECT = " +
                                      json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def sync(path: Path) -> list[dict]:
    config = settings(path)
    rows = validate_lyrics(json.loads((path / "lyrics.json").read_text(encoding="utf-8")), float(config["duration"]))
    (path / "src/lyrics.js").write_text("// Generated from lyrics.json by scripts/mv.py sync.\nconst MV_LYRICS = " +
                                      json.dumps(rows, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    return rows


def refresh_analysis(path: Path) -> dict:
    data = analyze_audio(path / settings(path)["audio"])
    previous = path / "analysis.json"
    if previous.is_file():
        old = json.loads(previous.read_text(encoding="utf-8"))
        if old.get("audio", {}).get("sha256") == data["audio"]["sha256"]:
            if "lyrics" in old:
                data["lyrics"] = old["lyrics"]
            if "chosen_provenance" in old.get("tempo", {}):
                data["tempo"]["chosen_provenance"] = old["tempo"]["chosen_provenance"]
    dump(previous, data)
    return data


def doctor() -> int:
    result = {name: binary(name, False) for name in ("python3", "node", "npm", "ffmpeg", "ffprobe")}
    candidates = [os.environ.get("CHROME_PATH"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"]
    result["chrome"] = next((p for p in candidates if p and Path(p).is_file()), None) or next(
        (x for x in (shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")) if x), None)
    result["ready_for_render"] = all(result.get(x) for x in ("node", "chrome", "ffmpeg", "ffprobe"))
    result["note"] = "npm用于项目依赖安装；已安装node_modules时无需重复安装。Chrome/GPU最终以抽帧实测为准。"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready_for_render"] else 1


def initialize(args) -> int:
    audio, lyric = Path(args.audio).expanduser().resolve(), Path(args.lyrics).expanduser().resolve()
    if not audio.is_file() or not lyric.is_file():
        raise ValueError("需要可读取的本地音乐和歌词文件；请先保存附件。")
    target = Path(args.project).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError("项目目录非空，停止以免覆盖。请换目录；修改已有项目直接继续。")
    # Validate all inputs before creating the user's project.
    analysis = analyze_audio(audio)
    if analysis["silent_or_near_silent"]:
        raise ValueError("音乐近乎静音，无法作为本次MV音轨；请检查文件。")
    rows, lyric_meta = read_lyrics(lyric, analysis["duration"], tuple(analysis["active_audio_span"]))
    if args.bpm is not None and (not math.isfinite(args.bpm) or not 20 <= args.bpm <= 300):
        raise ValueError("BPM应在20到300之间。")
    if args.offset is not None and not math.isfinite(args.offset):
        raise ValueError("offset必须为有限秒数。")
    if not 1 <= args.fps <= 120:
        raise ValueError("fps应在1到120之间。")
    width, height = ASPECTS[args.aspect]
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("node_modules", "out", "__pycache__", ".DS_Store"))
    inputs = target / "inputs"
    inputs.mkdir(exist_ok=True)
    audio_name = "music" + audio.suffix.lower()
    lyric_name = "lyrics-original" + (lyric.suffix.lower() or ".txt")
    shutil.copy2(audio, inputs / audio_name)
    shutil.copy2(lyric, inputs / lyric_name)
    tempo = analysis["tempo"]
    config = {"duration": analysis["duration"], "bpm": args.bpm or tempo["bpm"],
              "offset": args.offset if args.offset is not None else tempo["offset"], "fps": args.fps,
              "width": width, "height": height, "audio": "inputs/" + audio_name,
              "captions": args.captions, "status": "unimplemented"}
    write_settings(target, config)
    dump(target / "lyrics.json", rows)
    analysis["lyrics"] = lyric_meta
    analysis["tempo"]["chosen_provenance"] = "provided" if args.bpm is not None else "estimated"
    dump(target / "analysis.json", analysis)
    manifest = {"schema_version": 1, "skill": "bella-music-mv", "audio": "inputs/" + audio_name,
                "audio_sha256": sha256(audio), "audio_duration": analysis["duration"], "original_lyrics": "inputs/" + lyric_name,
                "lyrics_sha256": sha256(lyric), "aspect": args.aspect,
                "timing_provenance": sorted({r["timing"] for r in rows}),
                "deliverables": ["out/video.mp4", "STORYBOARD.md", "lyrics.json", "analysis.json", "project.json", "src/scenes/"]}
    dump(target / "project.json", manifest)
    sync(target)
    print(json.dumps({"project": str(target), "duration": config["duration"], "lyrics": len(rows),
                      "status": "unimplemented", "warnings": lyric_meta["warnings"],
                      "next": "写STORYBOARD.md和原创章节场景；在studio.html挂载；完成后将PROJECT.status设为authored，再check/render/verify。"}, ensure_ascii=False, indent=2))
    return 0


def inspect_project(path: Path, draft: bool = False) -> dict:
    path = path.resolve()
    config = settings(path)
    manifest = json.loads((path / "project.json").read_text(encoding="utf-8"))
    errors, warnings = [], []
    duration = float(config.get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        errors.append("无效片长")
    if "audio_duration" in manifest and abs(duration - float(manifest["audio_duration"])) > .05:
        errors.append("配置片长与导入原曲不符；本技能默认完整原曲，不能通过缩短配置把片段冒充整曲")
    for name in ("bpm", "fps", "width", "height"):
        number = config.get(name)
        if not isinstance(number, (float, int)) or not math.isfinite(number) or number <= 0:
            errors.append(f"无效配置{name}")
    if config.get("captions") not in {"karaoke", "line", "off"}:
        errors.append("captions必须是karaoke、line或off")
    if not draft and config.get("status") != "authored":
        errors.append("场景尚未完成：PROJECT.status必须为authored；草稿检查使用--draft")
    track = (path / config.get("audio", "missing")).resolve()
    if not track.is_file() or not track.is_relative_to(path):
        errors.append("音乐文件缺失或位于项目外部")
    elif sha256(track) != manifest["audio_sha256"]:
        errors.append("音乐已被替换；需重新分析并核对歌词和分镜，不能沿用旧时长/节拍")
    try:
        rows = validate_lyrics(json.loads((path / "lyrics.json").read_text(encoding="utf-8")), duration)
        generated = (path / "src/lyrics.js").read_text(encoding="utf-8")
        encoded = json.dumps(rows, ensure_ascii=False, indent=2)
        if "const MV_LYRICS = " + encoded + ";" not in generated:
            errors.append("lyrics.json与src/lyrics.js不一致；运行sync")
        if any(r["timing"] == "approximate" for r in rows):
            warnings.append("存在估算歌词时间；需试听抽查，并在交付说明标出句级估算的限制")
        if config.get("captions") == "karaoke" and not all(r.get("wordTiming") == "exact" or r["timing"] == "exact" for r in rows):
            warnings.append("部分歌词没有精确词时间，将显示整行进度高亮")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    storyboard = path / "STORYBOARD.md"
    if not draft and (not storyboard.is_file() or len(storyboard.read_text(encoding="utf-8").strip()) < 80):
        errors.append("缺少可审阅的STORYBOARD.md分镜")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "settings": config}


def node_command(path: Path, args: list[str]) -> list[str]:
    media = [f"--{name}={exe}" for name in ("ffmpeg", "ffprobe") if (exe := binary(name, False))]
    return [binary("node"), str(path / "render.mjs"), *args, *media]


def node_env() -> dict:
    env = dict(os.environ)
    ffmpeg = binary("ffmpeg", False)
    if ffmpeg:
        # Child renderer spawns ffmpeg by name; support the documented FFMPEG override.
        env["PATH"] = str(Path(ffmpeg).parent) + os.pathsep + env.get("PATH", "")
    return env


def run_check(path: Path, draft: bool = False) -> tuple[dict, int]:
    result = inspect_project(path, draft)
    if not result["valid"]:
        return result, 1
    proc = subprocess.run(node_command(path, ["--check"] + (["--draft"] if draft else [])), cwd=path,
                          env=node_env(), capture_output=True, text=True, timeout=180)
    found = next((line.removeprefix("MV_CHECK=") for line in proc.stdout.splitlines() if line.startswith("MV_CHECK=")), None)
    if found:
        result["engine"] = json.loads(found)
    else:
        result["errors"].append("渲染器未返回MV_CHECK检查结果")
    if proc.returncode:
        result["errors"].append((proc.stderr or proc.stdout)[-2500:])
    timeline = result.get("engine", {}).get("timeline", {})
    timeline_ok = timeline.get("structuralValid", timeline.get("valid", False)) if draft else timeline.get("valid", False)
    if found and not timeline_ok:
        result["errors"].extend(timeline.get("errors", ["镜头时间线未通过"]))
    if draft and timeline.get("coverageValid") is False:
        result["warnings"].extend(timeline.get("coverageErrors", ["草稿尚未覆盖全曲；只可预览已实现片段"]))
    result["valid"] = not result["errors"]
    return result, 0 if result["valid"] else 1


def verify(path: Path, file: Path, draft: bool = False) -> dict:
    config = settings(path)
    errors, warnings = [], []
    if not file.is_file():
        return {"valid": False, "errors": ["成片不存在"], "warnings": []}
    info = probe(file)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        errors.append("成片必须同时包含视频与音乐音轨")
    if video:
        rate = float(Fraction(video.get("avg_frame_rate", "0/1")))
        dur = float(video.get("duration") or info["format"]["duration"])
        tolerance = max(.12, 2 / config["fps"])
        if abs(dur - config["duration"]) > tolerance:
            errors.append(f"成片时长{dur:.3f}s与音乐/配置{config['duration']:.3f}s不符")
        if (video.get("width"), video.get("height")) != (config["width"], config["height"]):
            errors.append("成片分辨率与配置不一致")
        if abs(rate - config["fps"]) > .01:
            errors.append("成片帧率与配置不一致")
        frames = video.get("nb_frames")
        if frames and abs(int(frames) - math.ceil(config["duration"] * config["fps"])) > 1:
            errors.append("成片帧数不足或多余")
    if audio:
        audio_len = float(audio.get("duration") or info["format"]["duration"])
        if abs(audio_len - config["duration"]) > .15:
            errors.append("成片音乐时长与输入不一致，可能音轨缺失/截断")
    decode = subprocess.run([binary("ffmpeg"), "-v", "error", "-xerror", "-i", str(file), "-f", "null", "-"],
                            capture_output=True, text=True, timeout=max(120, float(config["duration"]) * 4))
    if decode.returncode:
        errors.append("完整解码失败：" + decode.stderr[-1500:])
    base = inspect_project(path, draft)
    errors.extend(base["errors"])
    warnings.extend(base["warnings"])
    warnings.append("结构/完整解码检查不证明画面好看或歌词精确，仍需联系表和短片视觉、听觉验收。")
    report = {"valid": not errors, "errors": errors, "warnings": warnings, "video": str(file.relative_to(path)) if file.is_relative_to(path) else file.name,
              "bytes": file.stat().st_size, "sha256": sha256(file), "streams": info.get("streams", [])}
    (path / "out").mkdir(exist_ok=True)
    dump(path / "out/verification.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    init = sub.add_parser("init")
    init.add_argument("--audio", required=True)
    init.add_argument("--lyrics", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--bpm", type=float)
    init.add_argument("--offset", type=float)
    init.add_argument("--fps", type=int, default=24)
    init.add_argument("--aspect", choices=ASPECTS, default="landscape")
    init.add_argument("--captions", choices=("karaoke", "line", "off"), default="karaoke")
    for cmd in ("analyze", "sync", "check", "render", "verify", "install"):
        child = sub.add_parser(cmd)
        child.add_argument("--project", required=True)
        if cmd in {"check", "render", "verify"}:
            child.add_argument("--draft", action="store_true")
        if cmd == "verify":
            child.add_argument("--video", default="out/video.mp4")
    args, remaining = parser.parse_known_args(argv)
    if remaining and args.command != "render":
        parser.error("unexpected arguments: " + " ".join(remaining))
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "init":
            return initialize(args)
        path = project_path(args.project)
        if args.command == "install":
            return subprocess.run([binary("npm"), "ci", "--ignore-scripts"], cwd=path).returncode
        if args.command == "analyze":
            data = refresh_analysis(path)
            summary = {k: data[k] for k in ("duration", "active_audio_span", "tempo", "limitations")}
            summary["lyrics"] = data.get("lyrics", {})
            summary["detail_file"] = "analysis.json"
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sync":
            print(f"Synced {len(sync(path))} lyric lines")
            return 0
        if args.command == "check":
            result, status = run_check(path, args.draft)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return status
        if args.command == "verify":
            video = Path(args.video)
            result = verify(path, video.resolve() if video.is_absolute() else (path / video).resolve(), args.draft)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["valid"] else 1
        if args.command == "render":
            result, status = run_check(path, args.draft)
            if status:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return status
            flags = remaining or ["--clip", "--out=out/video.mp4"]
            if args.draft:
                flags.append("--draft")
            return subprocess.run(node_command(path, flags), cwd=path, env=node_env()).returncode
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Bella MV: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
