#!/usr/bin/env python3
"""Local speaking records. No language scoring, network, or third-party dependencies."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


VERSION = 1
RESULT_LABELS = {"pending": "待练习", "independent": "本次独立完成",
                 "with_hint": "提示后完成", "retry": "需要重练"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(obj, key, optional=False):
    value = obj.get(key, "" if optional else None)
    require(isinstance(value, str) and (optional or bool(value.strip())), f"{key}: expected {'a string' if optional else 'a nonempty string'}")
    return value


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", value), "Invalid ID")
    return value


def moment(value):
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result.utcoffset() is not None, "started_at must include a timezone")
    return result


def normalized(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def expression_id(phrase, meaning):
    key = normalized(phrase) + "\0" + normalized(meaning)
    return "e-" + hashlib.sha256(key.encode()).hexdigest()[:20]


def exam_formats():
    path = Path(__file__).resolve().parents[1] / "references/exam-formats.json"
    return read_json(path)["formats"]


def merge_profile(current, patch):
    require(isinstance(patch, dict), "Profile update must be an object")
    result = json.loads(json.dumps(current))
    for key, value in patch.items():
        if key == "exam_preferences":
            require(isinstance(value, dict), "exam_preferences must be an object")
            preferences = result.setdefault(key, {})
            for fid, settings in value.items():
                require(fid in exam_formats() and isinstance(settings, dict), "Unknown exam preference format")
                if "practice" in settings:
                    require(settings["practice"] in {"drill", "mock"}, "Unknown exam practice preference")
                if settings.get("exam_date"):
                    date.fromisoformat(settings["exam_date"])
                preferences.setdefault(fid, {}).update(settings)
        else:
            result[key] = value
    if "practice_goal" in result:
        require(result["practice_goal"] in {"daily", "exam"}, "practice_goal must be daily or exam")
    if result.get("active_exam"):
        require(result["active_exam"] in exam_formats(), "Unknown active_exam")
    return result


def validate_exam(session, turns):
    if session["mode"] != "exam":
        require("exam" not in session, "Use mode exam for exam metadata")
        return
    exam = session.get("exam")
    require(isinstance(exam, dict), "Exam session needs exam metadata")
    catalog = exam_formats()
    fid = string(exam, "format_id")
    require(fid in catalog, "Unknown exam format; verify and register the official format first")
    require(exam.get("practice") in {"drill", "mock"}, "Unknown exam practice mode")
    fidelity = exam.get("fidelity")
    require(fidelity in {"voice_timed", "self_timed", "untimed", "assisted"}, "Unknown simulation fidelity")
    require(exam.get("scope") in {"task", "speaking_section"}, "Exam scope must be task or speaking_section")
    require(date.fromisoformat(string(exam, "rules_checked_on")) <= moment(session["started_at"]).date(), "Rules cannot have been checked in the future")
    string(exam, "bank_id")
    qids = exam.get("question_ids")
    require(isinstance(qids, list) and qids and len(set(qids)) == len(qids), "question_ids must be a nonempty unique list")
    for qid in qids:
        identifier(qid)
    timing = exam.get("timing", {"method": "none"})
    require(isinstance(timing, dict) and timing.get("method") in {"host", "self", "none"}, "Unknown timing method")
    if fidelity == "voice_timed":
        require(session["input_type"] in {"voice", "audio"} and timing["method"] == "host", "voice_timed requires actual audio and host timing")
        elapsed = timing.get("elapsed_seconds")
        require(isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and elapsed > 0, "voice_timed needs measured elapsed_seconds")
        string(timing, "evidence")
    if fidelity == "self_timed":
        require(timing["method"] == "self", "self_timed needs self timing")
    answers = exam.get("answers", [])
    require(isinstance(answers, list), "Exam answers must be a list")
    require(isinstance(exam.get("completed", False), bool), "completed must be boolean")
    seen = set()
    for answer in answers:
        require(isinstance(answer, dict), "Invalid exam answer")
        qid, tid = string(answer, "question_id"), string(answer, "answer_turn_id")
        require(qid in qids and qid not in seen, "Exam first answers need unique known question IDs")
        seen.add(qid)
        require(answer.get("task") in catalog[fid]["tasks"], "Task does not belong to this exam format")
        require(tid in turns and turns[tid]["role"] == "user", "Exam answer must refer to an actual user turn")
        if exam["practice"] == "mock":
            require(turns[tid].get("stage") != "retry", "A mock first answer cannot be a post-feedback retry")
        require(isinstance(answer.get("help_used", False), bool), "help_used must be boolean")
        if exam["practice"] == "mock" and answer.get("help_used"):
            require(fidelity == "assisted", "Mock with help must be marked assisted")
    if exam.get("completed") and exam["scope"] == "speaking_section":
        for task, rules in catalog[fid]["tasks"].items():
            count = sum(answer["task"] == task for answer in answers)
            require(count >= rules.get("items", 1), "A completed speaking section is missing required tasks/items")
    if exam.get("completed"):
        require(seen == set(qids), "A completed exam scope must contain the actual first answers for all planned questions")
    if "assessment" in exam:
        require(isinstance(exam["assessment"], str), "assessment must be evidence-based written feedback")


def validate_exam_bank(session, root):
    if session["mode"] != "exam":
        return
    exam = session["exam"]
    bank_id = identifier(exam["bank_id"])
    path = Path(root) / "question-banks" / (bank_id + ".json")
    require(path.is_file(), "Exam question bank snapshot not found; cache the used questions before saving")
    bank = read_json(path)
    require(isinstance(bank, dict) and bank.get("version") == 1 and bank.get("id") == bank_id,
            "Invalid referenced bank snapshot")
    require(isinstance(bank.get("questions"), list), "Referenced snapshot has no questions")
    items = {q["id"]: q for q in bank["questions"]}
    require(len(items) == len(bank["questions"]), "Referenced snapshot has duplicate IDs")
    for qid in exam["question_ids"]:
        require(qid in items and items[qid]["format_id"] == exam["format_id"],
                "Question ID does not belong to this bank and exam format")
    for answer in exam.get("answers", []):
        require(items[answer["question_id"]]["task"] == answer["task"],
                "Exam answer task does not match the referenced bank question")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load(root):
    path = Path(root) / "records.json"
    if not path.exists():
        return {"version": VERSION, "revision": 0, "profile": {}, "sessions": {}, "edits": {}, "deleted": []}
    result = read_json(path)
    require(isinstance(result, dict) and result.get("version") == VERSION, "Unsupported records format/version; preserve the existing file")
    for key in ("profile", "sessions", "edits"):
        require(isinstance(result.get(key), dict), f"Invalid records field: {key}")
    require(isinstance(result.get("deleted"), list) and isinstance(result.get("revision"), int), "Invalid records metadata")
    return result


@contextmanager
def write_lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".write-lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Records are locked by another writer; do not overwrite or remove its lock") from exc
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".speaking-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def persist(root, data):
    data["revision"] += 1
    path = Path(root) / "records.json"
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return str(path.resolve())


def ordered(data):
    return sorted(data["sessions"].values(), key=lambda s: (moment(s["started_at"]), s["id"]))


def library(data):
    result = {}
    sessions = ordered(data)
    for session in sessions:
        for item in session.get("expressions", []):
            eid = item["id"]
            if eid in data["deleted"]:
                continue
            if eid not in result:
                result[eid] = dict(item, sources=[], attempts=[], status="pending", last_reviewed_at=None)
            result[eid]["sources"].append(session["id"])
            for key in ("example", "notes"):
                if item.get(key):
                    result[eid][key] = item[key]
    for session in sessions:
        for attempt in session.get("attempts", []):
            if attempt["expression_id"] not in result:
                require(attempt["expression_id"] in data["deleted"],
                        "A recorded attempt lost its expression source; preserve the source expression when replacing a session")
                continue
            entry = result[attempt["expression_id"]]
            turn = next(t for t in session["turns"] if t["id"] == attempt["answer_turn_id"])
            entry["attempts"].append(dict(attempt, session_id=session["id"], started_at=session["started_at"], answer=turn["text"]))
            entry["status"] = attempt["result"]
            entry["last_reviewed_at"] = session["started_at"]
    for eid, edit in data["edits"].items():
        if eid in result:
            result[eid].update(edit)
    return result


def validate_session(raw, data):
    require(isinstance(raw, dict), "Session must be an object")
    session = json.loads(json.dumps(raw))
    identifier(string(session, "id"))
    moment(string(session, "started_at"))
    require(session.get("mode") in {"topic", "description", "retell", "review", "expression", "exam"}, "Unknown mode")
    require(session.get("input_type") in {"voice", "audio", "text", "transcript"}, "Unknown input_type")
    string(session, "topic")
    session.setdefault("next_task", "")
    string(session, "next_task", optional=True)
    session.setdefault("source", {"coverage": "complete"})
    source = session["source"]
    require(isinstance(source, dict) and source.get("coverage") in {"complete", "partial", "summary"}, "source.coverage is required")
    for key in ("key", "reference", "asr_raw", "asr_clean"):
        if key in source:
            string(source, key)
    if session["input_type"] in {"audio", "transcript"}:
        string(source, "key")
    require(isinstance(session.get("turns"), list) and bool(session["turns"]), "turns must be a nonempty list")
    turns = {}
    for turn in session["turns"]:
        require(isinstance(turn, dict), "Invalid turn")
        tid = identifier(string(turn, "id"))
        require(tid not in turns, "Duplicate turn ID")
        string(turn, "text")
        require(turn.get("role") in {"user", "assistant"}, "Unknown turn role")
        require(turn.get("stage", "dialogue") in {"initial", "dialogue", "help", "retry", "review"}, "Unknown turn stage")
        turns[tid] = turn
    require(any(t["role"] == "user" for t in turns.values()), "A session needs an actual user answer")
    validate_exam(session, turns)
    for key in ("feedback", "expressions", "attempts"):
        session.setdefault(key, [])
        require(isinstance(session[key], list), f"{key} must be a list")
    known = library(data)
    new_items = set()
    for item in session["expressions"]:
        require(isinstance(item, dict), "Invalid expression")
        phrase, meaning = string(item, "phrase"), string(item, "meaning")
        item.setdefault("selection", "unspecified")
        require(item["selection"] in {"user", "coach", "unspecified"}, "Unknown expression selection source")
        expected = expression_id(phrase, meaning)
        eid = identifier(item.setdefault("id", expected))
        require(eid == expected or eid in known, "Unknown expression ID; omit ID for a new expression")
        if eid in known:
            require(normalized(phrase) == normalized(known[eid]["phrase"]), "Existing expression ID refers to a different phrase")
        require(eid not in new_items, "Duplicate expression in session")
        new_items.add(eid)
        for key in ("example", "notes"):
            string(item, key, optional=True)
    available = set(known) | new_items
    previous = data["sessions"].get(session["id"])
    if source.get("key"):
        previous = next((s for s in data["sessions"].values()
                         if s["source"].get("key") == source["key"]), previous)
    retired_attempts = {(a["id"], a["expression_id"]) for a in (previous or {}).get("attempts", [])}
    for key in ("feedback", "attempts"):
        seen = set()
        for item in session[key]:
            require(isinstance(item, dict), f"Invalid {key} item")
            iid = identifier(string(item, "id"))
            require(iid not in seen, f"Duplicate {key} ID")
            seen.add(iid)
            if key == "feedback":
                tid = string(item, "turn_id")
                require(tid in turns and turns[tid]["role"] == "user", "Feedback must refer to an actual user turn")
                require(item.get("kind") in {"error", "optional", "uncertain"}, "Unknown feedback kind")
                require(string(item, "original") in turns[tid]["text"], "Feedback original must occur in its user turn")
                for field in ("tag", "suggestion", "reason"):
                    string(item, field)
                if "retry_turn_id" in item:
                    retry = item["retry_turn_id"]
                    require(retry in turns and turns[retry]["role"] == "user", "Retry must refer to an actual user turn")
            else:
                if "expression_id" not in item:
                    item["expression_id"] = expression_id(string(item, "phrase"), string(item, "meaning"))
                eid = identifier(item["expression_id"])
                historical = (iid, eid) in retired_attempts and eid in data["deleted"]
                require((eid in available and eid not in data["deleted"]) or historical,
                        "Attempt refers to an unavailable/deleted expression")
                tid = string(item, "answer_turn_id")
                require(tid in turns and turns[tid]["role"] == "user", "Attempt must refer to an actual user answer")
                string(item, "prompt")
                require(item.get("result") in {"independent", "with_hint", "retry"}, "Unknown attempt result")
                require(item.get("hint") in {"none", "clue", "answer"}, "Unknown hint level")
                require((item["result"] != "independent" or item["hint"] == "none") and
                        (item["result"] != "with_hint" or item["hint"] != "none"), "Attempt result contradicts its hint level")
                require(isinstance(item.get("transfer", False), bool), "transfer must be boolean")
    return session


def filtered(data, args):
    rows = ordered(data)
    if getattr(args, "session", None):
        rows = [s for s in rows if s["id"] == args.session]
        require(bool(rows), "Session not found")
    if getattr(args, "exam", None):
        rows = [s for s in rows if s.get("exam", {}).get("format_id") == args.exam]
    if getattr(args, "goal", None):
        rows = [s for s in rows if (s["mode"] == "exam") == (args.goal == "exam")]
    start, end = getattr(args, "since", None), getattr(args, "until", None)
    if start:
        start = date.fromisoformat(start)
    if end:
        end = date.fromisoformat(end)
    require(not start or not end or start <= end, "since must not be after until")
    return [s for s in rows if (not start or moment(s["started_at"]).date() >= start)
            and (not end or moment(s["started_at"]).date() <= end)]


def issue_counts(sessions):
    counts = {}
    for session in sessions:
        for item in session.get("feedback", []):
            if item["kind"] == "error":
                row = counts.setdefault(item["tag"], {"tag": item["tag"], "occurrences": 0, "sessions": []})
                row["occurrences"] += 1
                if session["id"] not in row["sessions"]:
                    row["sessions"].append(session["id"])
    return sorted(counts.values(), key=lambda r: (-r["occurrences"], r["tag"]))


def review_items(data, limit):
    priorities = {"retry": 0, "with_hint": 1, "pending": 2, "independent": 3}
    minimum = datetime.min.replace(tzinfo=datetime.now().astimezone().tzinfo)
    def key(item):
        last = moment(item["last_reviewed_at"]) if item["last_reviewed_at"] else minimum
        return priorities[item["status"]], last, item["id"]
    return sorted(library(data).values(), key=key)[:limit]


def report(data, sessions):
    lines = ["# Bella 英语口语练习记录", "", f"本报告包含 {len(sessions)} 次实际存档。", ""]
    for session in sessions:
        lines += [f"## {session['started_at']} {session['topic']}", "",
                  f"输入方式：{session['input_type']}；记录范围：{session['source']['coverage']}。", ""]
        if session.get("exam"):
            exam = session["exam"]
            label = exam_formats()[exam["format_id"]]["label"]
            practice = {"drill": "题库练习", "mock": "模拟考试"}[exam["practice"]]
            fidelity = {"voice_timed": "语音实测计时", "self_timed": "用户自行计时", "untimed": "未实测计时", "assisted": "有辅助"}[exam["fidelity"]]
            completion = "本次声明范围已完成" if exam.get("completed") else "未标记完成"
            lines += [f"考试：{label}；方式：{practice}；条件：{fidelity}；范围：{exam['scope']}。", "",
                      f"完成状态：{completion}。", "",
                      f"规则核对：{exam['rules_checked_on']}；题库快照：{exam['bank_id']}。", "",
                      "### 考试首答", ""]
            for answer in exam.get("answers", []):
                text = next(t["text"] for t in session["turns"] if t["id"] == answer["answer_turn_id"])
                lines += [f"- {answer['question_id']} / {answer['task']}：{text}"]
            if exam.get("assessment"):
                lines += ["", "### 练习评估", "", exam["assessment"], ""]
        lines += ["### 原始对话与复练", ""]
        for turn in session["turns"]:
            text = turn["text"]
            fence = "`" * max(3, max((len(x) + 1 for x in re.findall(r"`+", text)), default=3))
            lines += [f"{turn['role']} · {turn.get('stage', 'dialogue')} · {turn['id']}", "", fence + "text", text, fence, ""]
        lines += ["### 针对性反馈", ""]
        if not session["feedback"]:
            lines += ["本次没有保存反馈。", ""]
        for item in session["feedback"]:
            label = {"error": "明确问题", "optional": "可选表达", "uncertain": "待确认"}[item["kind"]]
            lines += [f"- {label}：{item['original']} → {item['suggestion']}。{item['reason']}",
                      f"  复练：{item.get('retry_turn_id', '未记录')}。"]
        lines += ["", "### 留下的表达", ""]
        for item in session["expressions"]:
            if item["id"] not in data["deleted"]:
                entry = dict(item, **data["edits"].get(item["id"], {}))
                selection = {"user": "用户选择", "coach": "AI 推荐", "unspecified": "未标注"}[item.get("selection", "unspecified")]
                attempts = [a for a in session["attempts"] if a["expression_id"] == item["id"]]
                state = RESULT_LABELS[attempts[-1]["result"]] if attempts else "本次未记录作答"
                lines += [f"- {entry['phrase']}：{entry['meaning']}；来源：{selection}；当次作答：{state}。"]
                if entry.get("notes"):
                    lines += [f"  备注：{entry['notes']}"]
        heading = "实际回考与复练" if session["mode"] == "review" else "实际作答与复练"
        lines += ["", f"### {heading}", ""]
        if not session["attempts"]:
            lines += ["没有保存作答状态记录。", ""]
        for item in session["attempts"]:
            if item["expression_id"] in data["deleted"]:
                continue
            answer = next(t["text"] for t in session["turns"] if t["id"] == item["answer_turn_id"])
            lines += [f"- 题目：{item['prompt']}", f"  回答：{answer}",
                      f"  结果：{RESULT_LABELS[item['result']]}；提示：{item['hint']}。"]
        lines += ["", "### 下次任务", "", session.get("next_task") or "未安排。", ""]
    lines += ["## 明确问题统计", ""]
    for item in issue_counts(sessions):
        lines += [f"- {item['tag']}：出现 {item['occurrences']} 次，涉及 {len(item['sessions'])} 次练习。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("save", "context", "review", "profile", "expression", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        if name in {"save", "profile"}:
            p.add_argument("--input", required=True)
        if name in {"context", "review"}:
            p.add_argument("--limit", type=int, default=5 if name == "context" else 3)
        if name == "context":
            p.add_argument("--library-limit", type=int, default=20)
        if name in {"context", "report"}:
            p.add_argument("--session")
            p.add_argument("--since")
            p.add_argument("--until")
            p.add_argument("--exam", choices=list(exam_formats()))
            p.add_argument("--goal", choices=["daily", "exam"])
        if name == "report":
            p.add_argument("--out", required=True)
        if name == "expression":
            p.add_argument("--id", required=True)
            group = p.add_mutually_exclusive_group(required=True)
            group.add_argument("--delete", action="store_true")
            group.add_argument("--input")
    sub.add_parser("fingerprint").add_argument("file")
    args = parser.parse_args()
    if args.command == "fingerprint":
        sha = hashlib.sha256()
        with Path(args.file).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                sha.update(block)
        return {"key": "sha256:" + sha.hexdigest()}
    root = Path(args.root)
    for key in ("limit", "library_limit"):
        if hasattr(args, key):
            require(getattr(args, key) > 0, f"{key} must be positive")
    if args.command in {"save", "profile", "expression"}:
        with write_lock(root):
            data = load(root)
            if args.command == "save":
                session = validate_session(read_json(args.input), data)
                validate_exam_bank(session, root)
                source_key = session["source"].get("key")
                if source_key:
                    old = next((s for s in data["sessions"].values() if s["source"].get("key") == source_key), None)
                    if old:
                        session["id"], session["started_at"] = old["id"], old["started_at"]
                data["sessions"][session["id"]] = session
                # Rebuild from canonical sessions so a corrected/replaced record cannot inflate counts.
                library(data)
                path = persist(root, data)
                return {"saved": True, "path": path, "session_id": session["id"],
                        "session_count": len(data["sessions"]), "expression_ids": [e["id"] for e in session["expressions"]]}
            if args.command == "profile":
                edit = read_json(args.input)
                data["profile"] = merge_profile(data["profile"], edit)
            else:
                eid = identifier(args.id)
                require(eid in library(data), "Expression not found")
                if args.delete:
                    data["deleted"].append(eid)
                    data["edits"].pop(eid, None)
                else:
                    edit = read_json(args.input)
                    require(isinstance(edit, dict) and bool(edit) and set(edit) <= {"meaning", "example", "notes"}, "Edit only meaning, example, notes")
                    for key in edit:
                        string(edit, key, optional=key != "meaning")
                    data["edits"].setdefault(eid, {}).update(edit)
            return {"saved": True, "path": persist(root, data)}
    data = load(root)
    if args.command == "review":
        return {"total_expressions": len(library(data)), "candidates": review_items(data, args.limit)}
    sessions = filtered(data, args)
    if args.command == "context":
        entries = list(library(data).values())
        return {"profile": data["profile"], "total_sessions": len(data["sessions"]),
                "matching_sessions": len(sessions), "sessions": sessions[-args.limit:],
                "total_expressions": len(entries), "expressions": entries[:args.library_limit],
                "issues": issue_counts(sessions), "revision": data["revision"]}
    out = Path(args.out).resolve()
    require(out != (root / "records.json").resolve() and out != (root / ".write-lock").resolve(), "Report must not overwrite canonical records")
    atomic_text(out, report(data, sessions))
    return {"saved": True, "path": str(out), "session_count": len(sessions)}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
