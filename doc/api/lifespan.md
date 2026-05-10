# Lifespan Management (`mcp_server/lifespan.py`)

## Overview

Graceful shutdown handler with SIGTERM/SIGINT handling and resource cleanup. Implements FastMCP lifespan context manager for proper resource lifecycle.

## Lifespan Context Manager

### `server_lifespan(server: FastMCP) -> async generator`

FastMCP lifespan context manager for graceful shutdown.

This async context manager handles FastMCP server startup and shutdown. On startup, it initializes Mem0 AsyncMemory via `memory_lifespan`. On shutdown, it cleans up all resources with timeout enforcement.

**Parameters:**
- `server` (`FastMCP`): FastMCP server instance

**Yields:**
- `dict`: Contains `'memory'` (AsyncMemory) and `'manager'` (MemoryManager)

**Timeout:**
- Cleanup enforced within 300 seconds (MTTR < 5 minutes per NFR-5)

**Usage:**

```python
from fastmcp.server.lifespan import lifespan
from mcp_server.lifespan import server_lifespan

# Used internally by FastMCP
@mcp.server.lifespan(server_lifespan)
async def main():
    pass
```

## Helper Functions

### `_cleanup_with_timeout(memory_lifespan_result: dict) -> None`

Cleanup memory resources with timeout enforcement.

This function ensures cleanup completes within MTTR < 5 minutes (NFR-5). Uses `asyncio.timeout` to prevent cleanup from blocking shutdown indefinitely.

**Parameters:**
- `memory_lifespan_result` (`dict`): Dict containing 'memory' (AsyncMemory) and 'manager' (MemoryManager)

**Timeout:**
- `CLEANUP_TIMEOUT_SECONDS = 300`

**Error Handling:**
- Logs error if cleanup exceeds timeout (MTTR violation)
- Logs error if cleanup fails

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CLEANUP_TIMEOUT_SECONDS` | `300` | MTTR < 5 minutes enforcement |

## Flow Diagram

```
Server Startup
     │
     ▼
┌─────────────────────────────────┐
│   memory_lifespan context       │
│   (AsyncMemory init)            │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│   Yield memory/manager to      │
│   FastMCP request handlers      │
└─────────────────────────────────┘
     │
     ▼ Server Shutdown
┌─────────────────────────────────┐
│   _cleanup_with_timeout()      │
│   - aclose AsyncMemory          │
│   - 300s timeout enforcement    │
└─────────────────────────────────┘
```

## See Also

- [mcp_server/__init__.py](./mcp_server_init.md) - FastMCP singleton instance
- [transport.py](./transport.md) - Transport selection