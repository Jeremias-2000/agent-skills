# Python Backend Engineering Standard — Logging

## 1. Core Principles

Logging is an **infrastructure concern** that MUST be configured centrally and consumed consistently across all layers.

### Key Rules
1. Logging configuration must be centralized in `logging.conf` for local/non-Lambda runtimes or `configure_json_logging` for Lambda/structured runtimes.
2. Loggers must be obtained through the selected runtime's configured logger factory.
3. Log entries must include class, method, timestamp, and line number when configured.
4. Domain and Application layers must not know about logging implementation details.
5. Sensitive information must never be logged.
6. Log levels must be configurable without code changes.

### Domain Layer Logging — Pragmatic Exception

The architecture standard requires that the domain layer has no infrastructure dependencies. Logging sits at the boundary of this rule: obtaining a logger via `get_logger(__name__)` is generally accepted as a pragmatic exception because the stdlib `logging` module is a language primitive, not a framework.

Direct domain logging is exceptional. Prefer boundary logging or domain events. **Do not log from the domain** when:
- the log event is really an application-level observability concern (e.g., "use case started"), or
- the log would couple domain behavior to a specific observability format.

**Preferred patterns by context:**

| Context | Preferred approach |
|---|---|
| Domain invariant violation | Raise a domain exception; let the boundary exception handler log it. |
| Meaningful state transition | Domain may log via `get_logger(__name__)` — this is acceptable. |
| Use-case outcome | Log in the application layer, not the domain. |
| Audit trail / event sourcing | Emit a domain event; infrastructure subscribes and records it. |

The goal is that the domain remains independently testable and free of framework logging config. Using `logging.getLogger` does not violate that goal; importing a log formatter or a custom observability library does.

---

## 2. Local logging resolver

### Implementation

```python
# infrastructure/logging_resolver.py
import configparser
import logging
import logging.config
import os
from pathlib import Path

class LoggingResolver:
    """Finds and loads logging configuration, then exposes a logger factory."""

    def __init__(self) -> None:
        self.config_path = self._find_config()
        self._load_config()

    def _find_config(self) -> Path:
        """Find logging.conf in common project locations."""
        candidates = [
            Path.cwd() / "logging.conf",
            Path.cwd() / "config" / "logging.conf",
            Path(__file__).parent / "logging.conf",
            Path(__file__).parent.parent / "logging.conf",
        ]
        for path in candidates:
            if path.exists():
                return path
        return Path.cwd() / "logging.conf"

    def _load_config(self) -> None:
        """Load local logging configuration or configure an explicit fallback."""
        if self.config_path.exists():
            try:
                logging.config.fileConfig(self.config_path, disable_existing_loggers=False)
            except (OSError, ValueError, TypeError, configparser.Error) as error:
                raise RuntimeError(
                    f"Could not load logging config from {self.config_path}"
                ) from error
        else:
            self._fallback()

    def _fallback(self) -> None:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, None)
        if not isinstance(level, int):
            raise ValueError(f"Unsupported LOG_LEVEL: {level_name}")
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def get_logger(name: str) -> logging.Logger:
    """Return a logger after runtime bootstrap has configured logging."""
    return logging.getLogger(name)


# Backward-compatible alias
get_configured_logger = get_logger
```

---

## 3. logging.conf — Plaintext Format (non-Lambda)

Use this for local development, Django, Flask, or any runtime that writes to files or a terminal.

```ini
[loggers]
keys=root,app,domain,infrastructure,entrypoints

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=default,detailed

[logger_root]
level=INFO
handlers=consoleHandler

[logger_app]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=app
propagate=0

[logger_domain]
level=DEBUG
handlers=consoleHandler
qualname=domain
propagate=0

[logger_infrastructure]
level=INFO
handlers=fileHandler
qualname=infrastructure
propagate=0

[logger_entrypoints]
level=INFO
handlers=consoleHandler
qualname=entrypoints
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=default
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=DEBUG
formatter=detailed
args=('app.log', 'a')

[formatter_default]
format=%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - line %(lineno)d - %(message)s
datefmt=%Y-%m-%d %H:%M:%S

[formatter_detailed]
format=%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s - line %(lineno)d - %(message)s
datefmt=%Y-%m-%d %H:%M:%S.%f
```

---

## 4. Structured / JSON Logging (Lambda and CloudWatch)

