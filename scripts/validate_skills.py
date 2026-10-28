#!/usr/bin/env python3
"""Validate every skill package in this repository.

For each skills/<name>/ directory this checks:
  1. SKILL.md exists at the package root.
  2. The YAML frontmatter is present and parses.
  3. `name` matches the folder name and is lowercase-hyphen, <= 64 chars.
  4. `description` is present and <= 1024 chars.
  5. Every `references/...`, `scripts/...`, `assets/...` path mentioned in
     SKILL.md actually exists in the package.
  6. Any evals/evals.json parses and each eval has the required keys.

Usage:
    python scripts/validate_skills.py [--json]

Exit codes: 0 all valid, 1 one or more problems, 2 invalid usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Paths the SKILL.md body points at, e.g. references/foo.md, scripts/x.py
REF_RE = re.compile(r"\b((?:references|scripts|assets|evals)/[\w./-]+)")

REQUIRED_EVAL_KEYS = {"id", "category", "prompt", "expected_behaviors", "failure_signals"}


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    data: dict = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        if line[:1].isspace():
            continue  # skip nested keys (e.g. under metadata:)
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate_skill(skill_dir: Path, problems: list[dict]) -> None:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        problems.append({"skill": name, "code": "MISSING_SKILL_MD", "message": "SKILL.md not found at package root."})
        return

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm is None:
        problems.append({"skill": name, "code": "BAD_FRONTMATTER", "message": "Missing or malformed YAML frontmatter block."})
        return

    # name
    fm_name = fm.get("name", "")
    if fm_name != name:
        problems.append({"skill": name, "code": "NAME_MISMATCH", "message": f"frontmatter name '{fm_name}' != folder '{name}'."})
    if not NAME_RE.match(fm_name) or len(fm_name) > 64:
        problems.append({"skill": name, "code": "NAME_FORMAT", "message": f"name '{fm_name}' is not lowercase-hyphen or exceeds 64 chars."})

    # description
    desc = fm.get("description", "")
    if not desc:
        problems.append({"skill": name, "code": "MISSING_DESCRIPTION", "message": "frontmatter description is empty."})
    elif len(desc) > 1024:
        problems.append({"skill": name, "code": "DESCRIPTION_TOO_LONG", "message": f"description is {len(desc)} chars (limit 1024)."})

    # referenced paths exist
    for ref in sorted(set(REF_RE.findall(text))):
        if not (skill_dir / ref).exists():
            problems.append({"skill": name, "code": "BROKEN_REFERENCE", "message": f"referenced path not found: {ref}"})

    # evals parse + shape
    evals_file = skill_dir / "evals" / "evals.json"
    if evals_file.is_file():
        try:
            data = json.loads(evals_file.read_text(encoding="utf-8"))
            for i, ev in enumerate(data.get("evals", [])):
                missing = REQUIRED_EVAL_KEYS - set(ev)
                if missing:
                    problems.append({"skill": name, "code": "EVAL_SHAPE", "message": f"eval #{i} missing keys: {sorted(missing)}"})
        except json.JSONDecodeError as e:
            problems.append({"skill": name, "code": "EVAL_JSON", "message": f"evals.json does not parse: {e}"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate all skill packages.")
    ap.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    args = ap.parse_args(argv)

    if not SKILLS_DIR.is_dir():
        print(f"error: skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    problems: list[dict] = []
    skills = [d for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir()]
    for skill_dir in skills:
        validate_skill(skill_dir, problems)

    if args.json:
        print(json.dumps({"skills_checked": len(skills), "problems": problems}, indent=2))
    else:
        print(f"Checked {len(skills)} skills: {', '.join(d.name for d in skills)}")
        if problems:
            print(f"\n{len(problems)} problem(s):")
            for p in problems:
                print(f"  [{p['code']}] {p['skill']}: {p['message']}")
        else:
            print("All skills valid.")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
