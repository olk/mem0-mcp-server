# Transport Selection (`mcp_server/transport.py`)

## Overview

Transport selection module for FastMCP server. Supports stdio and SSE transports based on configuration.

## Enums

### `TransportType`

Transport type enum for MCP transport protocol types.

| Value | Description |
|-------|-------------|
| `STDIO` | Standard I/O transport for local AI agent integration |
| `SSE` | Server-Sent Events transport for remote HTTP connections |

**Usage:**

```python
from mcp_server.transport import TransportType

if transport == TransportType.STDIO:
    await mcp_server.run_stdio_async()
```

## Functions

### `run_transport(transport: str, host: str, port: int, mcp_server: FastMCP) -> None`

Run the appropriate transport based on configuration.

This function implements the Strategy Pattern (DP-4) to select between stdio and SSE transports at runtime based on the TRANSPORT configuration.

**Parameters:**
- `transport` (`str`): Transport type ("stdio" or "sse")
- `host` (`str`): Server bind address for SSE transport
- `port` (`int`): Server bind port for SSE transport
- `mcp_server` (`FastMCP`): FastMCP server instance

**Raises:**
- `ValueError`: If transport value is invalid
- `RuntimeError`: E-10 for stdio errors, E-11 for SSE errors

### `_run_stdio_transport(mcp_server: FastMCP) -> None`

Run stdio transport for local AI agent integration.

**Parameters:**
- `mcp_server` (`FastMCP`): FastMCP server instance

**Raises:**
- `RuntimeError`: E-10 if stdin/stdout not available

**Usage:**

```python
await _run_stdio_transport(mcp)
# Server runs via stdin/stdout
```

### `_run_sse_transport(host: str, port: int, mcp_server: FastMCP) -> None`

Run SSE transport for remote HTTP connections.

Includes health check endpoint registration at `/health` for monitoring.

**Parameters:**
- `host` (`str`): Server bind address
- `port` (`int`): Server bind port
- `mcp_server` (`FastMCP`): FastMCP server instance

**Raises:**
- `RuntimeError`: E-11 if port is in use or SSE transport fails

**Usage:**

```python
await _run_sse_transport("0.0.0.0", 8050, mcp)
# Server runs HTTP SSE on port 8050
```

## Strategy Pattern

```
Configuration
     │
     ▼
┌─────────────────────────────────┐
│   run_transport()               │
│   - Validate transport type      │
│   - Route to appropriate func   │
└─────────────────────────────────┘
     │
     ├── "stdio" ──► _run_stdio_transport()
     │                   │
     │                   ▼
     │               run_stdio_async()
     │
     └── "sse" ──────► _run_sse_transport()
                         │
                         ▼
                    run_http_async()
                    + health check
```

## Error Codes

| Error | Code | Description |
|-------|------|-------------|
| E-10 | ERR_STDIO_001 | stdin/stdout not available for stdio transport |
| E-11 | ERR_SSE_001 | Port already in use or SSE transport failed to start |

## See Also

- [lifespan.py](./lifespan.md) - Lifespan context manager
- [utils/health.py](./health.md) - Health check endpoint