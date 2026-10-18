#!/usr/bin/env python3
"""Discover catalogued skills in a source checkout or a flattened installation."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.S)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")
    lines = match.group(1).splitlines()
    result = {}
    for i, line in enumerate(lines):
        found = re.match(r"^(name|description):\s*(.*)$", line)
        if not found:
            continue
        key, value = found.groups()
        if value in ("|", ">", "|-", ">-"):
            parts = []
            for continuation in lines[i + 1:]:
                if continuation.strip() and not continuation[0].isspace():
                    break
                parts.append(continuation.strip())
            value = ("\n" if value.startswith("|") else " ").join(parts).strip()
        elif value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        result[key] = value
    if not result.get("name") or not result.get("description"):
        raise ValueError(f"Missing name or description: {path}")
    return result


def discover(skill_root: Path | None = None, category: str | None = None) -> list[dict]:
    root = (skill_root or Path(__file__).resolve().parents[1]).resolve()
    catalog = json.loads((root / "references/catalog.json").read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ValueError("Unsupported catalog schema")
    results = []
    for entry in catalog["skills"]:
        if category and entry["category"] != category:
            continue
        name = entry["name"]
        relative = Path(entry["path"])
        if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
                or relative.is_absolute() or ".." in relative.parts
                or relative.name != name):
            raise ValueError(f"Invalid catalog entry: {name}")
        # skills/<category>/<name> in source; <skills-home>/<name> after install.
        candidates = [root.parent / relative, root.parent / name]
        found, issues = [], []
        for candidate in candidates:
            definition = candidate / "SKILL.md"
            if not definition.is_file():
                continue
            try:
                actual = frontmatter(definition)
                if actual["name"] != name:
                    issues.append(f"Name mismatch at {definition}")
                    continue
                found.append((definition.resolve(), actual))
            except (ValueError, OSError) as exc:
                issues.append(str(exc))
        row = dict(entry, status="missing", skill_file=None, description=None)
        if found:
            definition, actual = found[0]
            row.update(status="available", skill_file=str(definition), description=actual["description"])
            if any(p.read_bytes() != definition.read_bytes() for p, _ in found[1:]):
                issues.append("Conflicting categorized and flat definitions")
        if issues:
            row.update(status="conflict", issues=issues)
        results.append(row)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", choices=["english", "research", "media", "game-3d"])
    parser.add_argument("--check", action="store_true", help="Return nonzero for missing/conflicting members")
    args = parser.parse_args()
    try:
        rows = discover(category=args.category)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Catalog error: {exc}\n")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return int(args.check and any(row["status"] != "available" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
