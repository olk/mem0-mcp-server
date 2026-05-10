# Transport Strategy Pattern

## Overview

The Transport Strategy Pattern selects between stdio and SSE transports at runtime based on configuration, enabling flexible deployment options.

## Problem

Different deployment scenarios require different transports:
- Local AI agent integration → stdio (stdin/stdout)
- Remote HTTP connections → SSE (Server-Sent Events)

Hardcoding transport selection creates inflexible deployment.

## Solution

Use configuration-driven strategy selection:

```python
class TransportType(Enum):
    """Transport protocol types."""
    STDIO = "stdio"
    SSE = "sse"

async def run_transport(transport: str, host: str, port: int, mcp_server: FastMCP) -> None:
    """Run appropriate transport based on configuration."""
    try:
        transport_type = TransportType(transport)
    except ValueError:
        raise ValueError(f"Invalid transport: {transport}. Must be stdio or sse")

    if transport_type == TransportType.STDIO:
        await _run_stdio_transport(mcp_server)
    else:
        await _run_sse_transport(host, port, mcp_server)
```

## Strategy Selection Flow

```
Configuration (TRANSPORT env var / config file)
         │
         ▼
┌─────────────────────────────────┐
│      run_transport()             │
│   - Validate transport type      │
│   - Parse to TransportType enum   │
└─────────────────────────────────┘
         │
         ├── "stdio" ──► _run_stdio_transport()
         │                   │
         │                   ▼
         │              run_stdio_async()
         │                   │
         │                   ▼
         │              stdin/stdout MCP
         │
         └── "sse" ──────► _run_sse_transport()
                             │
                             ▼
                        run_http_async()
                             │
                             ▼
                        SSE endpoint + health check
```

## Implementation

### stdio Transport

```python
async def _run_stdio_transport(mcp_server: FastMCP) -> None:
    """Run stdio transport for local AI agent integration."""
    try:
        await mcp_server.run_stdio_async()
    except Exception as e:
        raise RuntimeError(
            "ERR_STDIO_001: stdin/stdout not available for stdio transport"
        ) from e
```

### SSE Transport

```python
async def _run_sse_transport(host: str, port: int, mcp_server: FastMCP) -> None:
    """Run SSE transport with health check endpoint."""
    # Register health check for monitoring
    register_health_check(mcp_server)

    try:
        await mcp_server.run_http_async(transport="sse", host=host, port=port)
    except Exception as e:
        raise RuntimeError(
            "ERR_SSE_001: Port already in use or SSE transport failed to start"
        ) from e
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TRANSPORT` | `sse` | Transport type: "stdio" or "sse" |
| `HOST` | `0.0.0.0` | Server bind address (SSE only) |
| `PORT` | `8080` | Server bind port (SSE only) |

## Constraints

- **IC-4**: Correct transport function selection based on TRANSPORT value
- **FR-11**: stdio Transport support
- **FR-12**: SSE Transport support
- **FR-18**: Transport Selection based on configuration
- **AC-45**: transport=sse calls run_sse_async()
- **AC-46**: transport=stdio calls run_stdio_async()

## Error Handling

| Error | Code | Description |
|-------|------|-------------|
| E-10 | ERR_STDIO_001 | stdin/stdout not available |
| E-11 | ERR_SSE_001 | Port in use or SSE failed |
| E-16 | ERR_TRANS_001 | Invalid transport configuration |

## Benefits

| Benefit | Description |
|---------|-------------|
| **Flexibility** | Single code base, multiple transports |
| **Configuration** | Transport selection via config/env |
| **Extensibility** | Easy to add new transports |
| **Testability** | Mock transport selection |

## Trade-offs

- **Complexity**: More moving parts than hardcoded transport
- **Error handling**: Multiple error paths to consider
- **Testing**: Requires testing both transport paths

## Usage

```python
# Via environment variables
TRANSPORT=stdio python -m mcp_server.main
TRANSPORT=sse HOST=0.0.0.0 PORT=8050 python -m mcp_server.main

# Via code
from mcp_server.transport import run_transport

await run_transport(
    transport="sse",
    host="0.0.0.0",
    port=8050,
    mcp_server=mcp
)
```

## Related Patterns

- [Async Context Manager Pattern](./async_context_manager.md) - Lifespan management
- [SafeLogger Pattern](./safe_logger.md) - Log/output separation

## ADR Reference

- ADR-6: Transport Strategy Pattern

## Implementation Files

- `src/mcp_server/transport.py`