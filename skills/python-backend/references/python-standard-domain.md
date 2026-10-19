# Python Backend Engineering Standard — Domain

This reference covers the building blocks that live inside the domain layer: entities, aggregates, value objects, domain services, invariants, specifications, events, and exceptions.

For application-layer orchestration (use cases, application services, commands, DTOs, event publishing), see `references/python-standard-application.md`.

---

## 1. Domain Entities

Use an Entity when the concept:
- has identity
- has lifecycle
- owns meaningful business behavior

```python
from typing import List


@dataclass
class Order:
    id: str
    status: OrderStatus
    items: List[OrderItem]

    def cancel(self) -> None:
        if self.status == OrderStatus.SHIPPED:
            raise OrderCannotBeCancelled()
        self.status = OrderStatus.CANCELLED
```

Prefer:
```python
order.cancel()
```

over:
```python
order_service.cancel_order(order)
```

when the operation is naturally the responsibility of the entity.

An entity that only contains getters and setters is **not** automatically a good domain model. If there is no meaningful behavior, plain data classes or simple persistence models may be sufficient.

---

## 2. Aggregates

An Aggregate is a cluster of domain objects (one root entity and zero or more child entities or value objects) that is treated as a single unit for data changes. The **Aggregate Root** is the only object external code is allowed to hold a reference to or persist.

**Do not introduce an Aggregate Root by default.** Add one only when:
- two or more entities must change together to preserve a business invariant, and
- that invariant cannot be enforced by a single entity alone.

The classic signal is a consistency rule that spans multiple objects:

```text
An Order and its OrderItems must be consistent:
- you cannot add an item to a shipped order
- the order total must always reflect its items
```

```python
@dataclass
class Order:               # ← Aggregate Root
    id: str
    status: OrderStatus
    items: List[OrderItem] # ← child entity, owned by Order

    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderCannotBeModified()
        self.items.append(item)

    @property
    def total(self) -> Money:
        return sum((i.subtotal for i in self.items), Money(Decimal("0"), "BRL"))
```

### Aggregate rules

| Rule | Rationale |
|---|---|
| Only the root has a repository. | Persistence is always through the root — never load a child directly. |
| External objects hold only the root's identity. | References to child entities by other aggregates use IDs, not object references. |
| One aggregate = one transaction. | Treat this as a consistency guideline; changing multiple aggregates in one transaction requires explicit justification. |
| Keep aggregates small. | Large aggregates cause contention. If you need to lock the whole thing to change a small part, the boundary is wrong. |

### When NOT to use an Aggregate

- A single entity with no children that enforces its own invariants — it is already sufficient as a standalone entity.
- A read model or query result — aggregates are for writes.
- CRUD data with no cross-object invariants — a plain dataclass or persistence model is enough.

> **Aggregates solve a transactional consistency problem. If you do not have that problem, you do not need an aggregate.**

---

## 3. Value Objects

Use a Value Object when:
- identity is irrelevant — two instances with the same values are equal
- the concept has meaningful invariants or behavior
- immutability is appropriate

Good examples:
```text
Money
Email
CPF / NationalId
Address
Percentage
OrderNumber
PhoneNumber
```

```python
class InvalidMoneyAmount(Exception):
    """Raised when a monetary amount violates the domain invariant."""


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvalidMoneyAmount()

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatch()
        return Money(self.amount + other.amount, self.currency)
```

**Do not create:**
```python
class ProductName:
    value: str
```

merely to wrap a primitive. A Value Object earns its existence by providing meaningful domain semantics, invariant enforcement, or behavior — not just by wrapping a type.

---

## 4. Domain Services

Use a Domain Service **only** when:
1. the operation is genuine business logic
2. the logic does not naturally belong to a single Entity or Value Object
3. the operation is meaningful in the domain language

Good candidates:
```text
TaxCalculator
PricingPolicy
EligibilityChecker
FraudRiskEvaluator
```

