# Pattern Guide Index

This directory contains architectural and design pattern documentation for the mem0-mcp server.

## Core Patterns

| Pattern | Description |
|---------|-------------|
| [fastmcp_singleton.md](./fastmcp_singleton.md) | Single FastMCP instance enforcement |
| [async_context_manager.md](./async_context_manager.md) | Mem0 AsyncMemory lifecycle management |
| [repository_pattern.md](./repository_pattern.md) | Memory operations abstraction |
| [multi_tenant_isolation.md](./multi_tenant_isolation.md) | Tenant data isolation |
| [transport_strategy.md](./transport_strategy.md) | Transport selection (stdio/SSE) |
| [safe_logger.md](./safe_logger.md) | MCP stdout/library stderr separation |

## Pattern Relationships

```
FastMCP Singleton Pattern
        │
        ├── uses ──► Async Context Manager Pattern
        │
        ├── uses ──► Repository Pattern
        │
        └── coordinates ──► Transport Strategy Pattern

SafeLogger Output Separation Pattern
        │
        └── used by ──► Transport Strategy Pattern

Multi-Tenant Isolation Pattern
        │
        └── implemented via ──► Repository Pattern
```

## By Category

### Server Patterns
- FastMCP Singleton Pattern
- Transport Strategy Pattern

### Memory Patterns
- Async Context Manager Pattern
- Repository Pattern
- Multi-Tenant Isolation Pattern

### Observability Patterns
- SafeLogger Output Separation Pattern

## Quick Links

- [API Reference](../api/README.md)
- [Usage Examples](../examples/README.md)
- [Architecture Overview](../architecture/overview.md)