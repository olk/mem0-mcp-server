# API Reference Index

This directory contains API documentation for the mem0-mcp server components.

## Core Modules

| Module | Description |
|--------|-------------|
| [mcp_server_init.md](./mcp_server_init.md) | FastMCP server initialization and singleton pattern |
| [lifespan.md](./lifespan.md) | Lifespan context manager for resource lifecycle |
| [transport.md](./transport.md) | Transport selection (stdio vs SSE) |
| [memory_manager.md](./memory_manager.md) | Multi-tenant memory management with Mem0 AsyncMemory |
| [safe_logger.md](./safe_logger.md) | SafeLogger for MCP stdout/library stderr separation |

## Tools

| Tool | Description |
|------|-------------|
| [tools_add_memory.md](./tools_add_memory.md) | add_memory MCP tool for storing memories |
| [tools_search_memories.md](./tools_search_memories.md) | search_memories MCP tool for semantic search |

## Configuration

| Module | Description |
|--------|-------------|
| [config_settings.md](./config_settings.md) | Pydantic configuration models and validation |
| [config_loader.md](./config_loader.md) | Configuration file loading with tilde expansion |

## Quick Links

- [Architecture Overview](../architecture/overview.md)
- [Pattern Guides](../patterns/README.md)
- [Usage Examples](../examples/README.md)