# Async Context Manager Pattern

## Overview

The Async Context Manager Pattern manages Mem0 AsyncMemory lifecycle (init/cleanup) via async context manager, ensuring single shared instance across all tools.

## Problem

Mem0 AsyncMemory requires proper initialization at startup and cleanup at shutdown. Without careful management:
- Connections may leak
- Resources may not be released
- Cleanup may not complete within MTTR requirements

## Solution

Use `@asynccontextmanager` to create a lifespan context manager that:
1. Initializes AsyncMemory on server startup
2. Yields the memory instance to request handlers
3. Performs cleanup with timeout enforcement on shutdown

## Implementation

```python
# src/mcp_server/lifespan.py

@lifespan
async def server_lifespan(server: "FastMCP"):
    """FastMCP lifespan context manager for graceful shutdown."""
    from mcp_server.memory.lifespan import memory_lifespan

    settings = getattr(server, '_settings', None)
    if settings is None:
        raise Mem0InitializationError(
            "Server settings not found. Ensure main.py has set mcp._settings."
        )

    async with memory_lifespan(
            llm_config=settings.llm,
            vector_store_config=settings.vector_store,
            embedder_config=settings.embedder,
        ) as memory_lifespan_result:
        manager = memory_lifespan_result.get("manager")

        try:
            yield memory_lifespan_result
        finally:
            # Cleanup with timeout enforcement
            await _cleanup_with_timeout(memory_lifespan_result)
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `@lifespan` decorator | FastMCP lifespan hook |
| `memory_lifespan` | AsyncMemory initialization context |
| `_cleanup_with_timeout()` | Timeout-enforced cleanup |

## Cleanup Flow

```
Server Shutdown Signal (SIGTERM/SIGINT)
            │
            ▼
┌─────────────────────────────────┐
│   _cleanup_with_timeout()       │
│   - asyncio.timeout(300s)       │
│   - await memory.aclose()       │
└─────────────────────────────────┘
            │
            ├── Success ──► Connections closed
            │
            └── Timeout ──► MTTR violation logged
```

## Constraints

- **IC-3**: Mem0 AsyncMemory instances MUST be created and closed by asynccontextmanager
- **AC-59**: SIGTERM/SIGINT handled
- **AC-60**: Cleanup executed
- **AC-61**: Connections closed properly
- **NFR-5**: MTTR < 5 minutes (300 second timeout)

## Advantages

1. **Automatic cleanup**: Guaranteed resource release
2. **Timeout enforcement**: Prevents blocking shutdown
3. **Testability**: Easy to mock in tests
4. **Single instance**: Ensures one AsyncMemory per server

## Trade-offs

- **Complexity**: Requires understanding of async context managers
- **Debugging**: Stack traces may be less obvious
- **Error handling**: Cleanup errors may be swallowed

## Usage

```python
# FastMCP handles lifespan automatically
# No manual cleanup needed

@mcp.tool()
async def my_tool(ctx):
    # Memory available via ctx.request_context.lifespan_context
    memory = ctx.request_context.lifespan_context.get("memory")
    # Use memory...
# On server shutdown, cleanup happens automatically
```

## Related Patterns

- [FastMCP Singleton Pattern](./fastmcp_singleton.md) - Server instance management
- [Repository Pattern](./repository_pattern.md) - Memory operations abstraction

## ADR Reference

- ADR-1: FastMCP Singleton Pattern
- IC-3: AsyncMemory lifecycle management

## Implementation Files

- `src/mcp_server/lifespan.py`
- `src/mcp_server/memory/lifespan.py`