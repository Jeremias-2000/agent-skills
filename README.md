# agent-skills

A collection of reusable skills for coding agents.

## Available skills

- [`python-backend`](skills/python-backend/): Python backend architecture, domain-driven design, AWS Lambda, logging, testing, and quality.
- [`clean-arch-ddd-guard`](skills/clean-arch-ddd-guard/): validates a chosen Clean Architecture + DDD project layout and layer dependencies.

## Which skill should I use?

The skills address related but different questions:

| Skill | Main question | Scope |
|---|---|---|
| [`python-backend`](skills/python-backend/) | “How should I design or change this Python backend?” | General engineering guidance; architecture should be proportional to the system and can follow the project's existing conventions. |
| [`clean-arch-ddd-guard`](skills/clean-arch-ddd-guard/) | “Does this project follow the Clean Architecture + DDD layout we chose?” | Checks a specific project convention: folder placement, imports between layers, and test organization. |

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

### Do not use the guard to

- Force its directory tree onto a project that intentionally uses another architecture or naming convention.
- Treat every reported warning as a required change without inspecting the code and project context.
- Substitute its mechanical checks for a review of business rules, invariants, or whether DDD is warranted.

## About `python-backend`

A reusable Skill that guides an executing agent on clean architecture, domain-driven design principles, refactoring, and AWS Lambda best practices for Python backends.

## What it does

Activates when you're designing, scaffolding, implementing, reviewing, or refactoring any Python backend — APIs, workers, AWS Lambdas, or event-driven services. It guides the agent through:

- **Architecture decisions** — proportional complexity, module boundaries, dependency direction
- **Domain modeling** — entities, aggregates, value objects, domain services, domain events
- **Application layer** — use cases, commands/queries, ports, transaction boundaries, event publishing
- **Infrastructure** — FastAPI, SQLAlchemy, boto3, Pydantic v2, async vs sync, Lambda patterns
- **Logging & observability** — JSON logging for Lambda/CloudWatch, LoggerAdapter, structured context
- **Testing & quality** — domain unit tests, application fakes/stubs, event contract tests, architecture review checklist

## When to use it

The agent activates this skill automatically when it detects tasks related to:

- Python backend architecture or refactoring
- AWS Lambda handler design
- DDD patterns (entities, aggregates, value objects, repositories, ports)
- SQS/SNS/EventBridge consumer design
- Configuration management, logging, or observability in Python services

## Install

```bash
npx skills add https://github.com/Jeremias-2000/python-backend-engineering-skill
```

Or install directly from a local path:

```bash
npx skills add ./skills/python-backend
```

## Skill structure

```
skills/
├── python-backend/
│   ├── SKILL.md                          # general backend guidance
│   ├── evals/
│   │   └── evals.json
│   └── references/
│       ├── python-standard-architecture.md
│       ├── python-standard-domain.md
│       ├── python-standard-application.md
│       ├── python-standard-infrastructure.md
│       ├── python-standard-logging.md
│       ├── python-standard-quality.md
│       ├── python-standard-exceptions.md
│       └── python-standard-refactoring.md
└── clean-arch-ddd-guard/
    ├── SKILL.md                          # layout-specific architecture checks
    ├── scripts/check_structure.py
    └── references/
        ├── estrutura-esperada.md
        ├── checklist-ddd.md
        └── spec.json
```

Reference docs are loaded on demand — the agent only pulls in the relevant section based on the task at hand, keeping context lean. Active Skill files are normative; archived OpenSpec artifacts are historical only.

Examples labeled illustrative are intentionally abbreviated. Copyable normative examples state required imports, symbols, return behavior, and compatibility assumptions.

## Key principles enforced

- Architecture must be proportional to complexity — CRUD does not justify DDD
- Framework types (FastAPI, boto3, ORM) must never leak into domain or application code
- Configuration is loaded at the infrastructure boundary, never discovered inside business logic
- Message consumers must be designed for idempotency (at-least-once delivery)
- Every new abstraction must have a stated problem, owner, and testability benefit
- JSON structured logging for Lambda/CloudWatch; plaintext for local development
- Boundary exception handling through `exceptions.exception_handler`, with safe codes, envelopes, and transport-specific adapters
- Terminology: entrypoint is the outer boundary; adapter translates transport data; controller is an HTTP adapter; handler is a runtime or exception-mapping component

## Security notes

The `references/` directory contains Markdown documentation only — no executable scripts. This skill is safe to install and does not run any shell commands.

## License

MIT — see [LICENSE](LICENSE)
