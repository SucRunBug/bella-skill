"""Behavioral checks for persistence, provenance, review states and record exports."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/coach_records.py"


def session(sid="practice-one", stamp="2026-10-12T18:00:00+08:00"):
    return {
        "id": sid, "started_at": stamp, "mode": "topic", "input_type": "text", "topic": "昨天的早餐",
        "source": {"coverage": "complete"},
        "turns": [{"id": "t1", "role": "user", "text": "Yesterday I eat a burger.", "stage": "initial"},
                  {"id": "t2", "role": "assistant", "text": "昨天的动作可以用 ate，再说一次。", "stage": "help"},
                  {"id": "t3", "role": "user", "text": "Yesterday I ate a burger.", "stage": "retry"}],
        "feedback": [{"id": "f1", "turn_id": "t1", "kind": "error", "tag": "past-tense",
                      "original": "I eat", "suggestion": "I ate", "reason": "过去的动作", "retry_turn_id": "t3"},
                     {"id": "f2", "turn_id": "t3", "kind": "optional", "tag": "word-choice",
                      "original": "a burger", "suggestion": "a hamburger", "reason": "另一种说法"}],
        "expressions": [{"phrase": "at the time", "meaning": "在当时", "example": "I was hungry at the time."}],
        "attempts": [], "next_task": "讲一次不同的经历。"
    }


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bella-speaking-records-")
        self.base = Path(self.temp.name)
        self.root = self.base / "records"
        self.number = 0

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, command, *args, okay=True):
        process = subprocess.run([sys.executable, str(SCRIPT), command, "--root", str(self.root), *args],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode == 0, okay, process.stderr or process.stdout)
        return json.loads(process.stdout if okay else process.stderr)

    def datafile(self, value):
        self.number += 1
        path = self.base / f"input-{self.number}.json"
        path.write_text(json.dumps(value, ensure_ascii=False))
        return str(path)

    def save(self, data, okay=True):
        return self.run_cli("save", "--input", self.datafile(data), okay=okay)

    def test_read_empty_does_not_create_learner_folder(self):
        self.assertEqual(self.run_cli("context")["total_sessions"], 0)
        self.assertEqual(self.run_cli("review")["candidates"], [])
        self.assertFalse(self.root.exists())

    def test_resave_replaces_and_recounts_without_inflation(self):
        data = session()
        self.save(data)
        self.save(data)
        result = self.run_cli("context")
        self.assertEqual((result["total_sessions"], result["total_expressions"]), (1, 1))
        self.assertEqual(result["issues"], [{"tag": "past-tense", "occurrences": 1, "sessions": [data["id"]]}])
        data["feedback"] = []
        self.save(data)
        self.assertEqual(self.run_cli("context")["issues"], [])

    def test_import_fingerprint_updates_original_session(self):
        source = self.base / "record.txt"
        source.write_text("实际导入的原文")
        fingerprint = subprocess.run([sys.executable, str(SCRIPT), "fingerprint", str(source)], capture_output=True, text=True, check=True)
        data = session()
        data["input_type"] = "transcript"
        data["source"]["key"] = json.loads(fingerprint.stdout)["key"]
        self.save(data)
        data["id"] = "a-new-import-id"
        data["started_at"] = "2026-10-13T10:00:00+08:00"
        result = self.save(data)
        self.assertEqual(result["session_id"], "practice-one")
        row = self.run_cli("context")["sessions"][0]
        self.assertEqual(row["started_at"], "2026-10-12T18:00:00+08:00")
        self.assertEqual(result["session_count"], 1)

    def test_unanswered_expression_stays_pending(self):
        self.save(session())
        candidate = self.run_cli("review")["candidates"][0]
        self.assertEqual(candidate["status"], "pending")
        self.assertEqual(candidate["attempts"], [])

    def test_cross_session_states_and_duplicate_attempt(self):
        result = self.save(session())
        eid = result["expression_ids"][0]
        second = session("review-two", "2026-10-13T10:00:00+08:00")
        second["mode"] = "review"
        second["feedback"] = []
        second["attempts"] = [{"id": "a1", "expression_id": eid, "prompt": "描述当时的感受。",
                              "answer_turn_id": "t3", "result": "with_hint", "hint": "clue", "transfer": True}]
        self.save(second)
        self.save(second)
        candidate = self.run_cli("review")["candidates"][0]
        self.assertEqual(candidate["status"], "with_hint")
        self.assertEqual(len(candidate["attempts"]), 1)
        third = copy.deepcopy(second)
        third.update(id="review-three", started_at="2026-10-14T09:00:00+08:00")
        third["attempts"][0].update(result="independent", hint="none")
        self.save(third)
        candidate = self.run_cli("review")["candidates"][0]
        self.assertEqual(candidate["status"], "independent")
        self.assertEqual(len(candidate["sources"]), 3)

    def test_invalid_hint_claim_does_not_change_saved_records(self):
        self.save(session())
        before = (self.root / "records.json").read_bytes()
        bad = session("bad-review")
        bad["attempts"] = [{"id": "a1", "phrase": "at the time", "meaning": "在当时", "prompt": "造句",
                            "answer_turn_id": "t3", "result": "independent", "hint": "answer"}]
        self.save(bad, okay=False)
        self.assertEqual((self.root / "records.json").read_bytes(), before)

    def test_feedback_cannot_attribute_ai_words_to_user(self):
        bad = session()
        bad["feedback"][0]["turn_id"] = "t2"
        self.save(bad, okay=False)
        bad = session()
        bad["feedback"][0]["original"] = "Invented original"
        self.save(bad, okay=False)
        self.assertFalse((self.root / "records.json").exists())

    def test_corrupt_or_unsupported_store_is_preserved(self):
        self.root.mkdir()
        path = self.root / "records.json"
        for content in ("{broken", '{"version": 55}'):
            path.write_text(content)
            self.save(session(), okay=False)
            self.assertEqual(path.read_text(), content)

    def test_delete_then_reimport_does_not_restore_expression(self):
        data = session()
        data["source"]["key"] = "test-source-key"
        data["input_type"] = "transcript"
        data["attempts"] = [{"id": "a1", "phrase": "at the time", "meaning": "在当时", "prompt": "造句",
                             "answer_turn_id": "t3", "result": "with_hint", "hint": "answer"}]
        eid = self.save(data)["expression_ids"][0]
        self.run_cli("expression", "--id", eid, "--delete")
        data["id"] = "repeat-source"
        self.save(data)
        self.assertEqual(self.run_cli("context")["total_expressions"], 0)
        self.assertEqual(self.run_cli("review")["candidates"], [])

    def test_expression_edit_and_profile_survive_new_sessions(self):
        eid = self.save(session())["expression_ids"][0]
        self.run_cli("expression", "--id", eid, "--input", self.datafile({"meaning": "那时候", "notes": "我的释义"}))
        self.run_cli("profile", "--input", self.datafile({"feedback": "最后总结", "minutes": 5}))
        self.save(session("next-practice", "2026-10-13T11:00:00+08:00"))
        result = self.run_cli("context")
        self.assertEqual(result["expressions"][0]["meaning"], "那时候")
        self.assertEqual(result["profile"]["feedback"], "最后总结")

    def test_date_filter_uses_record_local_date_and_reports_coverage(self):
        self.save(session("one", "2026-10-12T00:01:00+08:00"))
        self.save(session("two", "2026-10-13T00:01:00+08:00"))
        result = self.run_cli("context", "--since", "2026-10-12", "--until", "2026-10-12")
        self.assertEqual(result["matching_sessions"], 1)
        self.assertEqual(result["sessions"][0]["id"], "one")
        self.run_cli("context", "--since", "2026-10-14", "--until", "2026-10-12", okay=False)

    def test_report_preserves_raw_and_protects_canonical_store(self):
        self.save(session())
        path = self.base / "练习记录.md"
        self.run_cli("report", "--out", str(path))
        text = path.read_text()
        self.assertIn("Yesterday I eat a burger.", text)
        self.assertIn("Yesterday I ate a burger.", text)
        self.assertIn("讲一次不同的经历", text)
        before = (self.root / "records.json").read_bytes()
        self.run_cli("report", "--out", str(self.root / "records.json"), okay=False)
        self.assertEqual((self.root / "records.json").read_bytes(), before)

    def test_concurrent_writer_fails_without_removing_existing_lock(self):
        self.save(session())
        lock = self.root / ".write-lock"
        lock.write_text("another writer")
        before = (self.root / "records.json").read_bytes()
        self.save(session(), okay=False)
        self.assertEqual(lock.read_text(), "another writer")
        self.assertEqual((self.root / "records.json").read_bytes(), before)

    def test_missing_timezone_and_missing_import_key_are_rejected(self):
        bad = session(stamp="2026-10-12T18:00:00")
        self.save(bad, okay=False)
        bad = session()
        bad["input_type"] = "audio"
        self.save(bad, okay=False)

    def test_replacing_session_preserves_later_review_sources(self):
        first = session()
        eid = self.save(first)["expression_ids"][0]
        second = session("later-review", "2026-10-13T08:00:00+08:00")
        second["expressions"] = []
        second["feedback"] = []
        second["attempts"] = [{"id": "a1", "expression_id": eid, "prompt": "造句",
                               "answer_turn_id": "t3", "result": "with_hint", "hint": "clue"}]
        self.save(second)
        before = (self.root / "records.json").read_bytes()
        first["expressions"] = []
        self.save(first, okay=False)
        self.assertEqual((self.root / "records.json").read_bytes(), before)

    def test_report_distinguishes_retries_selection_and_unanswered_words(self):
        data = session()
        data["expressions"][0]["selection"] = "user"
        data["expressions"].append({"phrase": "when the rain stopped", "meaning": "雨停的时候", "selection": "coach"})
        data["attempts"] = [{"id": "a1", "phrase": "at the time", "meaning": "在当时", "prompt": "重说一次",
                             "answer_turn_id": "t3", "result": "with_hint", "hint": "answer"}]
        self.save(data)
        path = self.base / "report.md"
        self.run_cli("report", "--out", str(path))
        text = path.read_text()
        self.assertIn("### 实际作答与复练", text)
        self.assertNotIn("### 实际回考", text)
        self.assertIn("来源：用户选择；当次作答：提示后完成", text)
        self.assertIn("来源：AI 推荐；当次作答：本次未记录作答", text)


if __name__ == "__main__":
    unittest.main()
