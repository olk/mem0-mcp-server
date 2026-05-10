# FastMCP Singleton Pattern

## Overview

The FastMCP Singleton Pattern ensures exactly one FastMCP instance exists in the application, enforcing MCP compliance and preventing multiple instance issues.

## Problem

The MCP specification requires exactly one FastMCP server instance. Multiple instances could cause:
- Tool registration conflicts
- Protocol violations
- Resource contention

## Solution

Implements a singleton pattern with thread-safe initialization that raises an error if a second instance is attempted.

## Implementation

```python
# src/mcp_server/__init__.py

_mcp_instance: FastMCP | None = None
_mcp_instance_count: int = 0
_mcp_lock: threading.Lock = threading.Lock()

def get_mcp_instance() -> FastMCP:
    """Get or create the single FastMCP instance."""
    global _mcp_instance, _mcp_instance_count

    with _mcp_lock:
        if _mcp_instance is not None:
            raise RuntimeError(
                "ERR_MCP_INIT: Multiple FastMCP instances detected or initialization failed"
            )

        _mcp_instance = FastMCP(
            name="Mem0-MCP Server",
            instructions="Server exposes Mem0 API via MCP",
            lifespan=server_lifespan
        )
        _mcp_instance_count += 1

    return _mcp_instance

# Create the single FastMCP instance (IC-2, IC-5)
mcp: FastMCP = get_mcp_instance()
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `_mcp_lock` | Thread-safe initialization lock |
| `_mcp_instance` | Singleton instance storage |
| `_mcp_instance_count` | Instance creation counter |
| `get_mcp_instance()` | Thread-safe singleton getter |

## Constraints

- **IC-2**: Exactly one FastMCP instance named 'Mem0-MCP Server'
- **IC-5**: All @mcp.tool decorators MUST bind to the single FastMCP instance
- **AC-1**: Server initializes with MCP compliance
- **AC-2**: Tools discoverable via MCP protocol
- **AC-3**: Protocol messages follow MCP format

## Error Handling

**E-1 (ERR_MCP_INIT)**: Multiple FastMCP instances detected

```python
try:
    mcp = get_mcp_instance()
except RuntimeError as e:
    # Handle multiple instance detection
    logger.error(f"MCP Init Error: {e}")
```

## Advantages

1. **Enforced compliance**: Single instance ensures MCP specification adherence
2. **Thread safety**: Lock prevents race conditions during initialization
3. **Clear error messaging**: Descriptive error on duplicate instantiation
4. **Testability**: `reset_mcp_instance()` enables test isolation

## Trade-offs

- **Coupling**: Module-level singleton creates implicit dependencies
- **Testing complexity**: Requires reset between test cases
- **Global state**: Difficult to swap implementations

## Usage

```python
# All tools use the singleton
from mcp_server import mcp

@mcp.tool()
async def my_tool(ctx):
    # Uses the single mcp instance
    pass
```

## Related Patterns

- [Async Context Manager Pattern](./async_context_manager.md) - Lifespan management
- [Repository Pattern](./repository_pattern.md) - Memory operations abstraction

## ADR Reference

- ADR-1: FastMCP Singleton Pattern
- ADR-3: MCP Protocol Compliance

## Implementation Files

- `src/mcp_server/__init__.py`