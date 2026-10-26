#!/usr/bin/env python3
"""Check catalog identity, local links, syntax, and distributable file hygiene."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "skills/bella-skill"
spec = importlib.util.spec_from_file_location("discovery", MAIN / "scripts/list_skills.py")
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def main() -> int:
    errors = []
    catalog = json.loads((MAIN / "references/catalog.json").read_text(encoding="utf-8"))
    entries = catalog["skills"]
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)):
        errors.append("Duplicate catalog member names")
    expected = {MAIN / "SKILL.md"} | {ROOT / "skills" / entry["path"] / "SKILL.md" for entry in entries}
    actual = set((ROOT / "skills").rglob("SKILL.md"))
    if expected != actual:
        errors.append(f"Catalog/discovery mismatch: {expected ^ actual}")
    for row in discovery.discover(MAIN):
        if row["status"] != "available":
            errors.append(f"Unavailable member: {row['name']} ({row['status']})")
        if not re.fullmatch(r"[0-9a-f]{40}", row["commit"]):
            errors.append(f"Invalid source commit: {row['name']}")
    for definition in sorted(actual):
        data = discovery.frontmatter(definition)
        if data["name"] != definition.parent.name:
            errors.append(f"Name/directory mismatch: {definition}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["name"]):
            errors.append(f"Invalid skill name: {definition}")
        if not 1 <= len(data["description"]) <= 1024:
            errors.append(f"Description length: {definition}")
        ui = definition.parent / "agents/openai.yaml"
        if not ui.is_file() or "$" + data["name"] not in ui.read_text(encoding="utf-8"):
            errors.append(f"Missing/inconsistent UI metadata: {definition.parent}")
    text_suffixes = {
        ".md", ".py", ".json", ".yaml", ".yml", ".sh", ".txt", ".html",
        ".js", ".mjs", ".cjs", ".css", ".svg", ".toml", ".lrc", ".srt", ".vtt",
    }
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(p in {".git", "__pycache__", ".venv", "node_modules"} for p in rel.parts):
            continue
        if path.is_symlink():
            errors.append(f"Symlink in distribution: {rel}")
            continue
        if not path.is_file():
            continue
        if path.name.startswith(".env") or path.name == ".DS_Store" or "evals" in rel.parts:
            errors.append(f"Private/generated file in distribution: {rel}")
        if path.suffix not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        if path.resolve() != Path(__file__).resolve() and re.search(r"(?:/Users/[^/\s]+/|/home/[^/\s]+/)", text):
            errors.append(f"Personal absolute path: {rel}")
        if re.search(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})\b", text):
            errors.append(f"Credential-like string: {rel}")
        if path.suffix == ".md":
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = link.split("#", 1)[0].strip().strip("<>")
                if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                resolved = (path.parent / unquote(target)).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    errors.append(f"Broken/local-external link: {rel} -> {target}")
        elif path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".py":
            compile(text, str(path), "exec")
        elif path.suffix == ".sh":
            result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
            if result.returncode:
                errors.append(f"Shell syntax error: {rel}: {result.stderr}")
    for error in errors:
        print("ERROR:", error)
    if errors:
        return 1
    print(f"Collection checks passed: {len(actual)} skills, {len(entries)} routed members, 4 categories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
