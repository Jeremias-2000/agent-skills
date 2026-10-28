<div align="center">

![MCP Server Skeleton banner](assets/banner.svg)

# MCP Server Skeleton

**A Python MCP server that exposes the Pokémon universe as structured tools.**

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP SDK](https://img.shields.io/badge/mcp-2.2.0-58a6ff)](https://py.sdk.modelcontextprotocol.io/)
[![Transport](https://img.shields.io/badge/transport-Streamable%20HTTP-2ea043)](https://modelcontextprotocol.io/)
[![Data](https://img.shields.io/badge/data-Pok%C3%A9API%20v2-e3350d)](https://pokeapi.co/)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

</div>

Built on the official [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/),
served over **Streamable HTTP** with Uvicorn, and backed by
[PokéAPI v2](https://pokeapi.co/). Configuration via Pydantic `BaseSettings`
and `python-dotenv`; observability via structured JSON logs on stderr.

## Implemented tools

The server currently registers **18 tools**.

### ❤️ Health

| Tool | Description |
|---|---|
| `health_check` | Returns the server health status. |

### ⚡ Pokémon

| Tool | Description |
|---|---|
| `get_pokemon_details` | Returns the main details of a Pokémon by name or Pokédex ID, including types, abilities, stats, dimensions, experience, and sprite. |
| `get_pokemon_species` | Returns species metadata, descriptions, breeding information, generation, habitat, and related species data. |
| `get_pokemon_evolution` | Returns the evolution chain associated with a Pokémon species. |
| `get_pokemon_encounters` | Returns locations, game versions, methods, conditions, and levels where a Pokémon can be encountered. |
| `get_pokemon_forms` | Returns alternate form information for a Pokémon. |
| `compare_pokemon` | Returns the details of two Pokémon so an MCP client can compare them. |

### 🎯 Types, moves, abilities, and items

| Tool | Description |
|---|---|
| `get_type_matchups` | Returns the damage relations for a Pokémon type. |
| `get_move_details` | Returns details for a move, including type, power, accuracy, PP, effects, target, and damage class. |
| `get_ability_details` | Returns an ability's effects and associated Pokémon. |
| `get_item_details` | Returns details for a Pokémon item. |

### 🗺️ Locations

| Tool | Description |
|---|---|
| `get_location_details` | Returns details for a Pokémon world location. |
| `get_location_encounters` | Returns encounter data for a location area. |

### 📚 Paginated catalog tools

| Tool | Description |
|---|---|
| `list_pokemon` | Lists Pokémon resources. |
| `list_moves` | Lists move resources. |
| `list_abilities` | Lists ability resources. |
| `list_items` | Lists item resources. |
| `list_locations` | Lists location resources. |

All catalog tools accept:

- `limit`: number of results, from `1` to `100`, default `20`.
- `offset`: number of results to skip, minimum `0`, default `0`.

The MCP SDK generates the input schema from the Python type annotations and
Pydantic `Field` constraints.

## 🏗️ Architecture

The project follows an explicit dependency flow:

```text
┌─────────────┐   ┌───────────────────┐   ┌────────────────┐   ┌──────────────────────┐   ┌──────────┐
│  MCP tool   │──▶│ application       │──▶│ domain         │──▶│ infrastructure       │──▶│ PokéAPI  │
│  (18 tools) │   │ use case          │   │ Protocol       │   │ adapter (httpx)      │   │ v2       │
└─────────────┘   └───────────────────┘   └────────────────┘   └──────────────────────┘   └──────────┘
```

### Main components

```text
app/
└── mcp/
    ├── application/
    │   ├── configuration/
    │   │   └── settings.py
    │   └── usecases/
    │       ├── get_pokemon_details.py
    │       └── pokeapi_resources.py
    ├── domain/
    │   ├── exceptions.py
    │   └── interfaces/
    │       └── adapters/
    │           └── pokemon_api.py
    └── infra/
        ├── adapters/
        │   └── pokeapi_client.py
        ├── entrypoints/
        │   └── mcp_server.py
        ├── logging/
        │   ├── __init__.py
        │   ├── json_formatter.py
        │   └── logging.conf
        └── tools/
            ├── health.py
            ├── pokemon.py
            ├── resources.py
            └── registry.py
```

The registry performs explicit tool registration. Automatic module discovery is
not used, which keeps dependencies and startup behavior predictable.

The HTTP adapter is isolated from the application and MCP layers. The
`PokemonApi` contract is defined with `typing.Protocol`, allowing use cases to
be tested with fake adapters without making network requests.

## 🔌 MCP SDK behavior

The tools use the documented `mcp==2.2.0` APIs:

- `MCPServer.tool()`
- Function annotations for generated input schemas.
- Structured output for resource tools.
- `ToolAnnotations` for read-only, idempotent, non-destructive tools.
- Streamable HTTP through `streamable_http_app()`.

Resource tools are annotated as:

- Read-only.
- Idempotent.
- Non-destructive.
- Open-world, because they call the external PokéAPI.

## ⚙️ Configuration

Local development settings are stored in `.env` at the project root:

```env
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_RELOAD=false
POKEAPI_BASE_URL=https://pokeapi.co/api/v2
POKEAPI_TIMEOUT=10.0
```

`.env` is ignored by Git and must not contain committed credentials.

Available settings:

| Variable | Default | Description |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Address where Uvicorn listens. |
| `MCP_PORT` | `8000` | Port where Uvicorn listens. |
| `MCP_RELOAD` | `false` | Enables Uvicorn reload during development. |
| `POKEAPI_BASE_URL` | `https://pokeapi.co/api/v2` | PokéAPI v2 base URL. |
| `POKEAPI_TIMEOUT` | `10.0` | HTTP timeout in seconds. |

Settings are loaded by `python-dotenv` and validated with Pydantic
`BaseSettings`. Process environment variables take precedence over `.env`
values.

## 📋 Logging

The server emits structured JSON logs to **stderr**, keeping stdout free for
the MCP protocol. Configuration lives in
`app/mcp/infra/logging/logging.conf` and is applied in two places:

- `app/run.py` passes it to Uvicorn via `log_config`, so Uvicorn's own
  loggers also emit JSON.
- `app/mcp/infra/entrypoints/mcp_server.py` calls `load_logging_config()` at
  import time, which covers the direct `uvicorn` command and the reload
  child process.

Each log line is a single JSON object:

```json
{"time": "2026-10-28T12:00:00.000Z", "level": "INFO", "name": "app.mcp.infra.tools.pokemon", "message": "get_pokemon_details called with pokemon=pikachu", "function": "get_pokemon_details", "line": 17, "file": "pokemon.py"}
```

| Field | Description |
|---|---|
| `time` | UTC timestamp in ISO 8601 format. |
| `level` | Log level (`INFO`, `WARNING`, ...). |
| `name` | Logger name, matching the module's dotted path. |
| `message` | Rendered log message. |
| `function` | Name of the function or method that emitted the record. |
| `line` | Line number of the logging call. |
| `file` | File name of the module that emitted the record. |
| `request_id` | MCP request ID, present only on records emitted inside a tool call. |
| `exception` | Traceback, present only when the record carries `exc_info`. |

To log from a module, use the standard convention — no hardcoded logger
names:

```python
import logging

logger = logging.getLogger(__name__)
```

Records propagate to the root logger, which owns the single stderr handler.
`httpx` and `httpcore` are capped at `WARNING` so routine PokéAPI requests
do not produce per-request lines.

### Request correlation with `Context`

Tools can declare a `ctx: Context` parameter (from
`mcp.server.mcpserver.context`) and the MCP SDK injects the per-request
context. Use `ctx.request_id` to correlate log records with the MCP request
that triggered them:

```python
@server.tool()
async def get_pokemon_details(pokemon: str, ctx: Context) -> dict[str, object]:
    logger.info(
        "get_pokemon_details called with pokemon=%s",
        pokemon,
        extra={"request_id": ctx.request_id},
    )
    ...
```

The `JsonFormatter` includes `request_id` only when the record carries it,
so non-request logs (startup, shutdown) stay unchanged.

Note: `Context` also exposes `ctx.log()` / `ctx.info()` / etc., which stream
log messages **to the MCP client**. That capability is deprecated in the
protocol (SEP-2577) and is intentionally not used here — logging stays on
stderr.

## 🚀 Setup

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r app\requirements.txt
Copy-Item .env.example .env
```

The defaults in `.env.example` work out of the box; adjust them in your local `.env` as needed.

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 🔍 Run the MCP server with MCP Inspector

The project uses **Streamable HTTP**. The MCP server and MCP Inspector run as
two separate processes:

```text
MCP client / Inspector
          |
          v
http://127.0.0.1:8000/mcp
          |
          v
MCP server + Uvicorn
```

### 1. Prerequisites

Install or verify:

- Python 3.11 or newer.
- Node.js and `npx`.
- PowerShell on Windows.

Check the installed versions:

```powershell
python --version
node --version
npx --version
```

### 2. Create and activate the virtual environment

Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r app\requirements.txt
```

If PowerShell blocks script activation, allow it only for the current
PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The server can also be started without activating the environment by using
`.venv\Scripts\python.exe` explicitly.

### 3. Configure the server

The server reads configuration from the `.env` file in the project root:

```env
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_RELOAD=false
POKEAPI_BASE_URL=https://pokeapi.co/api/v2
POKEAPI_TIMEOUT=10.0
```

The default endpoint is:

```text
http://127.0.0.1:8000/mcp
```

If `MCP_PORT` is changed, use the same port in the Inspector's
`--server-url`.

### 4. Start the MCP server

Open PowerShell terminal 1 at the project root and run:

```powershell
.\.venv\Scripts\python.exe -m app.run
```

Expected output includes:

```text
Uvicorn running on http://127.0.0.1:8000
```

Keep this terminal open. The MCP server must remain running while the
Inspector is connected.

You can verify the server manually with an MCP initialization request:

```powershell
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"manual-check","version":"1.0"}}}'
Set-Content .\mcp-request.json $body -NoNewline

curl.exe --max-time 5 `
  -X POST `
  -H "Accept: application/json, text/event-stream" `
  -H "Content-Type: application/json" `
  --data-binary "@.\mcp-request.json" `
  http://127.0.0.1:8000/mcp
```

The response should contain `HTTP 200` and an MCP `initialize` result.
Remove the temporary request file after validation:

```powershell
Remove-Item .\mcp-request.json
```

### 5. Start MCP Inspector

Open PowerShell terminal 2 at the project root and run:

```powershell
npx --yes @modelcontextprotocol/inspector@latest `
  --transport http `
  --server-url http://127.0.0.1:8000/mcp
```

The Inspector starts a local web interface, normally at:

```text
http://127.0.0.1:6274
```

The command prints an authenticated URL similar to:

```text
http://127.0.0.1:6274?MCP_INSPECTOR_API_TOKEN=<token>
```

Always open the complete URL printed by the command, including the
`MCP_INSPECTOR_API_TOKEN` query parameter. The token is generated for the
local Inspector process.

### 6. Use the Inspector

1. Open the authenticated Inspector URL in a browser.
2. Confirm that the transport is `HTTP`.
3. Confirm that the server URL is:
   `http://127.0.0.1:8000/mcp`.
4. Open the **Tools** section.
5. Select a tool.
6. Fill in the generated input form.
7. Execute the tool and inspect the structured response.

The Inspector should display all currently registered tools, including:

```text
health_check
get_pokemon_details
get_pokemon_species
get_pokemon_evolution
get_pokemon_encounters
get_pokemon_forms
compare_pokemon
get_type_matchups
get_move_details
get_ability_details
get_item_details
get_location_details
get_location_encounters
list_pokemon
list_moves
list_abilities
list_items
list_locations
```

For example, call `get_pokemon_details` with:

```json
{
  "pokemon": "pikachu"
}
```

Or call `list_pokemon` with:

```json
{
  "limit": 5,
  "offset": 0
}
```

The pagination schema is generated by the MCP SDK. `limit` accepts values
from `1` to `100`, and `offset` must be zero or greater.

### 7. Stop the processes

Stop the Inspector with `Ctrl+C` in terminal 2, then stop the MCP server with
`Ctrl+C` in terminal 1.

If a previous process is still holding a port, inspect the listeners:

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 8000,6274,6275 } |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

Stop only the process ID that belongs to the project or Inspector:

```powershell
Stop-Process -Id <PID>
```

The MCP server uses port `8000` by default. The Inspector web interface uses
port `6274` and its sandbox commonly uses port `6275`.

### 8. Alternative direct Uvicorn command

Instead of `app.run`, you can start the ASGI application directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn `
  app.mcp.infra.entrypoints.mcp_server:app `
  --host 127.0.0.1 `
  --port 8000
```

If you use this command, the `MCP_HOST` and `MCP_PORT` values from `.env` are
not applied automatically because the host and port are supplied explicitly
to Uvicorn.

### Troubleshooting

#### `Connection refused`

Confirm that the MCP server is running and that the URL uses the configured
port:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

#### `Address already in use`

Another process is using port `8000`. Stop the previous server or change
`MCP_PORT` in `.env`, then use the matching port in `--server-url`.

#### Inspector page does not open

Check that Node.js and `npx` are available:

```powershell
node --version
npx --version
```

Then run the Inspector command again and open the full authenticated URL
printed in the terminal.

## ⚠️ Error handling

Expected failures use domain exceptions with stable error codes:

- `invalid_pokemon_identifier`
- `pokemon_not_found`
- `pokemon_api_unavailable`
- `pokemon_api_invalid_response`

HTTP and JSON handling remain inside the PokéAPI adapter.

## 📖 API documentation

- [PokéAPI v2 documentation](https://pokeapi.co/docs/v2)
- [PokéAPI v2 resource index](https://pokeapi.co/api/v2/)
- [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)

## 📄 License

This project is licensed under the [MIT License](LICENSE).

Data is provided by [PokéAPI](https://pokeapi.co/), a free and open API
licensed under the BSD 3-Clause License. Please respect its
[fair use policy](https://pokeapi.co/docs/v2#info): cache responses when
possible and avoid high-frequency requests.

Pokémon and Pokémon character names are trademarks of Nintendo, Creatures
Inc., and GAME FREAK inc. This project is not affiliated with, endorsed by,
or sponsored by them or by PokéAPI.