AWS Lambda writes to CloudWatch Logs. CloudWatch can parse structured JSON natively, enabling log filtering, metric extraction, and tracing correlation without regex. **Use JSON logging for all Lambda functions.**

### When to use JSON logging

| Runtime | Recommended format |
|---|---|
| AWS Lambda | JSON (structured) |
| ECS / Fargate with CloudWatch | JSON (structured) |
| Local development | Plaintext (human-readable) |
| Django / Flask with file logging | Plaintext or JSON depending on log aggregator |

### JSON formatter setup (no extra dependencies)

```python
# infrastructure/json_logging.py
import json
import logging
import traceback
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """
    Emits log records as single-line JSON.
    Compatible with CloudWatch Logs Insights and OpenSearch.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Correlation IDs injected via LoggerAdapter extra (see section 5)
        for key in ("request_id", "correlation_id", "trace_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(payload, default=str)


def configure_json_logging(level: str = "INFO") -> None:
    """
    Replace all handlers on the root logger with a single JSON stdout handler.
    Call this once at the Lambda module level (outside the handler function)
    so it runs during the cold start and is reused across warm invocations.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    normalized_level = level.upper()
    numeric_level = getattr(logging, normalized_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Unsupported log level: {level}")
    root.setLevel(numeric_level)
```

### Lambda handler bootstrap

```python
# entrypoints/lambdas/my_handler.py
import logging
import os
from infrastructure.json_logging import configure_json_logging

# Cold-start: configure once, reused on warm invocations
configure_json_logging(level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    logger.info("Lambda invoked", extra={"request_id": context.aws_request_id})
    # ... delegate to use case
```

### Runtime bootstrap

When code runs both locally and in Lambda, use one composition-root bootstrap that selects the runtime-specific setup:

```python
# infrastructure/logging_resolver.py  (extended version)
import os

def setup_logging() -> None:
    """Configure logging once based on the current runtime environment."""
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        from infrastructure.json_logging import configure_json_logging
        configure_json_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    else:
        # Local runtime uses logging.conf or the explicit LOG_LEVEL fallback.
        LoggingResolver()
```

Call `setup_logging()` once at the composition root or Lambda module scope.

---

## 5. LoggerAdapter — Thread-Safe Context Enrichment

Use `LoggerAdapter` or `ContextLogger` for per-request context. Do not use `logging.setLogRecordFactory()` for request context.

### Usage

```python
import logging
from infrastructure.logging_resolver import get_logger


from typing import Dict, Optional


class ContextLogger:
    """
    Wraps a standard logger with per-instance extra context.
    Safe for concurrent use — does not modify global logging state.
    """

    def __init__(self, name: str, extra: Optional[Dict] = None) -> None:
        base = get_logger(name)
        self._adapter = logging.LoggerAdapter(base, extra or {})

    def with_context(self, **kwargs) -> "ContextLogger":
        """Return a new ContextLogger with additional key-value context merged in."""
        merged = {**self._adapter.extra, **kwargs}
        new = ContextLogger.__new__(ContextLogger)
        new._adapter = logging.LoggerAdapter(self._adapter.logger, merged)
        return new

    def __getattr__(self, name: str):
        return getattr(self._adapter, name)
```

### Example — application layer

```python
class CreateOrderUseCase:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository
        self._logger = ContextLogger("application.orders")

    def execute(self, command: CreateOrderCommand) -> OrderResult:
        log = self._logger.with_context(customer_id=str(command.customer_id))
        log.info("Creating order")
        order = Order.create(command.customer_id, command.items)
        self.repository.save(order)
        log.info("Order created", extra={"order_id": str(order.id)})
        return OrderResult(order_id=order.id)
```

In JSON output this produces:
```json
{"level": "INFO", "logger": "application.orders", "message": "Order created", "customer_id": "...", "order_id": "..."}
```

---

## 6. Layer-Specific Guidelines

### Domain Layer

Prefer boundary logging or domain events. Direct domain logging is exceptional and limited to meaningful state transitions when those alternatives cannot provide equivalent diagnostic value. Raise domain exceptions for invariant violations — let the application or exception handler log those.

```python
class Order:
    def cancel(self) -> None:
        logger = get_logger(__name__)

        if self.status == OrderStatus.SHIPPED:
            # Do NOT log here — raise and let the application layer observe it
            raise OrderCannotBeCancelled()

        self.status = OrderStatus.CANCELLED
        logger.info("Order cancelled", extra={"order_id": self.id})
```