Avoid:
```text
OrderService
UserService
ProductService
BusinessService
```

when these are merely containers for procedural code with no domain semantics. Prefer entity behavior when possible.

---

## 5. Business Rules vs Validation

Do not confuse validation with business rules. They are distinct concerns that belong in different places.

### Boundary / Input Validation

Concerned with whether the input is structurally correct.

Examples:
```text
required field present
string within length limit
UUID format valid
email syntax valid
JSON structure matches schema
type conversion succeeds
```

These belong **at the boundary**:

```python
class CreateOrderRequest(BaseModel):
    customer_id: UUID
    items: List[OrderItemRequest]
```

### Business Invariants

Concerned with whether an operation is permitted according to domain rules.

Examples:
```text
Order cannot be cancelled after shipment.
Customer cannot purchase beyond their credit limit.
Discount cannot exceed the policy maximum.
Payment cannot be captured twice.
```

These belong **in domain or application code**:

```python
order.cancel()  # domain enforces the invariant
```

Not:
```python
if order.status == "SHIPPED":
    raise HTTPException(status_code=400)  # Bad — business rule at HTTP boundary
```

> **Validation protects structural boundaries. Business invariants protect domain correctness.**

Pydantic validation must not become a replacement for domain modeling. Use it at the edge; model rules in the domain.

---

## 6. Specification Pattern

Do not create a Specification framework by default.

Use it only when predicates are:
- complex
- reusable across multiple contexts
- composable
- meaningful in the domain language

Simple rules should remain simple:
```python
if order.total > threshold:
    ...
```

Do not replace readable conditionals with `Specification`, `AndSpecification`, `OrSpecification`, `NotSpecification` unless real composability is needed.

When a Specification is justified:
```python
class EligibleForDiscount:
    def is_satisfied_by(self, order: Order) -> bool:
        return order.total > Decimal("100") and order.customer.is_loyalty_member
```

---

## 7. Domain Events

Use Domain Events when a meaningful occurrence inside the domain needs to be communicated — to other parts of the same domain, or to be picked up by infrastructure for publishing.

Examples:
```text
OrderPlaced
PaymentConfirmed
OrderCancelled
CustomerRegistered
```

Do not create events for every method call. An event represents something that **happened** and that other parts of the system care about.

```python
@dataclass(frozen=True)
class OrderCancelled:
    order_id: str
    cancelled_at: datetime
    reason: Optional[str] = None
```

### Domain Event vs Integration Event

| | Domain Event | Integration Event |
|---|---|---|
| Scope | Within the domain / bounded context | Across bounded contexts or external systems |
| Owner | Domain layer raises it | Application layer publishes it (via a port) |
| Format | Plain Python dataclass | Serialisable message (e.g., JSON envelope) |
| Example | `OrderCancelled` | `OrderCancelledMessage` sent to SQS |

The application layer is responsible for translating a domain event into an integration event and publishing it through an `EventPublisher` port. The domain does not know about queues, topics, or serialisation formats.

---

## 8. Domain Exceptions

Domain exceptions represent domain invariant violations, not HTTP errors or technical failures.

```python
class OrderCannotBeCancelled(Exception):
    """Raised when cancellation is attempted on a shipped order."""

class PaymentAlreadyCaptured(Exception):
    """Raised when capture is attempted on an already-captured payment."""
```

These must **not** reference HTTP status codes, framework types, or infrastructure concerns. Use named exceptions for domain-rule violations rather than `ValueError`, so boundary mappings remain deliberate and stable.

### Exception propagation flow

```text
Domain raises exception
        ↓
Application catches it (optional — for wrapping or logging)
        ↓
`ExceptionHandler` at the boundary maps it to the external response
        ↓
HTTP response / Lambda error envelope / DLQ message
```

Map known domain and application exceptions to external responses at the outermost boundary. Do not scatter `try/except` across every controller — use centralized exception handling.

Do not expose internal exception messages to clients.
