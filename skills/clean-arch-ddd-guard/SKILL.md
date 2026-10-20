---
name: clean-arch-ddd-guard
description: Checks Python projects against this skill's Clean Architecture + DDD folder convention and detects dependencies between layers. Use when a project adopts this template, to audit its structure, or to locate files. `src/` is the default for regular services; `bff/` is reserved for Backend for Frontend.
---

# Clean Architecture + DDD Guard

This skill validates a project convention based on Clean Architecture and Domain-Driven Design. Use it when a team has adopted this structure and wants to audit directories, imports, and test placement. It does not prescribe these layers for every Python backend; for general guidance and proportionate architecture choices, use `python-backend`.

## Expected structure

The reference structure and each directory's responsibility are documented in `references/expected-structure.md`. The `app/` directory is the code root; use exactly one internal package, depending on the application type:

```
app/
├── src/                    # regular Python service (default)
│   ├── application/        configuration/ · gateways/ · usecases/
│   ├── domain/             config/ · dtos/ · entities/ · interfaces/{adapters,gateways,usecases}/
│   └── infra/              adapters/ · controllers/
│                           di/ · entrypoints/ · exceptions/ · setup/
├── tests/
│   ├── integration/health_check/
│   └── unitary/{application,domain,infra}/
├── requirements.txt
├── requirements_tests.txt
├── pytest.ini
├── logging.conf
├── Dockerfile
└── run.py
```

For BFF projects, use `bff/` instead of `src/`, keeping the same layers and subdirectories. The original reference tree is truncated (it contains ellipses), so extra directories are not automatically errors. Treat directories or files outside the schema as *warnings* to confirm with the user. Only missing required directories or files are *errors*.

Subdirectories of `controllers/` represent business modules and vary by project; they are not globally required directories.

## Workflow

### 1. Run the checker

The script handles mechanical checks (directory existence, imports between layers, and frameworks in the domain). These checks are deterministic and should not depend on your interpretation.

```bash
python <skill-dir>/scripts/check_structure.py <project-root>
```

- `<project-root>` is the `app/` directory or its parent. The script locates it automatically.
- `src/` is the default for regular services. For a BFF, add `--package-name bff`.
- BFF example: `python <skill-dir>/scripts/check_structure.py <project-root> --package-name bff`.
- Use `--json` for structured output and `--strict` to treat warnings as errors (useful in CI).
- The script exits with code 1 when errors are found.

### 2. Interpret the results using DDD principles

The script cannot inspect what happens inside classes. After running it, read the files it flags and apply `references/checklist-ddd.md` to look for anemic entities, business rules leaking into controllers, DTOs used in place of entities, contracts without implementations, and similar issues. Consult this checklist whenever reviewing more than folder structure.

### 3. Report actionable findings

Group findings by severity and always say *where the file should be* and *why*. Suggested format:

```
## Results
✅ N checks passed · ❌ N errors · ⚠️ N warnings

## Errors
- `app/src/domain/entities/order.py:3` imports `src.infra...`
  → the domain cannot depend on infrastructure. Create the interface in `domain/interfaces/adapters/` and inject the implementation through `infra/di/`.

## Warnings
- `app/src/utils/` is not part of the schema. If it is a domain helper, move it to `domain/`; if it is technical, move it to `infra/`.

## Suggested fix
(Use `mkdir`/`git mv` commands or provide a diff if the user asks you to apply it.)
```

Do not move or delete files unless the user asks. Propose a plan and wait for confirmation, because moving files can break imports and history.

### 4. Choose the layer before writing new code in a project that adopted this template

Use this decision table:

| I am creating… | Put it in | Notes |
|---|---|---|
| Business rule, object with identity or behavior | `domain/entities/` | Pure Python; no frameworks |
| Data structure passed between layers | `domain/dtos/` | No business logic |
| Contract (ABC/Protocol) for a use case, gateway, or adapter | `domain/interfaces/{usecases,gateways,adapters}/` | Signature only |
| Configuration interface | `domain/config/` | Contract only |
| Use-case orchestration | `application/usecases/` | Implements an interface from `domain/interfaces/usecases/` |
| Application access to an external system | `application/gateways/` | Implements an interface from `domain/interfaces/gateways/` |
| Reading/loading application configuration | `application/configuration/` | |
| HTTP client, database, queue, external SDK | `infra/adapters/` | Implements an interface from `domain/interfaces/adapters/` |
| REST endpoint | `infra/controllers/<module>/` | Keep it thin: validate input, call a use case, format the response |
| Dependency wiring | `infra/di/` | The only place that knows all implementations |
| Entry point (app factory, handlers) | `infra/entrypoints/` | |
| Custom exception | `infra/exceptions/` | |
| Bootstrap, logging, initialization | `infra/setup/` | |
| Test | `tests/unitary/<layer>/` or `tests/integration/` | Mirrors the layer being tested |

If the user's request does not make the right location clear, choose based on the table, state your choice in one line, and proceed.

## Dependency rule

Dependencies point inward: `infra → application → domain`. Inner layers never know about outer layers.

- `domain` does not import `application`, `infra`, or frameworks (FastAPI, Flask, SQLAlchemy, requests, boto3, transport-layer Pydantic, etc.). This keeps the core testable without starting external services and lets you replace infrastructure without rewriting business rules.
- `application` imports `domain`, not `infra`. It communicates with the outside world only through domain interfaces.
- `infra` can import `domain` and `application`. This is where concrete implementations are wired together (through `di/`).
- `tests/` can import any layer, but each unit test should live in the directory for the layer it tests.

The script checks these rules by statically analyzing imports (including resolving relative imports).

## When a project does not match the schema

For regular services, use the `src/` package (the default); for BFFs, use `bff/` and run the checker with `--package-name bff`. If the root or other conventions differ, do not invent a large number of errors. Explain the mismatch and adapt a copy of `references/spec.json` using `--spec my_spec.json`.

## Skill files

- `scripts/check_structure.py`: checker (structure, dependencies, frameworks in the domain, and test mirroring).
- `references/expected-structure.md`: complete tree with each directory's responsibility.
- `references/checklist-ddd.md`: review checklist for concerns static analysis cannot detect.
- `references/spec.json`: the data-format schema used by the script (editable).