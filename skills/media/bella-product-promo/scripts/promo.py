#!/usr/bin/env python3
"""Project metadata, scaffolding and media verification. Python standard library only."""
import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]
BROWSER_TECH = {"native-html", "gsap", "threejs"}
TECH = {
    "native-html": {"title": "原生 HTML / Canvas / SVG / CSS", "benefit": "轻量、易改，适合字幕、图形和流程", "export": "browser-seek"},
    "gsap": {"title": "GSAP 时间线", "benefit": "适合连续 UI 变形和精确卡点", "export": "browser-seek"},
    "remotion": {"title": "Remotion / React / TypeScript", "benefit": "适合多版本、数据驱动和可复用视频组件", "export": "remotion-cli; no bundled engine"},
    "threejs": {"title": "Three.js", "benefit": "适合产品三维展示、拆解和空间镜头", "export": "browser-seek"},
    "blender": {"title": "Blender", "benefit": "适合高质量材质、灯光和复杂三维", "export": "blender-cli; no bundled engine"},
    "hybrid": {"title": "真实 UI / 实拍 + ffmpeg", "benefit": "适合突出产品真实操作和真实人物", "export": "ffmpeg; no bundled engine"},
}


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def styles():
    path = SKILL / "references" / "presets.json"
    return read_json(path).get("styles", []) if path.exists() else []


def finite_number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} 必须在 {low}–{high} 之间")


def validate_brief(brief):
    if not isinstance(brief, dict):
        raise ValueError("brief.json 必须是 JSON 对象")
    if brief.get("schema_version") != 1:
        raise ValueError("brief.schema_version 必须为 1")
    if brief.get("tech_id") not in TECH:
        raise ValueError("未知 tech_id")
    finite_number(brief.get("duration"), "duration", 0.05, 3600)
    finite_number(brief.get("fps"), "fps", 1, 120)
    if not isinstance(brief["fps"], int):
        raise ValueError("fps 必须为整数（1–120）")
    for name in ("width", "height"):
        value = brief.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 2 or value > 8192 or value % 2:
            raise ValueError(f"{name} 必须为 2–8192 的偶数")
    total = brief["duration"] * brief["fps"]
    if abs(total - round(total)) > 1e-6:
        raise ValueError("duration × fps 必须为整数帧；调整时长或帧率")
    if not isinstance(brief.get("style_id"), str) or not brief["style_id"]:
        raise ValueError("需要 style_id（尚未选择时可为 auto）")
    if not isinstance(brief.get("product"), str) or not brief["product"].strip():
        raise ValueError("需要非空 product")
    return brief


def load_brief(project):
    return validate_brief(read_json(Path(project) / "brief.json"))


def check_project(project):
    root = Path(project).resolve()
    brief = load_brief(root)
    if brief.get("status") != "authored":
        raise ValueError("项目尚未制作：必须实际编写内容，再把 brief.json 的 status 设为 authored")
    if brief["tech_id"] in BROWSER_TECH:
        entry = root / "engine" / "index.html"
        if not entry.is_file():
            raise ValueError("缺少 engine/index.html")
        if "BELLA_PROMO_UNAUTHORED" in entry.read_text(encoding="utf-8"):
            raise ValueError("engine/index.html 仍为未制作占位；不能正式导出")
    else:
        if not (root / "engine").is_dir() or not any((root / "engine").iterdir()):
            raise ValueError("engine/ 为空：请建立所选技术的实际工程；本工具没有该路线的现成引擎")
    return {"ok": True, "project": str(root), "tech_id": brief["tech_id"], "frames": round(brief["duration"] * brief["fps"]), "note": "静态检查通过；仍需实际渲染与画面、音轨核验"}


def executable(name):
    override = os.environ.get(name.upper())
    return override or shutil.which(name)


def command_version(path):
    if not path:
        return None
    try:
        flag = "--version" if Path(path).name in {"node", "npm", "blender"} else "-version"
        result = subprocess.run([path, flag], capture_output=True, text=True, timeout=10)
        return (result.stdout or result.stderr).splitlines()[0] if result.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return "unavailable"


def doctor(args):
    names = ("node", "npm", "ffmpeg", "ffprobe", "blender")
    tools = {name: {"path": executable(name), "version": command_version(executable(name))} for name in names}
    result = {"python": sys.version.split()[0], "tools": tools, "browser_engine": "native-html / gsap / threejs only", "note": "不会自动安装依赖；具体缺项按 references/technology.md 安装"}
    if args.project:
        root = Path(args.project).resolve()
        result["project"] = str(root)
        result["playwright_package"] = (root / "node_modules" / "playwright" / "package.json").is_file()
        if (root / "brief.json").exists():
            result["tech_id"] = load_brief(root)["tech_id"]
    output(result)


