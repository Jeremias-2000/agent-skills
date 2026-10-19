# Python Backend Engineering Standard — Quality, Testing & Checklist

## 1. Dependency Injection

Use manual dependency wiring by default.

Introduce a DI container when:
- the object graph becomes difficult to maintain
- composition is duplicated across multiple entrypoints
- dependencies have multiple implementations
- lifecycle management becomes significant
- manual composition becomes error-prone

**Punq** is the preferred container when a container is justified.

Use a Composition Root at `infrastructure/di/`.

Application and Domain code **must not** call `container.resolve(...)`.

**Bad:**
```python
class CreateOrder:
    def execute(self):
        repository = container.resolve(OrderRepository)  # service locator
```

**Good:**
```python
class CreateOrder:
    def __init__(self, repository: OrderRepository):
        self.repository = repository  # explicit injection
```

---

## 2. Testing Strategy

Testing should follow architectural boundaries.

### Domain

Fast unit tests with no infrastructure:

```text
Order
 ├── add_item
 ├── calculate_total
 ├── place
 └── cancel
```

These must be testable without: AWS, database, FastAPI, HTTP, Redis.

### Application

Test use cases using: fakes, stubs, mocks.

Use mocks selectively. Prefer fakes for repositories when they improve readability. Do not mock the Domain unnecessarily. Avoid mocking everything.

### Infrastructure

Use integration tests for:
- database repositories
- AWS integrations
- HTTP clients
- messaging
- persistence

Use Testcontainers or LocalStack when they provide meaningful confidence.

### API / Lambda

Test important scenarios through:
```text
HTTP request → controller → application → infrastructure
AWS event   → mapper     → use case
```

Also test important error, retry, and idempotency behaviors.

### Event Contract / Schema Tests

Lambda consumers and event-driven integrations have an implicit contract with their producers: the shape of the event. When that shape changes silently, the consumer breaks at runtime with a confusing `KeyError` or `ValidationError`. Pin that contract with explicit tests.

**When to write event contract tests:**
- Lambda functions triggered by SQS, SNS, EventBridge, S3, DynamoDB Streams, or Kinesis.
- Any consumer that parses a message envelope or extracts fields from an event.
- Integration points where the producer and consumer are owned by different teams or services.

**Approach 1 — Pydantic model as the contract**

Define a Pydantic model for the incoming event shape and test that real event fixtures parse correctly:

```python
# infrastructure/events/sqs_order_event.py
from pydantic import BaseModel, UUID4
from datetime import datetime

class OrderPlacedPayload(BaseModel):
    order_id: UUID4
    customer_id: UUID4
    placed_at: datetime
    total_amount: float

class SQSOrderPlacedEvent(BaseModel):
    order_id: UUID4
    customer_id: UUID4
    placed_at: datetime
    total_amount: float

    @classmethod
    def from_sqs_record(cls, record: dict) -> "SQSOrderPlacedEvent":
        import json
        body = json.loads(record["body"])
        return cls.model_validate(body)
```

The following versioned file is a real sample from the upstream service. Hand-authored payloads must be labeled as mocks.

```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "123e4567-e89b-12d3-a456-426614174000",
  "placed_at": "2026-08-26T10:00:00Z",
  "total_amount": 99.99
}
```

```python
# tests/contracts/test_sqs_order_event_contract.py
import json
from pathlib import Path

import pytest
from infrastructure.events.sqs_order_event import SQSOrderPlacedEvent

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "order_placed.json"

def test_valid_event_parses_correctly():
    payload = json.loads(FIXTURE_PATH.read_text())
    record = {"body": json.dumps(payload)}
    event = SQSOrderPlacedEvent.from_sqs_record(record)
    assert str(event.order_id) == "550e8400-e29b-41d4-a716-446655440000"
    assert event.total_amount == 99.99

def test_missing_required_field_raises_validation_error():
    record = {"body": json.dumps({"order_id": "550e8400-e29b-41d4-a716-446655440000"})}
    with pytest.raises(ValueError):  # structural parsing failure, not a domain-rule error
        SQSOrderPlacedEvent.from_sqs_record(record)
```

**Approach 2 — JSON Schema snapshot**

When you do not control the producer model, store the expected schema as a JSON file and assert the incoming event validates against it:

```python
# tests/contracts/test_eventbridge_schema.py
import json
from pathlib import Path
import jsonschema

SCHEMA = json.loads(Path("tests/contracts/schemas/order_placed.json").read_text())

def test_eventbridge_event_matches_schema(sample_eventbridge_event):
    jsonschema.validate(instance=sample_eventbridge_event["detail"], schema=SCHEMA)
```

**Checklist for event contract tests:**
- [ ] A Pydantic model or JSON schema exists for each consumed event shape.
- [ ] A canonical, versioned real sample is committed and linked to the contract model.
- [ ] Tests verify both valid parsing and rejection of structurally invalid events.
- [ ] When the upstream producer changes the schema, these tests fail fast before deployment.

