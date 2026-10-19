---
name: python-backend-engineering
description: "Python backend engineering standards for architecture, domain modeling, application layers, AWS Lambda, logging, testing, and quality. Activate when designing, scaffolding, implementing, reviewing, or refactoring any Python backend, API, worker, or Lambda - including architecture decisions, DDD patterns, ports and adapters, configuration, observability, and idempotency."
compatibility: "Python 3.8+, existing project tooling, and the project's configured test and lint commands."
metadata:
  version: "1.0.0"
  author: "Jeremias dos Santos Pinheiro"
license: MIT
---

# Python Backend Engineering Skill

This package is a reusable Skill that guides an executing agent. It is not an autonomous Agent implementation.

Normative language: `MUST`/`SHALL` marks mandatory boundaries; `SHOULD`/`RECOMMENDED` marks defaults; `MAY` marks project-defined choices.

Use the smallest architecture that preserves business boundaries, testability, maintainability, and dependency direction. Let the problem determine the patterns: `Simple -> Modular -> Layered -> Hexagonal -> DDD`.

When refactoring an existing Python backend, load `references/python-standard-refactoring.md`. For new projects, target `app/` and `app/tests/`; preserve coherent existing layouts such as top-level `tests/` unless migration has a concrete benefit.

Active files in this package are normative. Files under `openspec/changes/archive/` are historical planning artifacts, not executable guidance.

## Workflow

1. Inspect the existing project structure, tooling, entrypoints, and nearby tests before proposing new modules or dependencies.
2. Classify the system's complexity. Keep CRUD and small Lambdas simple; introduce domain concepts only when meaningful rules, invariants, lifecycle, or policy justify them.
3. Identify business capabilities and make those the primary module boundaries. Add internal domain, application, infrastructure, or entrypoint boundaries only where they reduce real coupling.
4. Decide which external capabilities need ports. Use capability-oriented interfaces only when isolation, replacement, independent testing, or persistence complexity justifies them.
5. Keep dependencies pointed inward: domain is framework-free, application orchestrates use cases, infrastructure implements technical concerns, and entrypoints translate external input and output.
6. Separate structural/input validation at the boundary from business invariants in domain or application code. Do not use transport validation as a replacement for domain modeling.
7. Load the relevant reference document before making decisions in that area:
   - Architecture and module boundaries: `references/python-standard-architecture.md`
   - Entities, value objects, aggregates, domain services, invariants, domain events, and exceptions: `references/python-standard-domain.md`
   - Use cases, commands/queries, application DTOs, transaction boundaries, event publishing, and application services: `references/python-standard-application.md`
   - Frameworks, ports, persistence, configuration, integrations, async/sync, and Lambda: `references/python-standard-infrastructure.md`
   - Testing, quality, dependency injection, contract tests, and review checklist: `references/python-standard-quality.md`
   - Logging configuration and layer-specific observability: `references/python-standard-logging.md`
   - Exception classification, boundary mapping, safe envelopes, transport adapters, and exception logging: `references/python-standard-exceptions.md`
   - Existing-backend refactoring, compatibility, class abstractions, constructor injection, Punq, and verification: `references/python-standard-refactoring.md`
8. Implement the smallest coherent change. Every new abstraction must have a stated problem, owner, protected boundary, and testability or maintainability benefit.
9. Verify behavior at the relevant boundary: domain unit tests, application tests with focused fakes or stubs, infrastructure integration tests where behavior depends on a real service, and API/Lambda tests for mapping, errors, retries, and idempotency.
10. Finish with the architecture review checklist in the quality reference and report any unresolved tradeoffs or test gaps.

## Non-negotiable Boundaries

- Keep framework, ORM, AWS SDK, transport DTO, and HTTP exception types out of domain code.
- Keep environment and secret discovery out of business code; load validated configuration at the infrastructure/composition boundary and inject it explicitly.
- Keep entrypoints thin: receive, parse and validate, map, invoke, map the result, and handle the external response.
- Use `ExceptionHandler` from `exceptions.exception_handler` at the final boundary. Deviations require an existing project convention or framework constraint and explicit justification; keep mappings and responses out of domain/application code.
- Keep transactions at the application/use-case boundary; infrastructure supplies the mechanism.
- Treat message delivery as at-least-once unless exactly-once behavior is explicitly guaranteed. Design consumers for idempotency.
- Consider timeout, retry safety, error mapping, logging, observability, and idempotency for every external integration.
- Never hardcode or log secrets, tokens, passwords, or unnecessary personal information.

## Abstraction Gate

Before adding an entity, value object, domain service, event, repository, gateway, port, mapper, factory, specification, application service, or DI container, answer:

- What concrete problem does it solve?
- Why is simpler code insufficient?
- Which module owns it?
- Which boundary does it protect?
- How does it improve testability or maintainability?
- What complexity does it add?

If the answers are unclear, do not add the abstraction.

Use `ABC` and `abstractmethod` for nominal class contracts. Use `Protocol` for structural ports when duck typing is sufficient. Neither is required universally; follow the relevant reference.

## Boundary Terminology

- **Entrypoint**: outer boundary receiving external input and returning or acknowledging output.
- **Adapter**: translator between a transport/runtime and application or handler results.
- **Controller**: HTTP-oriented adapter when the framework uses that term; do not create a separate adapter without a concrete responsibility.
- **Handler**: runtime entrypoint or exception-mapping component; qualify the term when both meanings exist.

## Completion Criteria

- Architecture is proportional to current complexity; empty layers and speculative dependencies are absent.
- Business rules live with the domain concept or policy that owns them.
- Boundary validation and business invariants are distinct.
- Dependencies are explicit and no service locator is used.
- Configuration, logging, and infrastructure concerns are centralized appropriately.
- Important behavior has tests at the correct architectural boundary.
- External failures, retry behavior, duplicate delivery, and sensitive data handling were considered.
