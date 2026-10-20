#!/usr/bin/env python3
"""Check whether a project follows the expected Clean Architecture + DDD structure.

Usage:
    python check_structure.py <project-root> [--package-name src|bff] [--spec spec.json] [--json] [--strict]

Checks:
  1. Required directories and files exist (error if missing).
  2. Directories/files outside the schema (warning).
  3. Stray .py files within layers (warning).
  4. Dependency rule between layers via AST (error).
  5. Forbidden frameworks in domain/application (error).
  6. Unit tests are in the correct layer directory (warning).

Exit codes: 0 no errors, 1 with errors (or warnings, with --strict), 2 invalid usage.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

DEFAULT_SPEC = Path(__file__).resolve().parent.parent / "references" / "spec.json"
PACKAGE_TOKEN = "{package_name}"


class Report:
    def __init__(self) -> None:
        self.ok = 0
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def passed(self) -> None:
        self.ok += 1

    def error(self, code: str, path: str, message: str, hint: str = "", line: int | None = None) -> None:
        self.errors.append({"code": code, "path": path, "line": line, "message": message, "hint": hint})

    def warn(self, code: str, path: str, message: str, hint: str = "", line: int | None = None) -> None:
        self.warnings.append({"code": code, "path": path, "line": line, "message": message, "hint": hint})


def find_root(start: Path, root_name: str, package: str) -> Path | None:
    """Accept the app/ directory itself, its parent, or an ancestor directory."""
    candidates = [start, start / root_name]
    candidates += [p for p in start.glob(f"*/{root_name}")]
    for c in candidates:
        if c.is_dir() and (c / package).is_dir():
            return c
    for c in candidates:
        if c.is_dir() and c.name == root_name:
            return c
    return None


def substitute_package_name(value, package_name: str):
    """Replace the package marker in the structural parts of the spec."""
    if isinstance(value, str):
        return value.replace(PACKAGE_TOKEN, package_name)
    if isinstance(value, list):
        return [substitute_package_name(item, package_name) for item in value]
    if isinstance(value, dict):
        return {
            substitute_package_name(key, package_name): substitute_package_name(item, package_name)
            for key, item in value.items()
        }
    return value


def iter_py(base: Path, ignore: set[str]):
    for p in sorted(base.rglob("*.py")):
        if any(part in ignore for part in p.parts):
            continue
        yield p


def layer_of(parts: tuple[str, ...], package: str, layers: list[str]) -> str | None:
    """Find a layer in a path/module by locating <package> followed by a layer."""
    for i, part in enumerate(parts[:-1]):
        if part == package and parts[i + 1] in layers:
            return parts[i + 1]
    return None


def resolve_import(node: ast.AST, file_parts: tuple[str, ...], root: Path, file_path: Path) -> list[tuple[str, ...]]:
    """Return imported modules as tuples of segments (with relative imports resolved)."""
    out: list[tuple[str, ...]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            out.append(tuple(alias.name.split(".")))
    elif isinstance(node, ast.ImportFrom):
        mod = tuple(node.module.split(".")) if node.module else ()
        if node.level:
            pkg_dir = file_path.parent.relative_to(root.parent).parts
            up = node.level - 1
            base = pkg_dir[: len(pkg_dir) - up] if up <= len(pkg_dir) else ()
            out.append(base + mod)
            for alias in node.names:  # from . import domain
                out.append(base + mod + (alias.name,))
        else:
            out.append(mod)
            for alias in node.names:  # from bff import domain
                out.append(mod + (alias.name,))
    return out


def check_structure(root: Path, spec: dict, rep: Report) -> None:
    ignore = set(spec["ignore_names"])
    for d in spec["required_dirs"]:
        if (root / d).is_dir():
            rep.passed()
        else:
            rep.error("MISSING_DIR", f"{root.name}/{d}", "Required directory is missing.",
                      f"Create `{root.name}/{d}/` (with `__init__.py` if it is a Python package).")
    for f in spec["required_files"]:
        if (root / f).is_file():
            rep.passed()
        else:
            rep.error("MISSING_FILE", f"{root.name}/{f}", "Required file is missing.",
                      f"Create `{root.name}/{f}`.")

    for parent, allowed in spec["allowed_children"].items():
        base = root / parent
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.name in ignore or child.name.startswith(".") or child.name == "__init__.py":
                continue
            if child.is_dir() and child.name not in allowed:
                rep.warn("UNEXPECTED_DIR", f"{root.name}/{parent}/{child.name}",
                         "Directory is outside the expected schema.",
                         f"If it contains business code, move it to `domain/`; if it is technical, move it to `infra/`. "
                         f"If it is intentional, add it to the spec.")
            elif child.is_file() and child.suffix == ".py":
                rep.warn("STRAY_FILE", f"{root.name}/{parent}/{child.name}",
                         "Stray .py file; layers should organize code in subdirectories.",
                         f"Move it to one of these subdirectories: {', '.join(allowed)}.")


def check_dependencies(root: Path, spec: dict, rep: Report) -> None:
    package = spec["package_name"]
    layers = spec["layers"]
    rules = spec["dependency_rules"]
    forb = {
        "domain": set(spec.get("forbidden_in_domain", [])),
        "application": set(spec.get("forbidden_in_application", [])),
    }
    ignore = set(spec["ignore_names"])
    checked = 0
    for py in iter_py(root / package, ignore):
        rel = py.relative_to(root.parent).parts
        src_layer = layer_of(rel, package, layers)
        if not src_layer:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError) as exc:
            rep.warn("PARSE", str(py.relative_to(root.parent)), f"Could not parse: {exc}")
            continue
        checked += 1
        seen: set[tuple] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for mod in resolve_import(node, rel, root, py):
                if not mod:
                    continue
                shown = str(py.relative_to(root.parent))
                tgt_layer = layer_of(mod + ("_",), package, layers)
                key = (node.lineno, tgt_layer, mod[0])
                if key in seen:  # `from a.b import c` gera a.b e a.b.c: reporta uma vez
                    continue
                seen.add(key)
                if tgt_layer and tgt_layer != src_layer and tgt_layer not in rules[src_layer]:
                    allowed = ", ".join(rules[src_layer]) or "no other layers"
                    rep.error("LAYER_VIOLATION", shown,
                              f"`{src_layer}` importa `{tgt_layer}` ({'.'.join(mod)}).",
                              f"`{src_layer}` may depend only on: {allowed}. "
                              f"Declare the interface in `domain/interfaces/` and inject the implementation through `infra/di/`.",
                              node.lineno)
                top = mod[0]
                if src_layer in forb and top in forb[src_layer]:
                    rep.error("FRAMEWORK_IN_" + src_layer.upper(), shown,
                              f"`{src_layer}` importa a biblioteca tecnica `{top}`.",
                              "Technical details belong in `infra/adapters/` behind a domain interface.",
                              node.lineno)
    if checked:
        rep.passed()


def check_tests_mirror(root: Path, spec: dict, rep: Report) -> None:
    tests = root / "tests" / "unitary"
    if not tests.is_dir():
        return
    ignore = set(spec["ignore_names"])
    package = spec["package_name"]
    layers = spec["layers"]
    for py in iter_py(tests, ignore):
        if py.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        in_layer = py.relative_to(tests).parts[0]
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for mod in resolve_import(node, (), root, py):
                    lay = layer_of(mod + ("_",), package, layers)
                    if lay:
                        imported.add(lay)
        if imported and in_layer in layers and in_layer not in imported:
            rep.warn("TEST_PLACEMENT", str(py.relative_to(root.parent)),
                     f"Test is in `unitary/{in_layer}/` but imports only {', '.join(sorted(imported))}.",
                     f"Move it to `tests/unitary/{sorted(imported)[0]}/` if it tests that layer.")
        else:
            rep.passed()


def render_text(rep: Report, root: Path) -> str:
    lines = [f"Analyzed project: {root}",
             f"✅ {rep.ok} checks passed · ❌ {len(rep.errors)} errors · ⚠️  {len(rep.warnings)} warnings", ""]
    for title, items in (("ERRORS", rep.errors), ("WARNINGS", rep.warnings)):
        if not items:
            continue
        lines.append(title)
        for it in items:
            loc = it["path"] + (f":{it['line']}" if it["line"] else "")
            lines.append(f"- [{it['code']}] {loc}\n    {it['message']}")
            if it["hint"]:
                lines.append(f"    → {it['hint']}")
        lines.append("")
    if not rep.errors and not rep.warnings:
        lines.append("Structure and dependencies conform to the schema.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".", help="app/ directory or its parent")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC), help="schema in JSON format")
    ap.add_argument("--package-name", choices=("src", "bff"), default="src",
                    help="internal package name: src (regular service, default) or bff (Backend for Frontend)")
    ap.add_argument("--json", action="store_true", help="output in JSON format")
    ap.add_argument("--strict", action="store_true", help="warnings also cause failure")
    args = ap.parse_args()

    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Invalid spec: {exc}", file=sys.stderr)
        return 2

    spec = substitute_package_name(spec, args.package_name)
    spec["package_name"] = args.package_name

    start = Path(args.project).resolve()
    root = find_root(start, spec["root_name"], spec["package_name"])
    if root is None:
        print(f"Could not find `{spec['root_name']}/{spec['package_name']}` in {start}. "
              f"Use --spec to adapt the schema to the project's names.", file=sys.stderr)
        return 2

    rep = Report()
    check_structure(root, spec, rep)
    check_dependencies(root, spec, rep)
    check_tests_mirror(root, spec, rep)

    if args.json:
        print(json.dumps({"root": str(root), "ok": rep.ok, "errors": rep.errors, "warnings": rep.warnings},
                         ensure_ascii=False, indent=2))
    else:
        print(render_text(rep, root))
    return 1 if rep.errors or (args.strict and rep.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())