### Application Layer

```python
class CreateOrderUseCase:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository
        self._logger = ContextLogger("application.orders")

    def execute(self, command: CreateOrderCommand) -> OrderResult:
        log = self._logger.with_context(customer_id=str(command.customer_id))
        log.info("Use case started")
        # ... business logic ...
        log.info("Use case completed", extra={"order_id": str(order.id)})
        return OrderResult(order_id=order.id)
```

### Infrastructure Layer

```python
class DynamoDBOrderRepository:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self._logger = get_logger("infrastructure.dynamodb")

    async def get_by_id(self, order_id: str) -> Optional[Order]:
        self._logger.debug("Fetching order", extra={"order_id": order_id})
        # DynamoDB operations...
        return result
```

### Entrypoint Layer

```python
@router.post("/orders")
async def create_order(request: CreateOrderRequest):
    logger = logging.getLogger("entrypoints.api")
    logger.info("Order request received", extra={"customer_id": str(request.customer_id)})

    # The configured boundary adapter delegates failures to ExceptionHandler.
    result = use_case.execute(command)
    logger.info("Order created", extra={"order_id": str(result.order_id)})
    return {"order_id": result.order_id}
```

---

## 7. Best Practices

### DO ✅
- Use `get_logger(__name__)` consistently.
- Use `LoggerAdapter` / `ContextLogger` to attach request or correlation context.
- Log meaningful business events and state changes.
- Use appropriate levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
- Include context (IDs, state, relevant data) as `extra` fields — especially in JSON mode.
- Log unknown exceptions with `exc_info=True`; expected known failures use contextual logging without a traceback by default. See `references/python-standard-exceptions.md`.
- Guard expensive debug operations:
  ```python
  if logger.isEnabledFor(logging.DEBUG):
      payload = render_debug_payload(data)
      logger.debug("Payload details", extra={"payload": payload})
  ```
- Use JSON logging for Lambda / CloudWatch runtimes.
- Configure logging once at module/composition-root scope for Lambda.

### DON'T ❌
- Never log sensitive information (passwords, tokens, secrets, PII).
- Don't hardcode log levels.
- Don't use `print()` for logging.
- Don't over-log in tight loops.
- Don't use `logging.setLogRecordFactory()` for per-request context — use `LoggerAdapter`.
- Don't configure logging inside use cases or domain objects.
- Don't log framework internals.

---

## 8. Testing Logging

### Using caplog

```python
import logging

def test_order_cancellation_logged(caplog):
    caplog.set_level(logging.INFO)

    order = Order(id="order-123", status=OrderStatus.PENDING)
    order.cancel()

    assert any("Order cancelled" in r.message for r in caplog.records)
```

### Using LoggerAdapter / ContextLogger in tests

```python
from unittest.mock import MagicMock, patch

def test_use_case_logs_start():
    mock_repo = MagicMock()

    with patch("application.orders.create_order.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        use_case = CreateOrderUseCase(mock_repo)
        use_case.execute(CreateOrderCommand(customer_id="cust-1", items=[]))

        mock_logger.info.assert_any_call("Use case started")
```

---

## 9. Logging Checklist

### Configuration
- [ ] `logging_resolver.py` implemented and used as the single logger factory.
- [ ] JSON logging configured for Lambda / CloudWatch runtimes.
- [ ] Plaintext logging configured for local / non-Lambda runtimes.
- [ ] Log levels are environment-configurable (e.g., `LOG_LEVEL` env var).
- [ ] `logging.setLogRecordFactory()` is NOT used for per-request context.

### Implementation
- [ ] Domain logs only meaningful state transitions; invariant violations are raised, not logged.
- [ ] Application logs use-case boundaries (start, success, failure).
- [ ] Infrastructure logs technical operations with IDs and `exc_info=True` on errors.
- [ ] Entrypoints log request/response boundaries.
- [ ] `LoggerAdapter` / `ContextLogger` used for correlation ID propagation.

### Quality
- [ ] No sensitive information logged.
- [ ] Appropriate log levels used.
- [ ] Unknown exceptions are logged once with `exc_info=True`; known expected failures are not redundantly logged.
- [ ] Performance impact considered (guard clauses on DEBUG).
- [ ] Logs are useful for debugging and production incident investigation.
