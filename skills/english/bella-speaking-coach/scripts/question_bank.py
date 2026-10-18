#!/usr/bin/env python3
"""Validate and cache source-labelled speaking prompts; web retrieval is performed by the Agent."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from coach_records import atomic_text, exam_formats, identifier, normalized, read_json, require, string, write_lock


OFFICIAL = ("ielts.org", "britishcouncil.org", "ielts.idp.com", "ets.org", "pearsonpte.com", "pearsonpte.com.cn")


def checked_date(value, as_of):
    result = date.fromisoformat(value)
    require(result <= as_of, "A retrieval/publication/report date cannot be in the future")
    return result


def validate_bank(raw, as_of):
    require(isinstance(raw, dict) and raw.get("version") == 1, "Unsupported bank format/version")
    bank = json.loads(json.dumps(raw))
    identifier(string(bank, "id"))
    overall = checked_date(string(bank, "checked_on"), as_of)
    require(isinstance(bank.get("sources"), list) and bank["sources"], "Sources are required")
    sources = {}
    for source in bank["sources"]:
        require(isinstance(source, dict), "Invalid source")
        sid = identifier(string(source, "id"))
        require(sid not in sources, "Duplicate source ID")
        string(source, "title")
        parsed = urlsplit(string(source, "url"))
        require(parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username and not parsed.password, "Use a public source URL without credentials")
        require(source.get("kind") in {"official", "third_party"}, "Unknown source kind")
        if source["kind"] == "official":
            host = parsed.hostname.lower()
            require(any(host == domain or host.endswith("." + domain) for domain in OFFICIAL), "Official source must use a known exam authority domain")
        require(checked_date(string(source, "checked_on"), as_of) <= overall, "Source check is later than the snapshot")
        for field in ("published_on", "updated_on"):
            if source.get(field):
                checked_date(source[field], as_of)
        for field in ("applicable_from", "applicable_until"):
            if source.get(field):
                date.fromisoformat(source[field])
        require(not source.get("applicable_from") or not source.get("applicable_until") or
                source["applicable_from"] <= source["applicable_until"], "Invalid source period")
        sources[sid] = source
    require(isinstance(bank.get("questions"), list) and bank["questions"], "Questions are required")
    catalog = exam_formats()
    ids, contents = set(), set()
    for q in bank["questions"]:
        require(isinstance(q, dict), "Invalid question")
        qid = identifier(string(q, "id"))
        require(qid not in ids, "Duplicate question ID")
        ids.add(qid)
        fid = string(q, "format_id")
        require(fid in catalog and q.get("task") in catalog[fid]["tasks"], "Question task/version mismatch")
        string(q, "topic")
        key = (fid, q["task"], normalized(string(q, "prompt")))
        require(key not in contents, "Duplicate prompt in this snapshot")
        contents.add(key)
        require(q.get("provenance") in {"official_sample", "reported", "adapted", "generated"}, "Unknown question provenance")
        refs = q.get("source_ids")
        require(isinstance(refs, list) and refs and all(s in sources for s in refs), "Question needs known source IDs")
        kinds = {sources[s]["kind"] for s in refs}
        if q["provenance"] == "official_sample":
            require(kinds == {"official"}, "A third-party question is not an official sample")
        if q["provenance"] == "reported":
            require("third_party" in kinds, "A recalled question needs a report source")
        if q.get("reported_on"):
            checked_date(q["reported_on"], as_of)
        if "materials" in q:
            require(isinstance(q["materials"], list), "materials must be a list")
            for material in q["materials"]:
                require(isinstance(material, dict) and material.get("type") in {"audio", "image"}, "Unknown material type")
                string(material, "reference")
    return bank


def select(bank, fid, task, as_of, max_age, limit, for_date=None):
    sources = {s["id"]: s for s in bank["sources"]}
    questions = [q for q in bank["questions"] if q["format_id"] == fid and (not task or q["task"] == task)]
    used = {sid for q in questions for sid in q["source_ids"]}
    dates = [date.fromisoformat(sources[sid]["checked_on"]) for sid in used]
    stale = not dates or (as_of - min(dates)).days > max_age
    target_date = for_date or as_of
    def outside(source):
        return ((source.get("applicable_from") and target_date < date.fromisoformat(source["applicable_from"])) or
                (source.get("applicable_until") and target_date > date.fromisoformat(source["applicable_until"])))
    catalogue = exam_formats()[fid]
    selected = []
    for q in questions[:limit]:
        row = dict(q)
        required = set(catalogue["tasks"][q["task"]].get("input_media", []))
        supplied = {m["type"] for m in q.get("materials", [])}
        row["media_not_attached"] = sorted(required - supplied)
        row["needs_real_media_check"] = bool(required)
        row["outside_source_period"] = any(bool(outside(sources[sid])) for sid in q["source_ids"])
        selected.append(row)
    period_mismatch = any(any(bool(outside(sources[sid])) for sid in q["source_ids"]) for q in questions)
    return {"bank_id": bank["id"], "snapshot_checked_on": bank["checked_on"], "as_of": as_of.isoformat(),
            "for_date": target_date.isoformat(), "refresh_required": stale or period_mismatch, "source_period_mismatch": period_mismatch,
            "provenance_counts": {kind: sum(q["provenance"] == kind for q in questions)
                for kind in ("official_sample", "reported", "adapted", "generated")},
            "total_matching": len(questions), "questions": selected, "sources": [sources[sid] for sid in sorted(used)],
            "notice": "来源核对日期不等于考试发生日期；媒体引用仍需实际打开或由宿主播放。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("save")
    save.add_argument("--root", required=True)
    save.add_argument("--input", required=True)
    save.add_argument("--as-of", required=True)
    read = sub.add_parser("read")
    location = read.add_mutually_exclusive_group(required=True)
    location.add_argument("--root")
    location.add_argument("--file")
    read.add_argument("--format", required=True, choices=list(exam_formats()))
    read.add_argument("--task")
    read.add_argument("--as-of", required=True)
    read.add_argument("--for-date")
    read.add_argument("--max-age-days", type=int, default=7)
    read.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    if args.command == "save":
        bank = validate_bank(read_json(args.input), as_of)
        root = Path(args.root) / "question-banks"
        target = root / (bank["id"] + ".json")
        with write_lock(root):
            if target.exists():
                require(read_json(target) == bank, "Snapshot ID already has different content; use a new ID")
            else:
                atomic_text(target, json.dumps(bank, ensure_ascii=False, indent=2) + "\n")
        return {"saved": True, "bank_id": bank["id"], "path": str(target.resolve()), "questions": len(bank["questions"])}
    require(args.limit > 0 and args.max_age_days >= 0, "Invalid limit or max age")
    require(not args.task or args.task in exam_formats()[args.format]["tasks"], "Unknown task for this exam")
    if args.file:
        candidates = [validate_bank(read_json(args.file), as_of)]
    else:
        paths = (Path(args.root) / "question-banks").glob("*.json")
        candidates = [validate_bank(read_json(p), as_of) for p in paths]
    candidates = [b for b in candidates if any(q["format_id"] == args.format and
                  (not args.task or q["task"] == args.task) for q in b["questions"])]
    if not candidates:
        return {"refresh_required": True, "bank_id": None, "total_matching": 0, "questions": [], "sources": []}
    # The oldest actually read source limits freshness, even if the snapshot was recently repackaged.
    bank = max(candidates, key=lambda b: (b["checked_on"], b["id"]))
    target_date = date.fromisoformat(args.for_date) if args.for_date else as_of
    return select(bank, args.format, args.task, as_of, args.max_age_days, args.limit, target_date)


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
