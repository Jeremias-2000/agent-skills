# Structured JSON logging

All logs go to **stderr** as single-line JSON. One root handler; every module uses `logging.getLogger(__name__)`.

## logging.conf

`app/mcp/infra/logging/logging.conf`:

```ini
[loggers]
keys=root,httpx,httpcore

[handlers]
keys=consoleHandler

[formatters]
keys=jsonFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_httpx]
level=WARNING
handlers=
qualname=httpx
propagate=1

[logger_httpcore]
level=WARNING
handlers=
qualname=httpcore
propagate=1

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=jsonFormatter
args=(sys.stderr,)

[formatter_jsonFormatter]
class=app.mcp.infra.logging.json_formatter.JsonFormatter
format=%(message)s
```

Rules:

- `class=` for the formatter MUST be a fully-qualified importable path from the project root.
- `disable_existing_loggers` is not set → defaults applied by `fileConfig(path, disable_existing_loggers=False)` in the loader; keeps uvicorn/SDK loggers alive.
- `httpx`/`httpcore` capped at WARNING so routine API calls don't emit per-request lines.
- No `datefmt` — the formatter emits its own UTC timestamp.

## JsonFormatter

`app/mcp/infra/logging/json_formatter.py`:

```python
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
            "file": record.filename,
        }
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)
```

Fields: `time` (UTC ISO 8601), `level`, `name` (dotted module path), `message`, `function`, `line`, `file`; optional `request_id` (only inside tool calls) and `exception` (only with `exc_info`).

Keep `json.dumps` default `ensure_ascii=True` — Windows stderr is often cp1252 and non-ASCII payloads must not raise `UnicodeEncodeError`.

## Loader

`app/mcp/infra/logging/__init__.py`:

```python
import logging.config
from pathlib import Path

LOGGING_CONF = Path(__file__).resolve().parent / "logging.conf"


def load_logging_config(path: Path = LOGGING_CONF) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"logging.conf not found at: {path}")
    logging.config.fileConfig(path, disable_existing_loggers=False)
```

Returns `None` — it configures, it does not vend loggers.

## Load points (both required)

1. `mcp_server.py` module scope, before `create_server()` — covers the direct `uvicorn` command and the reload child process.
2. `run.py` passes `log_config=str(LOGGING_CONF)` to `uvicorn.run` — uvicorn's own loggers (`uvicorn.error`, `uvicorn.access`) emit JSON too.

The MCP SDK's internal `configure_logging()` (`basicConfig` with a Rich handler) runs inside `MCPServer.__init__`; since our config loads first, it is a harmless no-op. No duplicate lines.

## Module usage

```python
import logging

logger = logging.getLogger(__name__)
```

## Request correlation with Context

Tools declare `ctx: Context` (from `mcp.server.mcpserver.context`); the SDK injects the per-request context. Pass `request_id` via `extra`:

```python
from mcp.server.mcpserver.context import Context

@server.tool()
async def get_details(name: str, ctx: Context) -> dict[str, object]:
    logger.info("get_details called with name=%s", name,
                extra={"request_id": ctx.request_id})
    ...
```

Do NOT use `ctx.log()` / `ctx.info()` / `ctx.warning()` / `ctx.error()` — the MCP logging capability (server→client `notifications/message`) is deprecated as of protocol 2026-07-28 (SEP-2577). Logging stays server-side on stderr. The MCP Inspector "Logging" capability row will show as not enabled; that is expected and correct.

## Tests

`tests/test_logging.py` covers: missing conf raises `FileNotFoundError`; loaded config emits parseable JSON on stderr with expected `level`/`name`/`message`/`function`/`line`/`file`; `exception` field present with `exc_info`; `request_id` field present when passed via `extra`. Insert the project root into `sys.path` at the top of the test module so `app.*` imports resolve.
