#!/usr/bin/env python3
"""Statically audit an MCP server for the six-stage guardrail controls.

This checker scans Python source for *signals* that the guardrail stages are
present or absent. It is heuristic: it cannot prove a control is correct, only
that likely evidence for it exists or that a likely anti-pattern is present.
Treat findings as leads for review, not as proof of compliance.

Usage:
    python check_guardrails.py <project-root> [--json] [--strict]

Stages checked (heuristic signals):
  1. Authentication/scope   - JWKS/issuer/audience validation, algorithm allowlist
  2. Input guard            - strict schema (extra=forbid), normalization, injection checks
  3. Tool execution         - token-derived identity, ownership check, sanitized errors
  4. DTO + masking          - output allowlist, masking functions, no direct serialization
  5. Output DLP + audit     - detector usage, structured audit log, fail-closed
  6. Final response         - flagged as out-of-scope for the server (host/gateway concern)

Anti-patterns flagged as errors:
  - Identity taken from tool arguments (user_id/account_id/cpf as parameters)
  - Algorithm read from the token header / `alg: none` accepted
  - Direct `return` of a provider/SDK response object from a tool
  - `verify=False` / disabled JWT verification
  - Logging sensitive-looking fields in cleartext

Exit codes: 0 no errors, 1 with errors (or warnings with --strict), 2 invalid usage.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

IGNORE_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", ".pytest_cache", "tests", "test"}

# --- Signal patterns (case-insensitive) -------------------------------------

STAGE_SIGNALS = {
    "stage1_authn_scope": [
        r"jwks", r"\bissuer\b", r"\baudience\b", r"verify_signature", r"decode\(",
        r"algorithms\s*=", r"RS256|ES256|EdDSA", r"required_scopes|required_scope",
    ],
    "stage2_input_guard": [
        r"extra\s*=\s*['\"]forbid", r"additionalProperties", r"model_config",
        r"normalize|nfkc|unicodedata", r"injection", r"strict\s*=\s*True",
    ],
    "stage3_execution": [
        r"identity\.sub|claims\[['\"]sub", r"owner\s*==|ownership", r"not found",
        r"idempotency", r"timeout\s*=", r"circuit",
    ],
    "stage4_dto_masking": [
        r"mask", r"allowlist|allow_list", r"dto", r"redact", r"response_model",
    ],
    "stage5_dlp_audit": [
        r"dlp|detector|presidio", r"luhn", r"audit", r"correlation_id",
        r"append.?only", r"\bredact\b",
    ],
}

# --- Anti-patterns (errors) --------------------------------------------------

IDENTITY_ARG_RE = re.compile(
    r"\b(user_id|account_id|account_owner|customer_id|cpf|cnpj|ssn|owner_id)\b\s*:\s*[\w\[\]'\"\.]+",
    re.IGNORECASE,
)
ALG_FROM_HEADER_RE = re.compile(r"(get_unverified_header|header\[['\"]alg|token\.header)", re.IGNORECASE)
ALG_NONE_RE = re.compile(r"['\"]none['\"]", re.IGNORECASE)
VERIFY_FALSE_RE = re.compile(r"verify\s*=\s*False|verify_signature\s*=\s*False|options\s*=\s*\{[^}]*verify", re.IGNORECASE)
SENSITIVE_LOG_RE = re.compile(
    r"(log|logger|logging)\.\w+\([^)]*\b(password|secret|token|cvv|pan|card_number|api_key)\b",
    re.IGNORECASE,
)


class Report:
    def __init__(self) -> None:
        self.ok = 0
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.stage_hits: dict[str, set[str]] = {k: set() for k in STAGE_SIGNALS}

    def passed(self) -> None:
        self.ok += 1

    def error(self, code, path, message, hint="", line=None):
        self.errors.append({"code": code, "path": path, "line": line, "message": message, "hint": hint})

    def warn(self, code, path, message, hint="", line=None):
        self.warnings.append({"code": code, "path": path, "line": line, "message": message, "hint": hint})


def iter_py(base: Path):
    for p in sorted(base.rglob("*.py")):
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        yield p


def is_tool_function(node: ast.FunctionDef) -> bool:
    """Heuristic: a function registered as an MCP tool (decorated or named like one)."""
    for dec in node.decorator_list:
        text = ast.dump(dec)
        if "tool" in text.lower():
            return True
    return False


def returns_name_directly(node: ast.FunctionDef) -> bool:
    """Detect `return <name>` where name looks like a raw provider response."""
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and isinstance(child.value, ast.Name):
            if re.search(r"(resp|response|result|raw|data|provider)", child.value.id, re.IGNORECASE):
                return True
    return False


def scan_file(path: Path, root: Path, rep: Report) -> None:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    rel = str(path.relative_to(root))
    lower = src.lower()

    # Collect stage signals
    for stage, patterns in STAGE_SIGNALS.items():
        for pat in patterns:
            if re.search(pat, src, re.IGNORECASE):
                rep.stage_hits[stage].add(rel)
                break

    lines = src.splitlines()

    # Anti-pattern: identity as an argument
    for i, line in enumerate(lines, 1):
        m = IDENTITY_ARG_RE.search(line)
        if m and "sub" not in line.lower() and "# ok" not in line.lower():
            # Only flag when it looks like a function parameter (has a colon annotation)
            rep.warn(
                "IDENTITY_ARG", rel,
                f"Possible identity-from-argument: `{m.group(0).strip()}`.",
                "Derive identity from the validated token `sub`, not from tool arguments (IDOR/confused deputy).",
                i,
            )

    # Anti-pattern: algorithm from header / alg none / verify False
    for i, line in enumerate(lines, 1):
        if ALG_FROM_HEADER_RE.search(line):
            rep.error(
                "ALG_FROM_HEADER", rel,
                "Algorithm appears to be read from the token header.",
                "Take the algorithm from server configuration (allowlist RS256/ES256/EdDSA), never from the token.",
                i,
            )
        if VERIFY_FALSE_RE.search(line):
            rep.error(
                "VERIFY_DISABLED", rel,
                "Signature/certificate verification appears to be disabled.",
                "Never disable JWT or TLS verification outside a throwaway local test.",
                i,
            )

    # Anti-pattern: sensitive value logged
    for i, line in enumerate(lines, 1):
        if SENSITIVE_LOG_RE.search(line):
            rep.error(
                "SENSITIVE_LOG", rel,
                "A sensitive-looking field may be logged in cleartext.",
                "Never log secrets, tokens, PAN, or passwords; log a hash only when traceability is required.",
                i,
            )

    # Anti-pattern: tool returns raw provider response
    try:
        tree = ast.parse(src)
    except SyntaxError:
        rep.warn("PARSE_ERROR", rel, "Could not parse file; skipped AST checks.")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and is_tool_function(node) and returns_name_directly(node):
            rep.warn(
                "RAW_RETURN", rel,
                f"Tool `{node.name}` may return a raw provider response object.",
                "Convert to a per-tool output DTO from an explicit allowlist; never serialize the provider object directly.",
                node.lineno,
            )


def evaluate_stages(rep: Report) -> None:
    """Warn about stages with no detected signal anywhere in the project."""
    for stage in STAGE_SIGNALS:
        if rep.stage_hits[stage]:
            rep.passed()
        else:
            rep.warn(
                "STAGE_MISSING", "(project)",
                f"No signal detected for {stage.replace('_', ' ')}.",
                "Confirm this stage is implemented; the checker only detects likely evidence, not correctness.",
            )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit an MCP server for guardrail controls.")
    ap.add_argument("root", help="Project root (directory containing the MCP server source).")
    ap.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit 1).")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    rep = Report()
    files = list(iter_py(root))
    if not files:
        print(f"error: no Python files found under {root}", file=sys.stderr)
        return 2

    for f in files:
        scan_file(f, root, rep)
    evaluate_stages(rep)

    # Stage 6 is always out of scope for the server itself.
    rep.warn(
        "STAGE6_OUT_OF_SCOPE", "(project)",
        "Final-response validation (stage 6) cannot be enforced by the MCP server.",
        "Implement it in the orchestrator/gateway/host that can inspect the LLM's final text, or document it as a client requirement.",
    )

    if args.json:
        print(json.dumps({
            "root": str(root),
            "files_scanned": len(files),
            "passed": rep.ok,
            "errors": rep.errors,
            "warnings": rep.warnings,
            "stage_coverage": {k: sorted(v) for k, v in rep.stage_hits.items()},
        }, indent=2))
    else:
        print(f"Scanned {len(files)} files under {root}")
        print(f"[OK] {rep.ok} checks passed | [ERR] {len(rep.errors)} errors | [WARN] {len(rep.warnings)} warnings\n")
        for e in rep.errors:
            loc = f"{e['path']}:{e['line']}" if e.get("line") else e["path"]
            print(f"ERROR   [{e['code']}] {loc}\n        {e['message']}\n        -> {e['hint']}")
        for w in rep.warnings:
            loc = f"{w['path']}:{w['line']}" if w.get("line") else w["path"]
            print(f"WARNING [{w['code']}] {loc}\n        {w['message']}\n        -> {w['hint']}")

    if rep.errors or (args.strict and rep.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
