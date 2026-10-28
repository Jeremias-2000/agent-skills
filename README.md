<div align="center">

![agent-skills banner](assets/banner.svg)

# agent-skills

**A curated collection of reusable, composable skills for coding agents.**

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-4-58a6ff)](#available-skills)
[![Format](https://img.shields.io/badge/format-SKILL.md-2ea043)](https://github.com/anthropics/skills)
[![Install](https://img.shields.io/badge/install-npx%20skills%20add-3776AB)](#installation)

</div>

Each skill is a self-contained package — a `SKILL.md` plus on-demand references, scripts, and assets — that a compatible agent loads only when the task calls for it. Install once; the agent activates the right guidance automatically.

---

## Available skills

| Skill | What it does |
|---|---|
| [`python-backend`](skills/python-backend/) | Python backend architecture, domain-driven design, AWS Lambda, logging, testing, and quality. |
| [`clean-arch-ddd-guard`](skills/clean-arch-ddd-guard/) | Validates a chosen Clean Architecture + DDD project layout and layer dependencies. |
| [`mcp-guardrails-architect`](skills/mcp-guardrails-architect/) | Designs and reviews security guardrails for MCP servers handling sensitive data. |
| [`mcp-server-skeleton`](skills/mcp-server-skeleton/) | Scaffolds and reviews Python MCP servers over Streamable HTTP with clean architecture layers, structured JSON logging, and MCP Inspector workflows. |

## Installation

Install every skill from GitHub:

```bash
npx skills add https://github.com/Jeremias-2000/agent-skills
```

Or install a single skill from a local clone:

```bash
npx skills add ./skills/python-backend
npx skills add ./skills/clean-arch-ddd-guard
npx skills add ./skills/mcp-guardrails-architect
npx skills add ./skills/mcp-server-skeleton
```

Then invoke a skill by name (for example `/python-backend`) in a compatible agent chat, or describe the task in natural language — the agent activates the matching skill on its own.

## Which skill should I use?

The skills address related but different questions:

| Skill | Main question | Scope |
|---|---|---|
| [`python-backend`](skills/python-backend/) | "How should I design or change this Python backend?" | General engineering guidance; architecture should be proportional to the system and can follow the project's existing conventions. |
| [`clean-arch-ddd-guard`](skills/clean-arch-ddd-guard/) | "Does this project follow the Clean Architecture + DDD layout we chose?" | Checks a specific project convention: folder placement, imports between layers, and test organization. |
| [`mcp-guardrails-architect`](skills/mcp-guardrails-architect/) | "How should this MCP server authenticate, validate, and protect sensitive data?" | Security architecture and review guidance for MCP tool input, execution, output, and final LLM responses. |
| [`mcp-server-skeleton`](skills/mcp-server-skeleton/) | "How do I build or extend a Python MCP server the right way?" | Reference skeleton and workflow for scaffolding MCP servers: Streamable HTTP transport, layer layout, logging, and Inspector verification. |

### Use `python-backend` when

- Starting a backend or deciding whether a small CRUD service needs layers, ports, repositories, or DDD concepts.
- Designing or implementing an API, worker, AWS Lambda, external integration, logging, configuration, or tests.
- Refactoring a backend and deciding how to preserve behavior while improving its boundaries.
- The project has its own established layout, or you have not decided to adopt the guard's template.

This skill provides recommendations and decision criteria. It does **not** require every project to have `domain/`, `application/`, and `infra/`, and it favors simpler designs when added layers do not solve a concrete problem.

### Use `clean-arch-ddd-guard` when

- The team has explicitly chosen this repository's Clean Architecture + DDD convention for the project.
- Checking whether a new or existing file belongs in the right layer.
- Reviewing imports for forbidden dependencies, such as domain code importing infrastructure or frameworks.
- Checking that required directories/files exist and unit tests are organized by layer.
- Performing an architecture review that needs both automated structural checks and the DDD checklist.

The guard is **template-specific**, not a universal definition of Clean Architecture. Its verifier expects `app/src/` by default for a regular service, or `app/bff/` for a Backend for Frontend (BFF). For a BFF, run it with `--package-name bff`. Its warnings need judgment: an extra folder is not automatically an architecture defect, and the script cannot determine whether domain modeling is meaningful just by inspecting paths and imports.

### Use both when

You are working on a project that has adopted the guard's template and need to make a design or implementation change:

1. Use `python-backend` to decide what design solves the problem without unnecessary complexity.
2. Use `clean-arch-ddd-guard` to check that the resulting files and dependencies respect the project's chosen layout.

For example, when adding an external integration, `python-backend` helps decide whether an abstraction is justified; the guard then checks whether its contract and implementation are placed in the correct layers.

**Do not use the guard to:**

- Force its directory tree onto a project that intentionally uses another architecture or naming convention.
- Treat every reported warning as a required change without inspecting the code and project context.
- Substitute its mechanical checks for a review of business rules, invariants, or whether DDD is warranted.

### Use `mcp-guardrails-architect` when

- Creating, changing, or reviewing MCP tools, resources, or prompts that handle sensitive data.
- Designing OAuth 2.1/OIDC, JWT/JWKS, scopes, MFA, or object-level authorization for an MCP Resource Server.
- Defining strict tool input schemas, output DTOs, masking, DLP, or audit logging.
- Assessing prompt injection, confused deputy, IDOR/BOLA, SSRF, token passthrough, or data exfiltration risks in an MCP/LLM integration.
- Reviewing whether security controls fail closed and what evidence/tests are needed before release.

The skill uses a six-stage pipeline: authentication and scope, input guard, tool execution, output DTO and masking, output DLP and audit, and final response validation. It is guidance and a review checklist, not a ready-made security implementation. In particular, final-response validation must run in a gateway/orchestrator/host that can inspect the LLM's final text; a standalone MCP Resource Server cannot enforce that stage by itself.

For a focused review, provide the relevant tool/schema/authentication/output code and ask for findings by pipeline stage, evidence, severity, recommendations, and uncovered acceptance tests. Do not include real credentials or production personal/payment data; use synthetic examples. The skill does not automatically install middleware, validate a deployment, or prove regulatory compliance — treat its recommendations as design and verification guidance, and confirm protocol/library details against the versions used by your project.

### Use `mcp-server-skeleton` when

- Scaffolding a new MCP server in Python.
- Adding tools or resources to an existing MCP server built on the skeleton.
- Wiring or reviewing logging, configuration, or entrypoint structure.
- Running the server with MCP Inspector for manual validation.

The package ships a canonical working example — a PokéAPI-backed server with 18 tools — plus reference docs for project layout, structured JSON logging with per-request correlation, and the Inspector handshake workflow.

## Repository structure

```
skills/
├── python-backend/
│   ├── SKILL.md                          # general backend guidance
│   ├── evals/
│   └── references/
│       ├── python-standard-architecture.md
│       ├── python-standard-domain.md
│       ├── python-standard-application.md
│       ├── python-standard-infrastructure.md
│       ├── python-standard-logging.md
│       ├── python-standard-quality.md
│       ├── python-standard-exceptions.md
│       └── python-standard-refactoring.md
├── clean-arch-ddd-guard/
│   ├── SKILL.md                          # layout-specific architecture checks
│   ├── evals/evals.json                  # behavior tests for the agent
│   ├── scripts/check_structure.py
│   └── references/
│       ├── expected-structure.md
│       ├── checklist-ddd.md
│       └── spec.json
├── mcp-guardrails-architect/
│   ├── SKILL.md                          # MCP security guardrail design and review
│   ├── evals/evals.json
│   └── scripts/check_guardrails.py       # static audit for the six-stage controls
└── mcp-server-skeleton/
    ├── SKILL.md                          # MCP server scaffolding and review workflow
    ├── evals/evals.json
    ├── app/                              # canonical reference implementation (18 tools)
    ├── tests/
    └── references/
        ├── structure.md
        ├── logging.md
        └── inspector.md
```

Every skill ships an `evals/evals.json` — behavior test cases with `expected_behaviors` and `failure_signals` that let you measure whether an agent actually applies the skill. Two skills also ship executable checkers (`check_structure.py`, `check_guardrails.py`) for deterministic, machine-verifiable enforcement.

## Validating the skills

A repo-level validator checks every skill's frontmatter, referenced files, and evals shape:

```bash
python scripts/validate_skills.py
```

It runs in CI on any change under `skills/` (see `.github/workflows/validate-skills.yml`) and exits non-zero on a missing `SKILL.md`, malformed frontmatter, a broken reference, or an unparseable evals file.

Reference docs are loaded on demand — the agent only pulls in the relevant section based on the task at hand, keeping context lean. Active skill files are normative. Examples labeled illustrative are intentionally abbreviated; copyable normative examples state required imports, symbols, return behavior, and compatibility assumptions.

## Key principles enforced

- Architecture must be proportional to complexity — CRUD does not justify DDD.
- Framework types (FastAPI, boto3, ORM) must never leak into domain or application code.
- Configuration is loaded at the infrastructure boundary, never discovered inside business logic.
- Message consumers must be designed for idempotency (at-least-once delivery).
- Every new abstraction must have a stated problem, owner, and testability benefit.
- JSON structured logging for Lambda/CloudWatch; plaintext for local development.
- Boundary exception handling through `exceptions.exception_handler`, with safe codes, envelopes, and transport-specific adapters.
- Terminology: entrypoint is the outer boundary; adapter translates transport data; controller is an HTTP adapter; handler is a runtime or exception-mapping component.

## Security notes

The skills' `references/` directories contain Markdown documentation only. The only executable scripts are the two clearly documented verifiers — `clean-arch-ddd-guard/scripts/check_structure.py` and `mcp-guardrails-architect/scripts/check_guardrails.py` — plus the repo-level `scripts/validate_skills.py`. These skills are safe to install and do not run any hidden shell commands.

## License

MIT — see [LICENSE](LICENSE).
