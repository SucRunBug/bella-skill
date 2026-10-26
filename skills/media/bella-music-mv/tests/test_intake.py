"""Meaningful offline intake regressions; no personal music or model service."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from lyrics import read_lyrics, validate
import mv


class LyricsTests(unittest.TestCase):
    def parse(self, text, suffix, duration=12):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / ("lyrics" + suffix)
            file.write_text(text, encoding="utf-8")
            return read_lyrics(file, duration)

    def test_plain_chinese_preserves_lines_and_discloses_estimate(self):
        rows, meta = self.parse("[主歌]\n月亮走过我的窗\n我们追着星光\n", ".txt")
        self.assertEqual([r["text"] for r in rows], ["月亮走过我的窗", "我们追着星光"])
        self.assertEqual(rows[0]["start"], 0)
        self.assertEqual(rows[-1]["end"], 12)
        self.assertTrue(all(r["timing"] == "approximate" for r in rows))
        self.assertTrue(meta["warnings"])

    def test_repeated_lrc_and_offset(self):
        rows, _ = self.parse("[ar:Example]\n[offset:500]\n[00:01.00][00:05.00]Again\n[00:08.50]Home", ".lrc")
        self.assertEqual([(r["start"], r["end"]) for r in rows], [(1.5, 5.5), (5.5, 9), (9, 12)])
        self.assertEqual([r["text"] for r in rows], ["Again", "Again", "Home"])

    def test_srt_and_vtt_preserve_gaps(self):
        srt = "1\n00:00:01,200 --> 00:00:02,500\n你好\n世界\n\n2\n00:00:05,000 --> 00:00:06,000\n回来"
        rows, _ = self.parse(srt, ".srt")
        self.assertEqual(rows[0]["text"], "你好 世界")
        self.assertEqual(rows[0]["end"], 2.5)
        vtt = "WEBVTT\n\n00:01.000 --> 00:02.000 align:center\n<b>Hello</b>"
        rows, meta = self.parse(vtt, ".vtt")
        self.assertEqual(rows[0]["text"], "Hello")
        self.assertEqual(meta["format"], "vtt")

    def test_exact_words_need_preserve_text_and_bounds(self):
        row = {"start": 0, "end": 2, "text": "Hello world", "timing": "aligned", "wordTiming": "exact",
               "words": [{"start": 0, "end": .5, "text": "Hello "}, {"start": .7, "end": 1.8, "text": "world"}]}
        self.assertEqual(validate([row], 3)[0]["wordTiming"], "exact")
        row["words"][1]["text"] = "invented"
        with self.assertRaisesRegex(ValueError, "preserve"):
            validate([row], 3)

    def test_reject_overlap_nan_out_of_bounds_and_empty(self):
        invalid = [[], [{"start": 0, "end": 20, "text": "x"}], [{"start": float("nan"), "end": 1, "text": "x"}],
                   [{"start": 0, "end": 2, "text": "a"}, {"start": 1, "end": 3, "text": "b"}]]
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate(rows, 12)

    def test_partial_timestamps_are_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "混合"):
            self.parse("[00:01]First\nMissing timestamp", ".lrc")


class ProjectTests(unittest.TestCase):
    def make_project(self, base):
        (base / "src").mkdir()
        (base / "inputs").mkdir()
        (base / "inputs/music.wav").write_bytes(b"fixture")
        mv.write_settings(base, {"duration": 2, "fps": 24, "width": 1920, "height": 1080, "bpm": 120,
                                 "offset": 0, "audio": "inputs/music.wav", "status": "authored", "captions": "karaoke"})
        mv.dump(base / "project.json", {"audio_sha256": mv.sha256(base / "inputs/music.wav"), "audio_duration": 2})
        mv.dump(base / "lyrics.json", [{"start": 0, "end": 2, "text": "test", "timing": "provided"}])
        (base / "STORYBOARD.md").write_text("A real fixture storyboard with one continuous shot. " * 4)
        mv.sync(base)

    def test_new_input_invalidates_existing_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.make_project(path)
            self.assertTrue(mv.inspect_project(path)["valid"])
            (path / "inputs/music.wav").write_bytes(b"different song")
            result = mv.inspect_project(path)
            self.assertFalse(result["valid"])
            self.assertTrue(any("替换" in e for e in result["errors"]))

    def test_lyrics_source_must_be_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.make_project(path)
            mv.dump(path / "lyrics.json", [{"start": 0, "end": 2, "text": "new text"}])
            self.assertFalse(mv.inspect_project(path)["valid"])
            mv.sync(path)
            self.assertTrue(mv.inspect_project(path)["valid"])

    def test_unimplemented_project_cannot_pass_formal_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.make_project(path)
            config = mv.settings(path)
            config["status"] = "unimplemented"
            mv.write_settings(path, config)
            self.assertFalse(mv.inspect_project(path)["valid"])
            self.assertTrue(mv.inspect_project(path, draft=True)["valid"])

    def test_shortening_config_cannot_masquerade_as_whole_song(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.make_project(path)
            config = mv.settings(path)
            config["duration"] = 1
            mv.write_settings(path, config)
            result = mv.inspect_project(path)
            self.assertFalse(result["valid"])
            self.assertTrue(any("原曲" in e for e in result["errors"]))

    def test_reanalysis_preserves_timing_provenance_only_for_same_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.make_project(path)
            prior = {"audio": {"sha256": "same"}, "tempo": {"chosen_provenance": "provided"},
                     "lyrics": {"format": "plain", "warnings": ["estimated timing"]}}
            mv.dump(path / "analysis.json", prior)
            with patch.object(mv, "analyze_audio", return_value={"audio": {"sha256": "same"}, "tempo": {"bpm": 120}}):
                result = mv.refresh_analysis(path)
            self.assertEqual(result["lyrics"]["warnings"], ["estimated timing"])
            self.assertEqual(result["tempo"]["chosen_provenance"], "provided")
            with patch.object(mv, "analyze_audio", return_value={"audio": {"sha256": "changed"}, "tempo": {"bpm": 90}}):
                result = mv.refresh_analysis(path)
            self.assertNotIn("lyrics", result)
            self.assertNotIn("chosen_provenance", result["tempo"])


if __name__ == "__main__":
    unittest.main()
