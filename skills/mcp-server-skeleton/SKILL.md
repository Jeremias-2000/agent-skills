---
name: mcp-server-skeleton
description: "Scaffold, structure, and operate Python MCP servers over Streamable HTTP with the official mcp SDK, Uvicorn, clean architecture layers, structured JSON logging on stderr, and per-request correlation via Context. Activate when creating a new MCP server, adding tools to one, wiring logging/observability, or reviewing an MCP server against this skeleton."
compatibility: "Python 3.11+, mcp SDK 2.x, uvicorn, pytest. Windows/PowerShell and POSIX shells."
metadata:
  version: "1.0.0"
  author: "Jeremias dos Santos Pinheiro"
license: MIT
---

# MCP Server Skeleton Skill

Guides an executing agent to build Python MCP servers that follow the reference skeleton: clean architecture layers, Streamable HTTP transport, structured JSON logging, and MCP Inspector workflows.

Normative language: `MUST`/`SHALL` marks mandatory boundaries; `SHOULD` marks defaults; `MAY` marks project-defined choices.

## When to use

- Scaffolding a new MCP server in Python.
- Adding tools/resources to an existing MCP server built on this skeleton.
- Wiring or reviewing logging, configuration, or entrypoint structure.
- Running the server with MCP Inspector for manual validation.

## Reference implementation

The canonical working example is the `mcp-server-skeleton` project (PokéAPI-backed, 18 tools). Load these references before making decisions in each area:

- Project layout, layers, and dependency flow: `references/structure.md`
- Logging configuration, JsonFormatter, Context correlation: `references/logging.md`
- Inspector workflow, session handshake, verification: `references/inspector.md`

## Non-negotiable boundaries

- The MCP server MUST be served over **Streamable HTTP** via `streamable_http_app()` behind Uvicorn. Do not use stdio unless the project explicitly requires it.
- All logging MUST go to **stderr** (stdout is reserved for the protocol on stdio transports and stays clean on HTTP). One root `StreamHandler(sys.stderr)` with a JSON formatter; no per-module handlers.
- Modules MUST obtain loggers with `logging.getLogger(__name__)` — never hardcoded logger names, never vendored logger objects from a config loader.
- Tools that need request correlation MUST declare `ctx: Context` (from `mcp.server.mcpserver.context`) and pass `extra={"request_id": ctx.request_id}` on log calls. The formatter includes `request_id` only when present.
- Do NOT use `ctx.log()` / `ctx.info()` / the MCP `logging` capability — it is deprecated in the protocol (SEP-2577). Logging stays server-side on stderr.
- Dependency direction MUST point inward: MCP tool → application use case → domain Protocol → infrastructure adapter → external API. Domain code stays framework-free.
- Configuration MUST load through Pydantic `BaseSettings` + `python-dotenv` at the composition boundary; never read env vars inside business logic.
- Third-party HTTP client loggers (`httpx`, `httpcore`) SHOULD be capped at WARNING in `logging.conf` to avoid per-request noise.

## Workflow

1. Inspect the existing project (if any): entrypoint, settings, tool registry, tests. Match its conventions before adding new patterns.
2. Scaffold or extend the layer layout per `references/structure.md`: `application/configuration` + `application/usecases`, `domain/exceptions` + `domain/interfaces`, `infra/adapters` + `infra/entrypoints` + `infra/logging` + `infra/tools`.
3. Register tools explicitly in `infra/tools/registry.py` — no automatic module discovery.
4. Wire logging per `references/logging.md`: `logging.conf` + `JsonFormatter` + `load_logging_config()` called at entrypoint import time, and `log_config=` passed to `uvicorn.run`.
5. Add `ctx: Context` to tools that log or need request metadata.
6. Verify: run the test suite, then boot the server and validate with MCP Inspector per `references/inspector.md` (initialize → notifications/initialized → tools/call).
7. For public repos: add a LICENSE, attribute the data source, and add trademark disclaimers for any third-party IP the API exposes.

## Common pitfalls

- `fileConfig` resolves formatter classes by import — the `class=` path in `logging.conf` MUST be fully qualified and importable from the project root (e.g. `app.mcp.infra.logging.json_formatter.JsonFormatter`).
- With `reload=True`, logging config MUST load in the uvicorn child process (entrypoint import), not only in the parent launcher.
- PowerShell mangles inline JSON in `curl.exe --data-binary`; write request bodies to temp files and use `--data-binary "@file"`.
- MCP Streamable HTTP is stateful: `initialize` returns an `mcp-session-id` header that MUST be sent on every subsequent request, and `notifications/initialized` MUST be sent before `tools/call`.
- Windows stderr is often cp1252 — keep `json.dumps` default `ensure_ascii=True` in the formatter so non-ASCII data (e.g. "Flabébé") cannot raise `UnicodeEncodeError`.
