# Python Backend Engineering Standard — Infrastructure

## 1. Framework Leakage

Framework leakage occurs when technology-specific concerns cross into business code.

Frameworks include: FastAPI, Flask, Django, Pydantic transport models, SQLAlchemy, boto3, AWS Lambda runtime, Redis clients, HTTP clients, Punq, ORM-specific types, framework exceptions.

**Forbidden in Domain:**
```python
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import Column
import boto3
```

**Forbidden in Application:**
```python
class CreateOrder:
    def execute(self, request: FastAPIRequest):  # Bad — framework type in use case
        ...
```

Framework leakage rule:
> A framework may depend on the application. The application must not become dependent on the framework merely because the framework is convenient.

---

### Leakage into Application Layer

**Bad — S3 SDK leaking into a use case:**
```python
import boto3

class UploadDocumentUseCase:
    def execute(self, file: bytes, filename: str) -> str:
        s3 = boto3.client("s3")                          # SDK in application
        bucket = os.getenv("DOCUMENTS_BUCKET")           # config discovery in application
        s3.put_object(Bucket=bucket, Key=filename, Body=file)
        return f"s3://{bucket}/{filename}"
```

**Good — use case depends on a port, not a technology:**
```python
class UploadDocumentUseCase:
    def __init__(self, storage: DocumentStorage):        # depends on capability
        self.storage = storage

    def execute(self, file: bytes, filename: str) -> str:
        return self.storage.upload(file, filename)       # clean, testable
```

### Leakage into Domain Layer

**Bad — ORM model becoming the domain model:**
```python
from sqlalchemy import Column, String
from sqlalchemy.orm import DeclarativeBase

class Order(DeclarativeBase):                            # domain tied to ORM
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    status = Column(String)

    def cancel(self):
        if self.status == "SHIPPED":
            raise HTTPException(status_code=400)        # HTTP concern in domain
        self.status = "CANCELLED"
```

**Good — domain model is plain Python:**
```python
@dataclass
class Order:
    id: str
    status: OrderStatus

    def cancel(self) -> None:
        if self.status == OrderStatus.SHIPPED:
            raise OrderCannotBeCancelled()              # domain exception only
        self.status = OrderStatus.CANCELLED
```

The ORM mapping lives in `infrastructure/database/` and converts between the ORM row and the domain object.

---

## 2. Ports and Adapters

Create an abstraction when the application must remain independent from an external capability.

Use `Protocol` when structural typing is sufficient. Use `ABC` with `abstractmethod` when the boundary requires explicit nominal inheritance or shared abstract behavior. Neither form is required without a concrete boundary problem.

```python
class PaymentGateway(Protocol):
    async def charge(...): ...

class DocumentStorage(Protocol):
    async def upload(...): ...

class EventPublisher(Protocol):
    async def publish(...): ...
```

The interface should represent the **capability**, not the technology.

Prefer:
```text
DocumentStorage       ← application port
```

over:
```text
S3Gateway             ← leaks technology into application
```

Infrastructure may implement:
```text
S3DocumentStorage     ← infrastructure adapter
```

---

## 3. Repository

A Repository is optional. Introduce one when:
- persistence details would otherwise leak into business/application code
- persistence behavior is meaningful to the domain
- multiple persistence strategies are possible
- isolation improves testing or maintainability
- the abstraction represents an actual domain/application capability

```python
from typing import List, Optional


class OrderRepository(Protocol):
    async def get_by_id(self, order_id: str) -> Optional[Order]: ...
    async def save(self, order: Order) -> None: ...
```

### Where should the interface live?

```text
If persistence is part of a domain concept
→ repository abstraction may live in Domain.

If persistence is merely an application capability
→ repository/port may live in Application.
```

The important rule is **dependency direction**, not the directory name.

Infrastructure implementations belong in `infrastructure/`:
```text
SQLAlchemyOrderRepository
DynamoDBOrderRepository
```

**Do not create repositories for every database table automatically.**
Repositories represent business/application persistence needs, not database tables.

---

## 4. DTOs

Use DTOs at architectural boundaries:
- HTTP requests / responses
- SQS events
- Lambda events
- external API responses
- application commands
- integration messages

Transport models must not leak into the Domain.

```python
class CreateOrderRequest(BaseModel):
    customer_id: UUID
    items: List[OrderItemRequest]
```

Convert external DTOs into application/domain concepts at the boundary.

---

## 5. Pydantic

Use Pydantic v2+.

Use it primarily for:
- API request validation
- API response models
- configuration
- external data parsing
- integration DTOs

The Domain should prefer `dataclass` or plain Python classes.

Pydantic may be used for Value Objects when it provides meaningful validation, but avoid making Pydantic models the core domain model by default.

Use modern Pydantic v2 APIs — `field_validator`, `model_validator`, `ConfigDict`. Do **not** use deprecated v1 APIs.

---

## 6. Configuration Management

Configuration is an **infrastructure concern**.

**Bad:**
```python
class PaymentService:
    def __init__(self):
        self.url = os.getenv("PAYMENT_URL")  # discovers its own config
```

**Correct flow:**
```text
Environment / Secrets
        ↓
Configuration (validated, immutable)
        ↓
Composition Root
        ↓
Explicit injection
        ↓
Application / Domain
```

Example:
```python
@dataclass(frozen=True)
class PaymentConfig:
    timeout: float
    endpoint: str
```

> **Business code receives configuration; it does not discover configuration.**

Secrets must not be hardcoded or logged.

---

