"""Check exam provenance, preference isolation, mock fidelity and bank freshness."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SEED = SCRIPTS.parent / "references/starter-bank.json"


def exam_session(fid="ielts-speaking", task="part2"):
    qid = {"ielts-speaking": "ielts-waiting-card", "pte-academic-2025": "pte-academic-situation",
           "pte-core-2026": "pte-core-situation", "toefl-ibt-2026": "toefl-interview-one"}[fid]
    return {"id": "exam-one", "started_at": "2026-10-15T18:00:00+08:00", "mode": "exam", "input_type": "text",
            "topic": "模拟测试：等待经历", "source": {"coverage": "complete"},
            "turns": [{"id": "t1", "role": "user", "stage": "initial", "text": "I waited for a parcel for two weeks."}],
            "exam": {"format_id": fid, "practice": "mock", "scope": "task", "completed": True,
                     "fidelity": "untimed", "rules_checked_on": "2026-10-15", "bank_id": "starter-20261015",
                     "question_ids": [qid], "timing": {"method": "none"},
                     "answers": [{"question_id": qid, "task": task, "answer_turn_id": "t1", "help_used": False}],
                     "assessment": "仅评文字证据；不评发音，不计算完整口语分数。"}}


class ExamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bella-exam-check-")
        self.base = Path(self.temp.name)
        self.root = self.base / "records"
        self.index = 0

    def tearDown(self):
        self.temp.cleanup()

    def file(self, data):
        self.index += 1
        path = self.base / f"input-{self.index}.json"
        path.write_text(json.dumps(data, ensure_ascii=False))
        return str(path)

    def call(self, script, *args, okay=True):
        p = subprocess.run([sys.executable, str(SCRIPTS/script), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(p.returncode == 0, okay, p.stderr or p.stdout)
        return json.loads(p.stdout if okay else p.stderr)

    def records(self, command, *args, **kwargs):
        return self.call("coach_records.py", command, "--root", self.root, *args, **kwargs)

    def save(self, data, **kwargs):
        bank_path = self.root / "question-banks" / "starter-20261015.json"
        if not bank_path.exists():
            self.save_bank(self.bank())
        return self.records("save", "--input", self.file(data), **kwargs)

    def bank(self):
        return json.loads(SEED.read_text())

    def save_bank(self, data, **kwargs):
        return self.call("question_bank.py", "save", "--root", self.root, "--input", self.file(data), "--as-of", "2026-10-15", **kwargs)

    def read_bank(self, *args, **kwargs):
        return self.call("question_bank.py", "read", "--root", self.root, "--format", "ielts-speaking", "--as-of", "2026-10-15", *args, **kwargs)

    def test_first_choice_and_exam_preferences_survive_switching(self):
        self.records("profile", "--input", self.file({"practice_goal": "exam", "active_exam": "ielts-speaking", "exam_preferences": {"ielts-speaking": {"practice": "mock", "target_score": "7"}}}))
        self.records("profile", "--input", self.file({"active_exam": "pte-core-2026", "exam_preferences": {"pte-core-2026": {"practice": "drill"}}}))
        self.records("profile", "--input", self.file({"practice_goal": "daily"}))
        profile = self.records("context")["profile"]
        self.assertEqual(profile["practice_goal"], "daily")
        self.assertEqual(profile["exam_preferences"]["ielts-speaking"]["target_score"], "7")
        self.assertEqual(profile["exam_preferences"]["pte-core-2026"]["practice"], "drill")
        self.records("profile", "--input", self.file({"practice_goal": "unknown"}), okay=False)
        self.assertEqual(self.records("context")["profile"], profile)

    def test_exam_filter_and_original_answer_export(self):
        self.save(exam_session())
        other = exam_session("pte-academic-2025", "respond_to_situation")
        other["id"] = "pte-one"
        self.save(other)
        self.assertEqual(self.records("context", "--exam", "ielts-speaking")["matching_sessions"], 1)
        self.assertEqual(self.records("context", "--goal", "daily")["matching_sessions"], 0)
        path = self.base / "exam-report.md"
        self.records("report", "--exam", "ielts-speaking", "--out", path)
        text = path.read_text()
        self.assertIn("考试首答", text)
        self.assertIn("未实测计时", text)
        self.assertIn("I waited for a parcel", text)
        self.assertNotIn("PTE Academic", text)

    def test_text_cannot_be_claimed_as_timed_audio(self):
        data = exam_session()
        data["exam"]["fidelity"] = "voice_timed"
        data["exam"]["timing"] = {"method": "host", "elapsed_seconds": 100, "evidence": "test-log"}
        self.save(data, okay=False)

    def test_helped_mock_must_be_assisted_and_retry_not_first_answer(self):
        data = exam_session()
        data["exam"]["answers"][0]["help_used"] = True
        self.save(data, okay=False)
        data["exam"]["fidelity"] = "assisted"
        self.save(data)
        data["turns"][0]["stage"] = "retry"
        self.save(data, okay=False)

    def test_core_cannot_use_academic_group_discussion(self):
        self.save(exam_session("pte-core-2026", "summarize_group_discussion"), okay=False)
        self.save(exam_session("pte-core-2026", "respond_to_situation"))

    def test_a_single_interview_is_not_complete_toefl_speaking(self):
        data = exam_session("toefl-ibt-2026", "interview")
        data["exam"]["scope"] = "speaking_section"
        self.save(data, okay=False)
        data["exam"]["scope"] = "task"
        self.save(data)

    def test_bank_empty_read_has_no_side_effects(self):
        result = self.read_bank()
        self.assertTrue(result["refresh_required"])
        self.assertFalse(self.root.exists())

    def test_bank_filters_versions_and_does_not_call_adaptations_real_questions(self):
        self.save_bank(self.bank())
        result = self.read_bank("--task", "part2")
        self.assertEqual(result["total_matching"], 2)
        self.assertFalse(result["refresh_required"])
        self.assertTrue(all(q["format_id"] == "ielts-speaking" and q["provenance"] == "adapted" for q in result["questions"]))
        self.assertEqual(result["provenance_counts"]["reported"], 0)

    def test_older_checked_sources_cannot_be_relabelled_fresh(self):
        bank = self.bank()
        for source in bank["sources"]:
            source["checked_on"] = "2026-10-01"
        self.save_bank(bank)
        self.assertTrue(self.read_bank()["refresh_required"])

    def test_future_dates_and_fake_official_sources_are_rejected(self):
        bank = self.bank()
        bank["sources"][0]["checked_on"] = "2026-10-16"
        self.save_bank(bank, okay=False)
        bank = self.bank()
        bank["questions"][0]["provenance"] = "official_sample"
        self.save_bank(bank, okay=False)
        bank = self.bank()
        bank["sources"][0]["url"] = "https://ielts.org.example.com/pretend"
        self.save_bank(bank, okay=False)

    def test_immutable_bank_snapshot_keeps_historical_question_reference(self):
        bank = self.bank()
        self.save_bank(bank)
        self.save_bank(bank)
        files = list((self.root/"question-banks").glob("*.json"))
        self.assertEqual(len(files), 1)
        before = files[0].read_bytes()
        bank["questions"][0]["prompt"] = "A changed prompt"
        self.save_bank(bank, okay=False)
        self.assertEqual(files[0].read_bytes(), before)

    def test_audio_stimulus_without_media_is_flagged_for_host_check(self):
        self.save_bank(self.bank())
        result = self.call("question_bank.py", "read", "--root", self.root, "--format", "toefl-ibt-2026", "--as-of", "2026-10-15", "--task", "listen_repeat")
        self.assertEqual(result["questions"][0]["media_not_attached"], ["audio"])
        self.assertTrue(result["questions"][0]["needs_real_media_check"])

    def test_target_exam_date_checks_source_period(self):
        bank = self.bank()
        for source in bank["sources"]:
            if source["kind"] == "third_party":
                source.update(applicable_from="2026-09-01", applicable_until="2026-12-31")
        self.save_bank(bank)
        result = self.read_bank("--for-date", "2027-01-08")
        self.assertTrue(result["source_period_mismatch"])
        self.assertTrue(result["refresh_required"])

    def test_task_read_falls_back_to_snapshot_with_requested_task(self):
        older = self.bank()
        older["id"] = "earlier-bank"
        older["checked_on"] = "2026-10-14"
        for source in older["sources"]:
            source["checked_on"] = "2026-10-14"
        self.save_bank(older)
        newer = self.bank()
        newer["id"] = "newer-bank"
        newer["questions"] = [q for q in newer["questions"] if q["format_id"] == "ielts-speaking" and q["task"] == "part1"]
        self.save_bank(newer)
        result = self.read_bank("--task", "part2")
        self.assertEqual(result["bank_id"], "earlier-bank")
        self.assertEqual(result["total_matching"], 2)
        self.assertFalse(result["refresh_required"])

    def test_exam_cannot_reference_missing_or_cross_exam_bank_question(self):
        data = exam_session()
        self.save(data)
        before = (self.root / "records.json").read_bytes()
        data["exam"]["bank_id"] = "missing-bank"
        self.save(data, okay=False)
        data = exam_session("pte-academic-2025", "respond_to_situation")
        data["exam"]["question_ids"] = ["ielts-waiting-card"]
        data["exam"]["answers"][0]["question_id"] = "ielts-waiting-card"
        self.save(data, okay=False)
        data = exam_session()
        data["exam"]["answers"][0]["task"] = "part1"
        self.save(data, okay=False)
        self.assertEqual((self.root / "records.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
