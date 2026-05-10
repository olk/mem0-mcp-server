# FastMCP Server (`mcp_server/__init__.py`)

## Overview

FastMCP server initialization module that provides the single FastMCP instance named "Mem0-MCP Server" for exposing Mem0 API functionality via MCP protocol.

## Installation

```python
from mcp_server import mcp, get_mcp_instance, reset_mcp_instance
```

## Classes

### `FastMCP` (imported from fastmcp)

The FastMCP server instance that exposes Mem0 memory tools via MCP protocol.

**Attributes:**
- `name`: "Mem0-MCP Server"
- `instructions`: "Server exposes Mem0 API via MCP"

## Functions

### `get_mcp_instance() -> FastMCP`

Get or create the single FastMCP instance.

This function implements the singleton pattern to ensure exactly one FastMCP instance exists (IC-2). On subsequent calls after the first instance is created, it raises `RuntimeError`.

**Returns:**
- `FastMCP`: The single FastMCP instance

**Raises:**
- `RuntimeError`: ERR_MCP_INIT if multiple instances are detected

### `reset_mcp_instance() -> None`

Reset the MCP instance (for testing purposes only).

This function is intended for testing scenarios where the singleton needs to be reset between test cases.

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `mcp` | `FastMCP` instance | The singleton FastMCP server instance |

## Usage Example

```python
from mcp_server import mcp

# The mcp instance is already initialized and ready
# All @mcp.tool decorators in tools/ module bind to this instance

# To reset (testing only):
from mcp_server import reset_mcp_instance
reset_mcp_instance()
```

## Error Handling

**E-1 (ERR_MCP_INIT)**: Multiple FastMCP instances detected or initialization failed.

```python
try:
    mcp = get_mcp_instance()
except RuntimeError as e:
    print(f"MCP initialization error: {e}")
```

## See Also

- [lifespan.py](./lifespan.md) - Lifespan context manager for resource lifecycle
- [transport.py](./transport.md) - Transport selection (stdio vs SSE)
- [memory/manager.py](./memory_manager.md) - Multi-tenant memory management