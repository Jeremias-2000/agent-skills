# AGENTS.md — working in the agent-skills repo

This file tells a coding agent how to add, edit, and review skills in this
repository. Follow it whenever a task touches anything under `skills/`.

## What a skill is here

A skill is a self-contained package under `skills/<name>/`:

- `SKILL.md` — required. YAML frontmatter (`name`, `description`, optional
  `compatibility`/`metadata`/`license`) plus the guidance body.
- `references/` — on-demand docs the agent loads only when relevant.
- `scripts/` — optional executable checkers (deterministic, machine-verifiable).
- `evals/evals.json` — behavior test cases for the agent.
- `assets/` — images, banners.

Keep packages lean: no `.venv/`, `__pycache__/`, `.pytest_cache/`, or local
`.env` (commit `.env.example` instead). These are gitignored — do not force-add
them.

## The quality bar (target: 9+/10)

Every skill should meet all of these. When you add or edit a skill, verify each.

1. **Valid format** — `SKILL.md` at the root; `name` matches the folder and is
   lowercase-hyphen ≤64 chars; `description` ≤1024 chars with clear activation
   triggers; every `references/`/`scripts/`/`assets/` path it mentions exists.
2. **Evals exist** — `evals/evals.json` with cases in this shape:
   `id`, `category`, `prompt`, `expected_behaviors`, `failure_signals`.
   Cover the skill's main stages/concerns, one eval per distinct behavior.
3. **Executable check where it helps** — if the skill makes claims that can be
   verified mechanically (structure, security controls, config), ship a
   `scripts/check_*.py` that exits non-zero on violations. Put deterministic
   checks in code; leave judgment to the agent.
4. **Progressive disclosure** — `SKILL.md` routes to references; it does not
   inline everything. Load-on-demand keeps agent context lean.
5. **Honest scope** — state what the skill does *not* do, its limits, and when
   *not* to use it. Cross-reference sibling skills instead of overlapping them.
6. **Normative language** — `MUST`/`SHALL` for mandatory boundaries,
   `SHOULD`/`RECOMMENDED` for defaults, `MAY` for project-defined choices.

## Workflow when adding or editing a skill

1. Create or update the package under `skills/<name>/`.
2. Write or update `evals/evals.json` for the behaviors you changed.
3. If you added a mechanical claim, add or update a `scripts/check_*.py`.
4. Run the validator and fix everything it reports:

   ```bash
   python scripts/validate_skills.py
   ```

5. If the skill has a checker, run it against a real target to confirm it works:

   ```bash
   python skills/<name>/scripts/check_<x>.py <some-project-root>
   ```

6. Update `README.md`: the "Available skills" table, the "Which skill should I
   use?" table, and the repository-structure tree.

The validator also runs in CI on any change under `skills/`
(`.github/workflows/validate-skills.yml`). A green local run should mean a
green CI run.

## Reviewing or rating a skill

When asked to rate or review a skill, score against the rubric in section
"The quality bar" and report per-skill. Note gaps against it (missing evals,
missing checker, broken references, overlapping scope) and recommend the
smallest change that closes each gap. Prefer raising a weak skill's floor over
polishing an already-strong one.

## Conventions

- Windows/PowerShell is the primary dev environment; keep scripts
  cross-platform and avoid non-ASCII output in CLI tools (cp1252-safe).
- Scripts print ASCII-only status markers (`[OK]`/`[ERR]`/`[WARN]`), support
  `--json` for structured output and `--strict` to treat warnings as errors,
  and use exit codes 0/1/2 (ok / findings / usage error).
- Don't commit secrets. Reference docs are Markdown-only; the only executables
  are the documented checkers and `scripts/validate_skills.py`.
