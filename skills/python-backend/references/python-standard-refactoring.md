# Python Refactoring Standard

Use this reference when refactoring an existing Python backend. Refactoring changes structure without changing intended behavior. Apply these rules with proportional architecture: do not add layers, classes, interfaces, or containers without a concrete boundary, substitution, testing, or maintainability benefit.

## Project organization

- For new projects, keep application code under `app/` and tests under `app/tests/`.
- If an existing project has an equivalent, coherent layout, do not move files only to match these paths. Record the equivalence in the implementation summary and preserve established tooling.
- Keep responsibilities cohesive. Use classes for stateful or boundary-oriented behavior; keep trivial stateless logic as functions or modules.
- Code blocks without a complete module context are illustrative; copyable examples must make imports, symbols, return behavior, and compatibility assumptions clear.

## Boundaries and abstractions

Create abstractions for repositories, services, controllers, handlers, gateways, or equivalent components only when they protect a meaningful boundary or enable replacement, isolation, or independent testing.

Before adding an abstraction, identify:

1. The concrete problem it solves.
2. The module that owns it.
3. The boundary it protects.
4. The testability or maintainability benefit.
5. The complexity it adds.

If these answers are unclear, keep the simpler design.

Nominal class abstractions use `ABC` and `abstractmethod` from `abc`. Structural ports may use `Protocol` when duck typing is sufficient and no nominal inheritance or shared abstract behavior is required:

```python
from abc import ABC, abstractmethod


class IService(ABC):

    @abstractmethod
    def should_do_something(self) -> str:
        raise NotImplementedError(
            "There is no implementation for this method"
        )


class Service(IService):

    def should_do_something(self) -> str:
        return "implemented"
```

Concrete implementations must fulfill every abstract method with valid syntax and compatible types.

Do not treat `ABC` or `Protocol` as universal requirements. Choose one only after the abstraction gate identifies a real boundary problem.

## Dependency injection

- Use constructor dependency injection for services, repositories, controllers, handlers, and other components with dependencies.
- Keep dependencies explicit and typed where project conventions support typing.
- Never use Service Locator.
- Do not resolve dependencies from a container inside domain, application, controller, or handler code.
- Assemble object graphs in the composition root.

## Punq

Use Punq only when it already exists in the project or its adoption is explicitly required. Do not introduce a container solely to satisfy this standard.

When Punq is used:

- Register required abstractions with their concrete implementations in the composition root.
- Update registrations whenever a boundary, constructor, lifetime, or implementation changes.
- Keep Punq configuration outside business logic.
- Keep application and domain code unaware of the container.

Constructor injection remains mandatory regardless of whether Punq is used.

## Unit-testable design

Design boundaries so unit tests can replace persistence, network, queues, clocks, and other external concerns with mocks, stubs, or fakes. Prefer the simplest test double that makes behavior clear. Use integration or contract tests when behavior depends on a real database, framework, protocol, or external service.

Update tests with each boundary move. Preserve characterization tests for behavior that is not yet fully specified.

## Coordinated updates

When refactoring affects a boundary, update all dependent surfaces together:

- imports and module paths;
- application composition and entrypoints;
- Punq registrations, when Punq is used;
- Alembic configuration and migrations, when persistence behavior or metadata is affected;
- unit, integration, contract, API, and handler tests.

Do not change migration history or schema semantics merely to improve structure.

## Compatibility requirements

Preserve existing behavior unless the user explicitly requests a functional change, including:

- API inputs, outputs, status codes, errors, and serialization;
- database schema behavior, queries, data semantics, and transaction boundaries;
- event payloads and delivery behavior;
- retries, timeouts, idempotency, and external-failure handling;
- logging and observability contracts;
- synchronous or asynchronous execution behavior.

Use compatibility adapters or staged migration when direct replacement could break callers. Separate required compatibility fixes from optional improvements.

## Verification

Inspect structure, tooling, entrypoints, and tests before changing code. Verify incrementally with existing project commands:

- focused unit tests for moved domain or application logic;
- fakes, stubs, or mocks for isolated external dependencies;
- integration or contract tests for persistence and external protocols;
- API or handler tests for mapping, errors, retries, and idempotency;
- existing type-check, lint, migration, and architecture checks.

Finish by checking dependency direction, absence of Service Locator usage, composition-root wiring, API and database compatibility, and unresolved test gaps. Do not add new validation tools unless the project already requires them.
