# MCP Inspector workflow and verification

How to run and manually verify an MCP server built on this skeleton.

## Starting the server

```powershell
.\.venv\Scripts\python.exe -m app.run
```

Expected: JSON startup lines on stderr, ending with `Uvicorn running on http://127.0.0.1:8000`.

## Starting the Inspector

```powershell
npx --yes @modelcontextprotocol/inspector@latest `
  --transport http `
  --server-url http://127.0.0.1:8000/mcp
```

Open the full authenticated URL it prints (includes `MCP_INSPECTOR_API_TOKEN`). Default UI port: 6274.

In the UI: transport **HTTP**, server URL `http://127.0.0.1:8000/mcp`, then **Tools** → select a tool → fill the form → execute.

## Programmatic verification (without the Inspector)

Streamable HTTP is **stateful**. The handshake:

1. `POST /mcp` with `initialize` → response headers include `mcp-session-id: <id>`.
2. `POST /mcp` with `notifications/initialized` (header `mcp-session-id: <id>`).
3. `POST /mcp` with `tools/call` (same session header).

Every request needs headers `Accept: application/json, text/event-stream` and `Content-Type: application/json`.

### PowerShell pitfall

PowerShell mangles inline JSON passed to `curl.exe --data-binary`. Write bodies to temp files:

```powershell
Set-Content .\req-init.json '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"check","version":"1.0"}}}' -NoNewline
Set-Content .\req-notif.json '{"jsonrpc":"2.0","method":"notifications/initialized"}' -NoNewline
Set-Content .\req-call.json '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"health_check","arguments":{}}}' -NoNewline

$out = curl.exe --max-time 5 -s -D - -X POST -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" --data-binary "@.\req-init.json" http://127.0.0.1:8000/mcp
$sid = ([regex]::Match(($out -join "`n"), 'mcp-session-id:\s*(\S+)')).Groups[1].Value

curl.exe --max-time 5 -s -X POST -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -H "mcp-session-id: $sid" --data-binary "@.\req-notif.json" http://127.0.0.1:8000/mcp
curl.exe --max-time 5 -s -X POST -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -H "mcp-session-id: $sid" --data-binary "@.\req-call.json" http://127.0.0.1:8000/mcp

Remove-Item .\req-init.json, .\req-notif.json, .\req-call.json
```

A successful `tools/call` returns SSE:

```text
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"text":"ok","type":"text"}],"isError":false,...}}
```

And the server stderr shows the correlated log:

```json
{"time": "...", "level": "INFO", "name": "app.mcp.infra.tools.health", "message": "health_check called", "function": "health_check", "line": 13, "file": "health.py", "request_id": "2"}
```

## Common failure modes

- `Session not found` (-32600): missing/invalid `mcp-session-id` header, or the session was terminated (a 400 on initialize terminates it).
- `Parse error` (-32700): malformed JSON body — usually PowerShell quoting; use body files.
- 404 on subsequent requests: session expired or server restarted; re-initialize.

## Stopping

`Ctrl+C` each process, or stop by PID. Verify ports are released:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,6274,6275 }
```

## Inspector capability panel

The Inspector shows server capabilities from the `initialize` handshake. For this skeleton: **Tools** ✓, **Resources/Prompts** ✓ (empty), **Logging/Completions/Tasks** ✗. The Logging ✗ is expected: the MCP logging capability is deprecated (SEP-2577) and this skeleton logs server-side to stderr instead.