def init_project(args):
    destination = Path(args.project).expanduser().resolve()
    if destination.exists():
        raise ValueError("目标已存在；为避免覆盖，请提供新的工程目录")
    known_styles = {item["id"] for item in styles()}
    if args.style != "auto" and args.style not in known_styles:
        raise ValueError("未知 style id；运行 list --kind styles 查看可用风格")
    aspect_sizes = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
    if (args.width is None) != (args.height is None):
        raise ValueError("自定义尺寸必须同时提供 --width 与 --height")
    width, height = (args.width, args.height) if args.width is not None else aspect_sizes[args.aspect]
    if width * int(args.aspect.split(":")[1]) != height * int(args.aspect.split(":")[0]):
        raise ValueError("自定义尺寸比例必须与 --aspect 一致")
    if args.url and not args.url.startswith(("https://", "http://")):
        raise ValueError("--url 必须使用 http:// 或 https://")
    brief = validate_brief({"schema_version": 1, "product": args.product or "待确认产品", "url": args.url, "style_id": args.style, "tech_id": args.tech, "duration": args.duration, "fps": args.fps, "aspect": args.aspect, "width": width, "height": height, "status": "unstarted", "audio": None})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    try:
        if args.tech in BROWSER_TECH:
            shutil.copytree(SKILL / "assets" / "browser-starter", destination, dirs_exist_ok=True)
            package = read_json(destination / "package.json")
            if args.tech == "gsap":
                package["dependencies"]["gsap"] = "3.15.0"
            elif args.tech == "threejs":
                package["dependencies"]["three"] = "0.186.1"
            (destination / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
        else:
            (destination / "engine").mkdir()
        (destination / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (destination / "assets").mkdir(exist_ok=True)
    except Exception:
        shutil.rmtree(destination)
        raise
    output({"ok": True, "project": str(destination), "status": "unstarted", "tech_id": args.tech, "next": "根据 brief 编写实际场景与音频，审阅画面后设 status=authored，再 check；脚手架不是成片", "browser_render_command": "node render.mjs --project . --output output.mp4" if args.tech in BROWSER_TECH else None})


def ratio(value):
    try:
        result = float(Fraction(str(value)))
        return result if math.isfinite(result) else 0.0
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0


def validate_probe(data, brief=None, expect_audio=False):
    streams = data.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("文件没有视频流")
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    fps = ratio(video.get("avg_frame_rate")) or ratio(video.get("r_frame_rate"))
    duration = ratio(video.get("duration")) or ratio(data.get("format", {}).get("duration"))
    width, height = video.get("width", 0), video.get("height", 0)
    if not width or not height or fps <= 0 or duration <= 0:
        raise ValueError("ffprobe 未返回有效尺寸、帧率和时长")
    if expect_audio and not audio:
        raise ValueError("需要音轨，但输出没有音频流")
    frames = next((int(value) for value in (video.get("nb_read_frames"), video.get("nb_frames")) if value is not None and str(value).isdigit()), None)
    if brief:
        if (width, height) != (brief["width"], brief["height"]):
            raise ValueError(f"尺寸不符：{width}×{height}")
        if abs(fps - brief["fps"]) > 0.01:
            raise ValueError(f"帧率不符：{fps}")
        if abs(duration - brief["duration"]) > max(0.1, 1 / brief["fps"]):
            raise ValueError(f"时长不符：{duration}")
        expected_frames = round(brief["duration"] * brief["fps"])
        if frames is not None and frames != expected_frames:
            raise ValueError(f"帧数不符：{frames}，应为 {expected_frames}")
    return {"ok": True, "width": width, "height": height, "fps": fps, "duration": duration, "frames": frames, "video_codec": video.get("codec_name"), "audio_streams": len(audio), "note": "媒体结构通过；画面内容、文字可读性与听感仍需人工/代理审阅"}


def verify_file(args):
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        raise ValueError("视频文件不存在")
    probe = executable("ffprobe")
    if not probe:
        raise ValueError("未找到 ffprobe；先安装 FFmpeg 或设置 FFPROBE 可执行文件路径")
    result = subprocess.run([probe, "-v", "error", "-count_frames", "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,nb_frames,nb_read_frames,duration:format=duration", "-of", "json", str(path)], capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError("ffprobe 失败：" + result.stderr.strip())
    brief = load_brief(args.project) if args.project else None
    output(validate_probe(json.loads(result.stdout), brief, args.expect_audio or bool(brief and brief.get("audio"))))


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("doctor", help="只读检查依赖，不自动安装")
    cmd.add_argument("--project")
    cmd = sub.add_parser("list", help="列出风格和技术路线")
    cmd.add_argument("--kind", choices=("styles", "tech", "all"), default="all")
    cmd = sub.add_parser("init", help="创建未制作工程，拒绝覆盖现有目录")
    cmd.add_argument("--project", required=True)
    cmd.add_argument("--product")
    cmd.add_argument("--url")
    cmd.add_argument("--style", default="auto")
    cmd.add_argument("--tech", choices=tuple(TECH), default="native-html")
    cmd.add_argument("--duration", type=float, default=20.0)
    cmd.add_argument("--fps", type=int, default=30)
    cmd.add_argument("--aspect", choices=("16:9", "9:16", "1:1"), default="16:9")
    cmd.add_argument("--width", type=int)
    cmd.add_argument("--height", type=int)
    cmd = sub.add_parser("check", help="阻止未制作占位被当成成片导出")
    cmd.add_argument("--project", required=True)
    cmd = sub.add_parser("verify", help="用真实 ffprobe 检查媒体结构")
    cmd.add_argument("file")
    cmd.add_argument("--project")
    cmd.add_argument("--expect-audio", action="store_true")
    return root


def main():
    args = parser().parse_args()
    try:
        if args.command == "doctor":
            doctor(args)
        elif args.command == "list":
            output({**({"styles": styles()} if args.kind in {"styles", "all"} else {}), **({"tech": [{"id": key, **value} for key, value in TECH.items()]} if args.kind in {"tech", "all"} else {})})
        elif args.command == "init":
            init_project(args)
        elif args.command == "check":
            output(check_project(args.project))
        elif args.command == "verify":
            verify_file(args)
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
