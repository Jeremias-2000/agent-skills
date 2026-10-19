# Python Backend Engineering Standard — Exception Handling

This reference is the authoritative guide for classifying, mapping, logging, and exposing exceptions at backend boundaries. It complements the domain, application, infrastructure, and logging references; it does not move transport concerns into business code.

## 1. Canonical Handler

Use `ExceptionHandler` from `exceptions.exception_handler` at the final boundary. Deviations require an existing project convention or framework constraint and explicit justification:

```python
from exceptions.exception_handler import ExceptionHandler
```

Do not create competing central handlers.

The handler translates failures at the outermost boundary. Domain and application code must not import HTTP exceptions, Lambda response types, queue envelopes, or framework response classes.

## 2. Categories and Public Codes

Keep internal categories separate from public codes. Categories describe ownership and operational behavior:

- domain
- application
- validation
- authentication
- authorization
- infrastructure
- timeout
- unexpected

Use a stable `ErrorCode` Enum for public semantics. Error-code values must not be HTTP status codes. Domain-rule violations must use named domain exceptions; do not use `ValueError` as the domain exception contract. `ValueError` remains valid for local configuration or parsing failures where no domain contract is being defined.

## 3. Shared Result and Public Envelope

The transport-neutral handler result SHOULD contain:

```text
error_code
safe_message
http_status (optional)
correlation_id (optional)
retryable
internal_log_context
```

Field ownership:

- `error_code`, `safe_message`: public candidates;
- `http_status`: HTTP adapter only;
- `correlation_id`: propagated when available;
- `retryable`: adapter metadata, not a retry decision;
- `internal_log_context`: internal only and never serialized.

External responses use the smallest contract required by the transport. When an envelope is appropriate, use:

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "Resource not found",
  "correlation_id": "request-123"
}
```

Include `correlation_id` only when available. Never expose exception text, stack traces, credentials, tokens, or unnecessary personal data.

For new projects, `500` is the default HTTP status for unexpected failures. Other category-to-status mappings are project-defined. Existing projects preserve their established API and transport contracts.

## 4. Mapping Precedence

Mappings must be deterministic:

1. exact or most-specific exception type;
2. registered base-class mapping;
3. generic unknown-error fallback.

Known failures return their documented `ErrorCode` and safe message. Unknown failures return a stable internal-error code and generic message.

## 5. Transport Adapters

Share classification, codes, and the neutral result across transports, but keep adapters thin and transport-specific:

- HTTP adapters translate the result into the existing response contract.
- Lambda adapters translate it into the event/runtime response contract.
- Worker and queue adapters decide acknowledgement, retry, reprocessing, or DLQ behavior from result metadata.

Retry and DLQ policy belongs to the transport adapter, not to a universal HTTP-oriented handler. Do not impose an HTTP envelope on non-HTTP transports.

## 6. Logging and Correlation

The final boundary owns logging of unhandled exceptions:

- unknown exceptions: log once with `exc_info=True` and correlation context;
- expected known failures: log contextual information without a traceback by default;
- inner layers: add context only when it provides diagnostic value, then re-raise or wrap without duplicating the final error log.

Propagate a correlation ID when the runtime provides one. Do not impose one universal generation mechanism across runtimes. Follow the logging reference for runtime configuration and sensitive-data protection.

## 7. Exception Chaining

When translating an exception into a new exception, preserve the cause:

```python
try:
    provider.charge(command)
except ProviderTimeout as error:
    raise PaymentUnavailable() from error
```

Chaining preserves diagnosis internally while the boundary controls the safe public message.

## 8. Testing

Test the handler and each adapter at its boundary. Cover:

- known category and `ErrorCode` mappings;
- specific mapping taking precedence over a base class;
- named domain exceptions;
- unknown-error fallback and safe public output;
- shared result fields and optional correlation ID;
- project-defined HTTP mappings;
- worker retry and DLQ decisions;
- one traceback-aware log for unknown failures;
- sensitive-data exclusion;
- chained original causes;
- preservation of existing public contracts.
