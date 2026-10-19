# Python Backend Engineering Standard — Application Layer

This reference covers the application layer: use cases, application services, commands and queries, application DTOs, transaction boundaries, and event publishing coordination.

For the domain building blocks (entities, value objects, domain services, invariants, domain events), see `references/python-standard-domain.md`.

---

## 1. What the Application Layer Does

Application code coordinates use cases. It sits between the domain and infrastructure, orchestrating the steps needed to fulfill a request without containing business rules itself.

A use case:
- loads entities or aggregates via ports/repositories
- invokes domain behavior
- calls infrastructure ports (storage, messaging, external APIs)
- manages the transaction boundary
- publishes integration events when necessary
- returns application-layer DTOs to the caller

A use case **must not** become the place where business rules accumulate.

**Bad — business rule living in the application layer:**
```python
class ApplyDiscountUseCase:
    def execute(self, command: ApplyDiscountCommand) -> None:
        if order.total > 1000:          # business rule — belongs in domain
            order.discount = 0.1
```

**Good — use case delegates to the domain:**
```python
class ApplyDiscountUseCase:
    def execute(self, command: ApplyDiscountCommand) -> None:
        order = self.repository.get_by_id(command.order_id)
        order.apply_discount(self.pricing_policy)   # domain owns the rule
        self.repository.save(order)
```

---

## 2. Use Cases

Prefer one class per use case with a single `execute` method (or `async def execute`).

```python
# application/use_cases/cancel_order.py
from dataclasses import dataclass
from typing import List, Optional
from domain.orders.entities import Order
from domain.orders.exceptions import OrderCannotBeCancelled, OrderNotFound
from application.orders.ports import OrderRepository

@dataclass
class CancelOrderCommand:
    order_id: str
    reason: Optional[str] = None

@dataclass
class CancelOrderResult:
    order_id: str
    status: str

class CancelOrderUseCase:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def execute(self, command: CancelOrderCommand) -> CancelOrderResult:
        order = self.repository.get_by_id(command.order_id)
        if order is None:
            raise OrderNotFound(command.order_id)

        order.cancel()                          # domain enforces the invariant
        self.repository.save(order)

        return CancelOrderResult(order_id=order.id, status=order.status.value)
```

This is a focused example. `Order`, `OrderStatus`, `OrderNotFound`, and `OrderRepository` are project-owned symbols shown here to make the boundary explicit.

**Keep use cases independently callable** — no framework type should appear in the signature. A use case must be testable with plain Python, no FastAPI, no Lambda event object, no HTTP request.

---

## 3. Commands and Queries

Use the Command / Query distinction when it reduces ambiguity.

| Type | Purpose | Returns |
|---|---|---|
| Command | Mutates state | Result or void; raises on failure |
| Query | Reads state | Data; no side effects |

```python
# Command — mutates
@dataclass
class PlaceOrderCommand:
    customer_id: str
    items: List[OrderItemCommand]

# Query — reads
@dataclass
class GetOrderQuery:
    order_id: str
```

You do not need to introduce a full CQRS pattern unless the read and write models genuinely diverge. For most systems, a plain use case with a typed command dataclass is sufficient.

---

## 4. Application DTOs

Use DTOs to carry data across architectural boundaries. Application-layer DTOs are not transport models — they are the application's internal data contract.

```python
@dataclass
class OrderResult:
    order_id: str
    status: str
    total_amount: float
    placed_at: datetime
```

Rules:
- Application DTOs must not contain domain entities. Return plain data.
- Transport models (Pydantic `BaseModel`) are converted from application DTOs at the entrypoint, not inside the use case.
- Do not pass Pydantic request models directly into use cases.

```python
# Entrypoint maps transport → command
command = PlaceOrderCommand(
    customer_id=str(request.customer_id),
    items=[OrderItemCommand(sku=i.sku, qty=i.quantity) for i in request.items],
)
result = use_case.execute(command)

# Entrypoint maps result → response
return OrderResponse(order_id=result.order_id, status=result.status)
```

---

## 5. Application Services

Do **not** create Application Services by default.

Introduce one only when:
- multiple use cases share substantial orchestration logic
- a multi-step workflow has reusable intermediate steps
- the orchestration itself is a meaningful, named capability

Otherwise `application/use_cases/` is sufficient. Prefer a small number of focused use cases over layers of services stacked on top of each other.

