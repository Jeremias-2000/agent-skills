# agent-skills

A collection of reusable skills for coding agents.

## Available skills

- [`python-backend`](skills/python-backend/): Python backend architecture, domain-driven design, AWS Lambda, logging, testing, and quality.

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
└── python-backend/
    ├── SKILL.md                          # skill definition and workflow
    ├── evals/
    │   └── evals.json                    # evaluation scenarios for skill quality
    └── references/
        ├── python-standard-architecture.md
        ├── python-standard-domain.md
        ├── python-standard-application.md
        ├── python-standard-infrastructure.md
        ├── python-standard-logging.md
        ├── python-standard-quality.md
        ├── python-standard-exceptions.md
        └── python-standard-refactoring.md
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
