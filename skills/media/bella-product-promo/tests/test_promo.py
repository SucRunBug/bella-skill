"""Behavior checks; FFmpeg integration runs when real tools are available."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "promo.py"
spec = importlib.util.spec_from_file_location("bella_promo", SCRIPT)
promo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promo)


class PromoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bella promo test ")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], text=True, capture_output=True)

    def create(self, name="产品 with spaces", *options):
        path = self.root / name
        result = self.cli("init", "--project", path, "--product", "测试产品", *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        return path

    def test_init_handles_spaces_and_records_contract(self):
        path = self.create()
        data = json.loads((path / "brief.json").read_text())
        self.assertEqual((data["style_id"], data["tech_id"], data["status"]), ("auto", "native-html", "unstarted"))
        self.assertEqual((data["duration"], data["fps"]), (20.0, 30))
        self.assertTrue((path / "engine" / "index.html").is_file())

    def test_existing_project_not_overwritten(self):
        path = self.create()
        marker = path / "my-content.txt"
        marker.write_text("keep me")
        result = self.cli("init", "--project", path)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "keep me")

    def test_invalid_fps_and_noninteger_frames_rejected(self):
        for extra in [("--fps", "0"), ("--fps", "121"), ("--fps", "29.97"), ("--fps", "30", "--duration", "0.11")]:
            with self.subTest(extra=extra):
                target = self.root / "bad"
                result = self.cli("init", "--project", target, *extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())

    def test_custom_size_requires_matching_even_aspect(self):
        for extra in [("--width", "160"), ("--width", "161", "--height", "90"), ("--width", "160", "--height", "100")]:
            result = self.cli("init", "--project", self.root / "bad", *extra)
            self.assertNotEqual(result.returncode, 0)

    def test_unknown_style_rejected_without_partial_project(self):
        path = self.root / "missing-style"
        result = self.cli("init", "--project", path, "--style", "nonexistent-style-id")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(path.exists())

    def test_unstarted_and_placeholder_cannot_pass_check(self):
        path = self.create()
        self.assertNotEqual(self.cli("check", "--project", path).returncode, 0)
        data = json.loads((path / "brief.json").read_text())
        data["status"] = "authored"
        (path / "brief.json").write_text(json.dumps(data))
        result = self.cli("check", "--project", path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("占位", result.stderr)

    def test_other_routes_do_not_claim_browser_engine(self):
        for tech in ("remotion", "blender", "hybrid"):
            path = self.create(tech, "--tech", tech)
            self.assertFalse((path / "render.mjs").exists())
            data = json.loads((path / "brief.json").read_text())
            data["status"] = "authored"
            (path / "brief.json").write_text(json.dumps(data))
            self.assertNotEqual(self.cli("check", "--project", path).returncode, 0)

    def test_browser_dependencies_follow_tech(self):
        for tech, package in [("gsap", "gsap"), ("threejs", "three")]:
            path = self.create(tech, "--tech", tech)
            deps = json.loads((path / "package.json").read_text())["dependencies"]
            self.assertIn(package, deps)
            self.assertIn("playwright", deps)

    def test_real_ffprobe_field_shapes_and_validation(self):
        data = {"streams": [{"codec_type": "audio", "codec_name": "aac"}, {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001", "nb_read_frames": "30", "duration": "1.001000"}], "format": {"duration": "1.001000"}}
        checked = promo.validate_probe(data, expect_audio=True)
        self.assertAlmostEqual(checked["fps"], 29.97002997)
        self.assertEqual(checked["frames"], 30)
        self.assertEqual(checked["audio_streams"], 1)
        with self.assertRaises(ValueError):
            promo.validate_probe({"streams": []})
        with self.assertRaises(ValueError):
            promo.validate_probe({"streams": [data["streams"][1]], "format": data["format"]}, expect_audio=True)

    @unittest.skipUnless(promo.executable("ffmpeg") and promo.executable("ffprobe"), "real FFmpeg and ffprobe not installed")
    def test_generated_video_and_audio_verified_by_real_ffprobe(self):
        path = self.create("media path", "--duration", "0.4", "--fps", "10", "--width", "160", "--height", "90")
        movie = path / "真实视频 output.mp4"
        result = subprocess.run([promo.executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=160x90:r=10", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "0.4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(movie)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        verified = self.cli("verify", movie, "--project", path, "--expect-audio")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        media = json.loads(verified.stdout)
        self.assertEqual((media["width"], media["height"], media["frames"], media["audio_streams"]), (160, 90, 4, 1))
        brief = json.loads((path / "brief.json").read_text())
        brief["fps"] = 20
        (path / "brief.json").write_text(json.dumps(brief))
        self.assertNotEqual(self.cli("verify", movie, "--project", path).returncode, 0)


if __name__ == "__main__":
    unittest.main()
