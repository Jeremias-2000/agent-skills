# Python Backend Engineering Standard — Architecture

## Core Principle

> Use the simplest architecture that preserves business boundaries, testability, maintainability and dependency direction.

Do not introduce abstractions, layers, patterns, directories or dependencies without a concrete reason.

Every abstraction introduced MUST have an explicit justification:

```text
Abstraction: PaymentGateway
Reason: Isolate the application from an external payment provider.
```

If an abstraction cannot be justified — **do not create it**.

---

## 1. Architecture Principles

1. Business rules must not depend on infrastructure.
2. Domain code must not depend on frameworks or external services.
3. Application code orchestrates use cases.
4. Infrastructure implements technical concerns.
5. Entry points must remain thin.
6. Dependencies must point inward.
7. Prefer composition over inheritance.
8. Prefer explicit code over unnecessary abstractions.
9. Prefer behavior-rich domain models when real domain behavior exists.
10. Do not introduce DDD patterns merely to follow a template.
11. Prefer **module boundaries based on business capabilities** over arbitrary technical layer boundaries.
12. Keep configuration and infrastructure concerns outside business logic.
13. Separate **input/structural validation** from **business invariants**.
14. CRUD does not automatically justify DDD.
15. Frameworks must not leak into business logic.

The architecture must evolve with the complexity of the system.

---

## 2. Architecture Decision Process

Before creating directories or abstractions, analyze the project.

### Step 1 — Determine complexity

```text
Does the system contain meaningful business rules?

NO  → Keep architecture minimal.
YES → Consider introducing domain concepts.
```

Do not create a Domain layer merely because the project is a backend.

A CRUD application with simple persistence and validation may not require:
- Entities with rich behavior
- Value Objects
- Domain Services
- Domain Events
- Specifications
- Repositories
- Ports
- Aggregates

**CRUD does not automatically justify DDD.**

DDD should be introduced when the system contains **meaningful business rules, invariants, policies, lifecycle or domain complexity**.

### Step 2 — External systems

```text
Does the application interact with external systems?

NO  → Avoid unnecessary ports/adapters.
YES → Is the integration likely to change, require isolation
      or require independent testing?

      YES → Introduce a port/interface.
      NO  → Keep the implementation simple.
```

Do not create interfaces merely because "Hexagonal Architecture requires interfaces".

### Step 3 — Persistence

```text
Does the application persist state?

NO  → Do not create repositories.
YES → Does persistence complexity or database coupling
      justify an abstraction?

      YES → Introduce a repository/port.
      NO  → Keep persistence implementation simple.
```

Do not create one repository per database table automatically.

### Step 4 — Orchestration

```text
Are multiple use cases sharing complex orchestration?

YES → Consider an Application Service.
NO  → Keep orchestration inside individual Use Cases.
```

### Step 5 — DDD patterns

```text
Is a DDD pattern solving an actual problem?

NO → Do not introduce it.
```

---

## 3. Module Boundaries Over Layer Boundaries

Prefer **business-oriented modules** over a global technical layer structure when the system grows.

Avoid organizing a complex application like:

```text
domain/
application/
infrastructure/
controllers/
repositories/
services/
```

where all business concepts are mixed together.

Prefer:

```text
app/
├── orders/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── entrypoints/
│
├── payments/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── entrypoints/
│
└── customers/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── entrypoints/
```

Scaling rule:

```text
Small system    → simple modules
Growing system  → business-oriented modules
Complex domain  → business modules with internal
                  domain/application/infrastructure boundaries
```

**Do not introduce module boundaries merely because a DDD diagram looks cleaner.**
A module must represent a meaningful responsibility or business capability.

---

## 4. Dependency Direction

```text
                ┌───────────────┐
                │    Domain     │   ← depends on nothing external
                └───────▲───────┘
                        │
                ┌───────┴───────┐
                │  Application  │   ← depends on Domain
                └───────▲───────┘
                        │
             ┌──────────┴──────────┐
             │   Infrastructure    │   ← depends on Application + Domain
             └──────────▲──────────┘
                        │
                 ┌──────┴──────┐
                 │ Entrypoints │   ← depend on Application + composition root
                 └─────────────┘
```

The architecture **must not** force every project to contain all these layers.

The dependency rule applies **when those layers exist**.

---

## 5. Entrypoints

Entrypoints are the outermost layer. They receive external input and delegate to the application.

Controllers, Lambda handlers, CLI commands and queue consumers are all entrypoints.

**Entrypoints must be thin:**

```text
receive input
→ validate / parse
→ map to application command or query
→ call use case
→ map result
→ return response / ack
```

No business logic belongs in an entrypoint. Use cases must remain callable without any framework.

HTTP controllers belong here — not in infrastructure. Controllers are an entrypoint concern.

**Bad:**
```python
def execute(request: Request) -> JSONResponse:  # framework type crossing boundary
    ...
```

**Good:**
```python
def execute(command: CreateOrderCommand) -> OrderResult:
    ...
```

---

## 6. Minimal Architecture First

Do not create the complete architecture template by default.

A simple Lambda may be:

```text
app/
├── handler.py
├── service.py
└── tests/
```

A small API may be:

```text
app/
├── orders/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   └── models.py
└── tests/
```

Only introduce `domain/`, `application/`, `infrastructure/` when the complexity justifies the separation.

**Architecture is allowed to grow. It is NOT required to start fully grown.**

Empty architectural directories are **forbidden**.

---

## 7. Recommended Maximum Structure (Complex Systems Only)

The structure below is the **maximum for a complex system, not the starting point**.

```text
app/
├── orders/
│   ├── domain/
│   │   ├── entities/        ← entities and aggregates
│   │   ├── value_objects/
│   │   ├── services/        ← domain services
│   │   ├── events/          ← domain events
│   │   └── exceptions/
│   │
│   ├── application/
│   │   ├── use_cases/       ← one file per use case, commands and results colocated
│   │   └── ports/           ← repository and capability interfaces owned by application
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── aws/
│   │   ├── http/
│   │   ├── messaging/
│   │   └── observability/
│   │
│   └── entrypoints/
│       ├── api/
│       └── lambdas/
│
└── payments/
    └── ...
```

Notes on the application layout:
- Commands, queries, and result dataclasses live alongside the use case that owns them — not in a separate `dto/` directory.
- A shared `ports/` directory holds repository protocols and capability interfaces. If a port is specific to one use case it may live next to it instead.
- Do not create `dto/` as a dumping ground for all data transfer objects. Transport models (Pydantic `BaseModel`) belong in the entrypoint, not in application.

Do not create every directory automatically. Only create directories that are currently needed.
