# Project structure and layers

Reference layout for a Python MCP server on the official `mcp` SDK.

## Directory tree

```text
app/
├── run.py                        # launcher: sys.path setup + uvicorn.run(..., log_config=...)
└── mcp/
    ├── application/
    │   ├── configuration/
    │   │   └── settings.py       # Pydantic BaseSettings + python-dotenv, lru_cache get_settings()
    │   └── usecases/             # one class per business capability
    │       ├── get_<entity>_details.py
    │       └── <api>_resources.py
    ├── domain/
    │   ├── exceptions.py         # domain exception hierarchy with stable `code` strings
    │   └── interfaces/
    │       └── adapters/
    │           └── <api>_api.py  # typing.Protocol contract for the external API
    └── infra/
        ├── adapters/
        │   └── <api>_client.py   # httpx implementation of the Protocol
        ├── entrypoints/
        │   └── mcp_server.py     # create_server() + streamable_http_app(); loads logging config
        ├── logging/
        │   ├── __init__.py       # load_logging_config()
        │   ├── json_formatter.py # JsonFormatter
        │   └── logging.conf      # fileConfig ini
        └── tools/
            ├── health.py         # health_check tool
            ├── <entity>.py       # entity tools
            ├── resources.py      # read-only resource/catalog tools
            └── registry.py       # register_tools(): explicit registration, no auto-discovery
tests/
└── test_logging.py
```

## Dependency flow

```text
MCP tool  →  application use case  →  domain Protocol  →  infrastructure adapter  →  external API
```

- **Domain** is framework-free: exceptions and `typing.Protocol` contracts only.
- **Application** orchestrates use cases, validates identifiers, raises domain exceptions.
- **Infrastructure** implements Protocols with httpx, registers MCP tools, owns logging/config.
- **Entrypoints** compose everything: `create_server()` builds the `MCPServer`, injects use cases, calls `register_tools()`.

## Entrypoint pattern

```python
# app/mcp/infra/entrypoints/mcp_server.py
from mcp.server.mcpserver import MCPServer
from app.mcp.infra.logging import load_logging_config
# ... other imports

load_logging_config()  # runs in the uvicorn child process too

def create_server() -> MCPServer:
    settings = get_settings()
    api: SomeApi = SomeApiClient(settings)
    usecase = GetDetailsUseCase(api)
    server = MCPServer(name="<server-name>")
    register_tools(server, usecase, ...)
    return server

mcp = create_server()
app = mcp.streamable_http_app()
```

## Launcher pattern

```python
# app/run.py
import sys
from pathlib import Path
import uvicorn

def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.mcp.application.configuration.settings import get_settings
    from app.mcp.infra.logging import LOGGING_CONF

    settings = get_settings()
    uvicorn.run(
        "app.mcp.infra.entrypoints.mcp_server:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=settings.mcp_reload,
        log_config=str(LOGGING_CONF),  # uvicorn's own loggers also emit JSON
    )
```

## Tool registration

Explicit, in `registry.py` — no auto-discovery:

```python
def register_tools(server, get_details, resources) -> None:
    register_health_tools(server)
    register_entity_tools(server, get_details)
    register_resource_tools(server, resources)
    logger.info("MCP tools registered")
```

Tools use `@server.tool()` with type annotations (the SDK generates input schemas), `ToolAnnotations(readOnlyHint=True, ...)` for read-only tools, and `structured_output=True` where supported.

## Settings

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix="", extra="ignore")
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_reload: bool = False
    # external API settings...

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`.env` at project root, loaded with `python-dotenv` (`override=False` so process env wins). `.env` MUST be in `.gitignore`.

## requirements.txt

```text
mcp==2.2.0
httpx==0.28.1
python-dotenv==1.2.4
pydantic-settings==2.11.0
uvicorn[standard]==0.34.0
```