---

## 3. Engineering Standards

Projects MUST preserve important behavior with appropriate tests, explicit configuration, and dependency management when dependencies exist. Type hints, linting, and formatting are RECOMMENDED for new projects and SHOULD follow existing project tooling. Scripts, prototypes, and disposable code MAY omit optional tooling when that scope is explicit.

Preferred tools for new projects:
```text
pytest
ruff
mypy / pyright
```

Use existing project tooling when present. Do not introduce a replacement or install a new tool solely because this Skill recommends it. Pytest, Ruff, and mypy/pyright are RECOMMENDED defaults for new projects.

---

## 4. Code Quality Rules

**Prefer:**
- small functions
- explicit dependencies
- clear names
- composition
- type hints
- immutable values where appropriate
- single responsibility
- early boundary validation
- clear error handling
- cohesive modules

**Avoid:**
- God classes / God services
- `utils/`, `helpers/`, `common/` as dumping grounds — code should live close to the concept that owns it
- service locators
- deep inheritance hierarchies
- premature abstractions
- unnecessary factories, interfaces, repositories, events, patterns
- framework leakage into domain or application
- hidden configuration access (`os.getenv` scattered through business code)

---

## 5. Architecture Smell Detection

When the architecture shows signs of over-engineering or misplaced responsibilities, simplify before adding more abstractions. See the full smell list and remediation guidance in section 7 (Architecture Review Checklist).

> **Simplify the architecture before adding more abstractions.**

---

## 6. Abstraction Justification

Before introducing any of the following:

```text
Entity / Value Object / Domain Service / Domain Event
Repository / Gateway / Port / Application Service
Specification / Mapper / Factory / DI Container
```

Answer:

1. What problem does this abstraction solve?
2. Why can't simpler code solve it?
3. Which module owns this abstraction?
4. Which architectural boundary does it protect?
5. What dependency direction does it enforce?
6. Does it improve testability or maintainability?
7. What complexity does it introduce?

If the answers are unclear: **do not introduce the abstraction.**

---

## 7. Architecture Review Checklist

### Architecture
- [ ] Architecture is proportional to system complexity.
- [ ] CRUD complexity has not been mistaken for domain complexity.
- [ ] Business modules have meaningful boundaries.
- [ ] Module boundaries are preferred over arbitrary technical layers.
- [ ] No unnecessary directory, abstraction, or dependency was added.

### Domain
- [ ] Business rules are in the correct layer.
- [ ] Domain behavior exists where domain behavior is actually needed.
- [ ] Domain does not depend on infrastructure, frameworks, or transport DTOs.
- [ ] Domain invariants are not delegated entirely to Pydantic.

### Validation
- [ ] Structural/input validation happens at the boundary.
- [ ] Business invariants are enforced by the appropriate domain/application component.
- [ ] Validation logic has not been confused with business logic.

### Framework
- [ ] No framework leakage exists.
- [ ] FastAPI/HTTP objects do not enter business logic.
- [ ] ORM models do not become domain models accidentally.
- [ ] AWS SDK types do not enter Domain/Application unnecessarily.

### Configuration
- [ ] Configuration is loaded at the infrastructure/composition boundary.
- [ ] Business code does not read environment variables directly.
- [ ] Configuration is explicitly injected.
- [ ] Secrets are not hardcoded or logged.

### Dependencies
- [ ] Dependencies are explicit.
- [ ] No service locator is used.
- [ ] DI container is used only when justified.

### Infrastructure
- [ ] External systems are isolated when necessary.
- [ ] Transaction boundaries are explicit.
- [ ] External calls have appropriate timeout behavior.
- [ ] Retry behavior is intentional and safe.
- [ ] Idempotency has been considered for message consumers.

### Testing
- [ ] Important business behavior has tests.
- [ ] Domain tests do not require infrastructure.
- [ ] Application tests use appropriate fakes/stubs/mocks.
- [ ] Infrastructure integrations have integration tests where valuable.
- [ ] Lambda/API boundaries have appropriate tests.
- [ ] Event contract / schema tests exist for each consumed event shape (SQS, SNS, EventBridge, etc.).
- [ ] Canonical event fixtures are committed alongside contract models.

### Observability
- [ ] Logging is appropriate for the runtime.
- [ ] Important failures are observable.
- [ ] Sensitive information is not logged.

---

## 8. Final Rule

The architecture must answer the problem, not the other way around.

Start with:
> "What problem does this system have?"

Then choose the smallest architecture that solves it.

```text
Simple → Modular → Layered → Hexagonal → DDD patterns
```

Move to the next level only when complexity justifies it. Prefer business capability → module boundary → internal architectural boundaries over jumping straight to global technical layers.

> **Good architecture is not the architecture with the most patterns.**
> **Good architecture is the architecture that makes the system easier to change without introducing unnecessary complexity.**