## 7. Transactions

Transaction boundaries belong to the **application/use-case layer**.

The Domain must not begin, commit or rollback transactions.

The Use Case defines the business operation boundary. Infrastructure implements the transaction mechanism.

---

## 8. Event-Driven Systems

Assume messaging systems may deliver messages more than once.

Consumers **must** consider idempotency:

```text
at-least-once delivery
        ↓
possible duplicate event
        ↓
idempotent processing
```

When applicable, use:
- idempotency keys
- deduplication records
- conditional writes
- transactional state changes
- appropriate visibility timeout
- dead-letter queues

Never assume exactly-once processing unless the infrastructure and design explicitly guarantee it.

---

## 9. External Integrations

Every external integration must explicitly consider:
```text
timeout / retry / error mapping / logging / observability / idempotency
```

Retries must only be introduced when the operation is safe to retry.

**Do not blindly retry `POST /payment`** without considering duplicate side effects.

---

## 10. AWS Lambda Specifics

Lambda handlers must be thin:

```text
AWS Event
   ↓
Event Mapper
   ↓
Application Use Case
   ↓
Domain
   ↓
Ports / Infrastructure
```

Handler responsibilities: receive event → extract data → map → invoke use case → handle entrypoint behavior.

AWS SDK code must not leak into Domain or Application.

**Lambda Execution Context — reuse expensive resources across invocations when safe:**

Suitable candidates: stateless HTTP clients, connection pools, SDK clients, read-only configuration.

- Avoid reusing resources that carry mutable per-invocation state.
- Do not eagerly initialize resources the Lambda does not need.
- Prefer targeted or lazy initialization.

---

## 11. Async vs Sync

Python async (`async`/`await`) has real costs and real benefits. Do not default to async simply because a framework supports it.

### Decision guide

```text
Does the selected runtime and driver support async, and is there
meaningful concurrency within one execution?

YES → consider async def
NO  → sync def is sufficient; async adds overhead without benefit
```

### When async is appropriate

- FastAPI route handlers that call async repositories or async HTTP clients.
- Repository adapters backed by async drivers (e.g., `asyncpg`, `aioboto3`, `motor`).
- Lambda handlers that fan out to multiple I/O operations concurrently (`asyncio.gather`).
- SQS/EventBridge consumers that perform concurrent I/O per invocation.

### When sync is sufficient

- CPU-bound logic (domain rules, calculations, transformations) — async provides no benefit and adds noise.
- Simple Lambda handlers with a single sequential I/O call — the complexity of an event loop is not justified.
- Script-style workers with no concurrency requirement.

### Lambda-specific tradeoffs

| Factor | Consideration |
|---|---|
| Cold start | An async Lambda handler must initialize an event loop; adds a small but measurable cold-start cost. |
| Single-invocation concurrency | Lambda runs one event at a time per instance; true async concurrency only helps within a single invocation (e.g., parallel `asyncio.gather` calls). |
| Sync boto3 vs async | `boto3` is synchronous. `aioboto3` / `aiobotocore` add async support but also add weight. Use sync boto3 unless you genuinely need async concurrency within one invocation. |
| Thread executor | For blocking I/O in an async Lambda, use `loop.run_in_executor(None, ...)` to avoid blocking the event loop. |

### Consistency rule

**Do not mix async and sync at the same architectural boundary.** If a use case is `async def`, all ports it calls must be async-compatible. If a use case is `sync`, its ports should be sync. A mixed boundary forces awkward `asyncio.run()` calls or thread executor workarounds.

```python
# Bad — sync use case calling an async repository
class CreateOrderUseCase:
    def execute(self, command: CreateOrderCommand) -> OrderResult:
        order = asyncio.run(self.repository.get_by_id(command.order_id))  # wrong
        ...

# Good — consistent async boundary
class CreateOrderUseCase:
    async def execute(self, command: CreateOrderCommand) -> OrderResult:
        order = await self.repository.get_by_id(command.order_id)
        ...
```

### Async test tooling

When the project uses Pytest, use `pytest-asyncio` for async tests and configure it once in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This avoids decorating every async test function individually.

---

## 12. Preferred Technologies

These are preferences, not unconditional requirements. Do not add a dependency simply because it appears here.

| Tool | Use when |
|---|---|
| **Pydantic v2** | Validating API requests/responses, parsing external data, configuration models. Not as a substitute for domain modeling. |
| **FastAPI** | Building HTTP APIs. Keep framework types out of application and domain layers. |
| **SQLAlchemy** | Relational persistence with non-trivial queries or multiple tables. For simple single-table access, a lighter approach may be sufficient. |
| **Alembic** | Database schema migrations when using SQLAlchemy. Always pair with SQLAlchemy. |
| **boto3** | AWS service integrations. Must be wrapped behind a port — never called directly from application or domain code. |
| **Punq** | DI container when the object graph becomes difficult to wire manually, or when multiple entrypoints duplicate composition. Do not introduce it for small applications. |
| **httpx** | Outbound HTTP calls to external services. Wrap behind a port when the integration must be testable or replaceable. |
| **Pytest** | Recommended for new projects. Existing projects use their configured test runner; use `pytest-asyncio` only when Pytest is selected. |
| **LocalStack** | Local integration testing against AWS services (SQS, S3, DynamoDB, Lambda). Prefer over mocking the SDK when testing infrastructure adapters. |
| **Testcontainers** | Integration testing against real databases or other containerized infrastructure. Prefer over in-memory fakes when persistence behavior matters. |