```text
Prefer:
  PlaceOrderUseCase
  CancelOrderUseCase
  RefundOrderUseCase

Over:
  OrderApplicationService.place()
  OrderApplicationService.cancel()
  OrderApplicationService.refund()
```

The second form groups use cases into a class for organizational convenience but gains nothing architecturally and makes individual use cases harder to test and inject.

---

## 6. Transaction Boundaries

Transaction boundaries belong to the **use case**, not the domain.

The domain must not begin, commit, or roll back transactions. The use case defines the business operation boundary; infrastructure implements the mechanism.

```python
class TransferFundsUseCase:
    def __init__(
        self,
        account_repo: AccountRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.account_repo = account_repo
        self.unit_of_work = unit_of_work

    def execute(self, command: TransferFundsCommand) -> None:
        with self.unit_of_work:
            source = self.account_repo.get_by_id(command.source_id)
            target = self.account_repo.get_by_id(command.target_id)
            source.debit(command.amount)
            target.credit(command.amount)
            self.unit_of_work.commit()
```

If you are not using a Unit of Work pattern, the use case still controls when `session.commit()` or equivalent is called — passed in via the repository or a context manager injected at composition time.

---

## 7. Publishing Integration Events

When a domain event must cross a bounded context boundary or reach an external system, the **application layer is responsible for the translation and publication** — not the domain.

The domain raises a domain event. The use case picks it up and publishes an integration event through an `EventPublisher` port.

```python
# application/ports/event_publisher.py
from typing import Protocol

class EventPublisher(Protocol):
    def publish(self, event_type: str, payload: dict) -> None: ...
```

The protocol snippet is illustrative; the concrete event and payload types remain project-defined.

```python
# application/use_cases/place_order.py
class PlaceOrderUseCase:
    def __init__(
        self,
        repository: OrderRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    def execute(self, command: PlaceOrderCommand) -> PlaceOrderResult:
        order = Order.create(command.customer_id, command.items)
        self.repository.save(order)

        # Translate domain event → integration event and publish
        self.event_publisher.publish(
            event_type="order.placed",
            payload={
                "order_id": order.id,
                "customer_id": order.customer_id,
                "placed_at": order.placed_at.isoformat(),
            },
        )

        return PlaceOrderResult(order_id=order.id)
```

The infrastructure adapter (`SQSEventPublisher`, `SNSEventPublisher`, etc.) handles serialization and transport. The use case depends only on the port.

---

## 8. Error Handling in the Application Layer

The application layer may catch domain exceptions for two reasons:
1. To wrap them in an application-level exception with richer context.
2. To add contextual logging before re-raising when it provides diagnostic value.

It must **not** map exceptions to HTTP status codes or transport-level error shapes — that is the entrypoint's responsibility.
Use `ExceptionHandler` from `exceptions.exception_handler` at the final boundary. Expected failures MUST NOT be logged again there when the application already added equivalent context.

```python
# Application layer — acceptable
try:
    order.cancel()
except OrderCannotBeCancelled:
    self.logger.warning("Cancellation rejected", extra={"order_id": command.order_id})
    raise  # let the entrypoint / global handler map it

# Application layer — bad
try:
    order.cancel()
except OrderCannotBeCancelled:
    raise HTTPException(status_code=422, detail="Cannot cancel shipped order")  # HTTP in application
```

---

## 9. Ports (Application-Owned Interfaces)

Ports that represent application capabilities (not domain capabilities) live in `application/ports/` or alongside the use cases that use them.

```text
application/
└── orders/
    ├── use_cases/
    │   ├── place_order.py
    │   └── cancel_order.py
    └── ports/
        ├── order_repository.py     # persistence port
        └── event_publisher.py      # messaging port
```

Infrastructure adapters implement these ports and live in `infrastructure/`. The dependency always points inward: infrastructure depends on application; application does not depend on infrastructure.

---

## 10. Application Layer Checklist

- [ ] Use cases are independently callable without framework types.
- [ ] Business rules are in the domain, not in the use case.
- [ ] Commands and results are plain Python dataclasses.
- [ ] Transport models (Pydantic) are not passed into use cases.
- [ ] Transaction boundaries are at the use case level.
- [ ] Integration events are published through a port, not directly via SDK.
- [ ] Application services are introduced only when orchestration is genuinely shared.
- [ ] Domain exceptions are not mapped to HTTP responses inside the application layer.
- [ ] Ports are defined in `application/` and implemented in `infrastructure/`.
