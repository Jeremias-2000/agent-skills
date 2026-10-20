# DDD / Clean Architecture Review Checklist

The `check_structure.py` script checks folder structure and imports. This checklist covers issues that can only be discovered by reading the code. Use it on files flagged by the script and on recently changed files.

## Domain

- [ ] **Entities have behavior.** A class containing only attributes and getters/setters, with rules scattered across use cases, is an anemic entity. Move the rules into the entity.
- [ ] **Entities protect invariants.** Invalid state should be impossible to create or reach (validate in the constructor or business methods).
- [ ] **Identity is explicit.** Entities are compared by identity (ID), not by all their attributes.
- [ ] **DTOs do not contain business rules.** If a DTO contains a business-related `if`, that code belongs in an entity.
- [ ] **No transport types in the domain.** Do not put framework request/response objects, ORM models, or serializers in `entities/`.
- [ ] **Use ubiquitous language.** Class and method names use business vocabulary (e.g., `ConcessionRequest`, `approve`), not technical terms (`Manager`, `Helper`, `Data`).

## Interfaces (contracts)

- [ ] Every interface in `domain/interfaces/<x>/` has at least one implementation in the corresponding location (`usecases` → `application/usecases`, `gateways` → `application/gateways`, `adapters` → `infra/adapters`).
- [ ] Every implementation in `application/usecases`, `application/gateways`, and `infra/adapters` declares which interface it implements.
- [ ] Interfaces contain signatures only, no logic.

## Application layer

- [ ] A use case represents a user/system intent, with a clear public method (e.g., `execute`).
- [ ] A use case receives dependencies through its constructor, typed to domain **interfaces**, never concrete classes.
- [ ] A use case knows nothing about HTTP (status codes, headers, requests) or database details.
- [ ] Gateways translate external formats into domain DTOs/entities so external system formats do not leak inward.

## Infrastructure layer

- [ ] Controllers are thin: they validate input, call a use case, and convert the result into a response. Business rules in a controller belong in an entity or use case.
- [ ] No controller instantiates adapters or use cases directly; it receives everything through `di/`.
- [ ] `di/` is the only place that imports concrete implementations to wire them together.
- [ ] Infrastructure exceptions are converted into domain/application errors before propagating, or mapped to HTTP responses in one place (`exceptions/`).
- [ ] Read environment configuration in `setup/` or `application/configuration/`, never through scattered `os.environ` access in the domain.

## Tests

- [ ] A domain unit test does not mock infrastructure (if it does, the domain is coupled).
- [ ] A use-case unit test uses fakes/mocks of domain **interfaces**.
- [ ] Every new layer has tests in `tests/unitary/<layer>/`.
- [ ] Integration tests live in `tests/integration/` and start the assembled application.

## Quick warning signs

| Symptom | Likely cause |
|---|---|
| `import requests`/`sqlalchemy`/`fastapi` in `domain/` | A technical detail has leaked into the core |
| Use case with many `if status_code ==` checks | The HTTP layer has leaked into the application |
| Controller with more than ~30 lines of logic | Business rules are in the wrong place |
| `utils/`, `helpers/`, or `common/` directory at a layer's root | A domain concept or layer boundary is missing |
| Domain test that requires a database or network | The domain is coupled to infrastructure |