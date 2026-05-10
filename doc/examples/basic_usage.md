# Getting Started with mem0-mcp

This guide helps you quickly set up and use the mem0-mcp server.

## Installation

### Prerequisites

- Python 3.12+
- Redis or other vector store (for production)
- OpenAI API key (or other LLM provider)

### Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/mem0-mcp-server.git
cd mem0-mcp-server

# Install dependencies
uv sync

# Set environment variables
export OPENAI_API_KEY="your-api-key"
```

### Configuration

Create `~/.config/mem0-mcp-server/settings.json`:

```json
{
  "vector_store": {
    "provider": "redis",
    "config": {
      "redis_url": "redis://localhost:6379"
    }
  },
  "llm": {
    "provider": "openai",
    "config": {
      "model": "gpt-4o",
      "temperature": 0.2
    }
  },
  "embedder": {
    "provider": "openai",
    "config": {
      "model": "text-embedding-3-small"
    }
  }
}
```

## Quick Start

### Using SSE Transport (Remote)

```bash
# Run with SSE transport
uv run python -m mcp_server.main

# Server starts on http://0.0.0.0:8080
```

### Using stdio Transport (Local AI Agent)

```bash
# Set transport to stdio
export MCP_TRANSPORT=stdio

# Run server
uv run python -m mcp_server.main
```

## Using MCP Tools

### Add Memory

```python
from mcp_server import mcp

# Via MCP client
result = await client.call_tool("add_memory", {
    "messages": [{"role": "user", "content": "I prefer dark mode"}],
    "user_id": "alice"
})
# Returns: {"results": [{"id": "mem_abc123", "memory": "I prefer dark mode", ...}]}
```

### Search Memories

```python
# Semantic search
result = await client.call_tool("search_memories", {
    "query": "theme preferences",
    "filters": {"user_id": "alice"},
    "limit": 5
})
# Returns: {"results": [{"memory_id": "mem_abc123", "content": "I prefer dark mode", "score": 0.92}]}
```

### Update Memory

```python
result = await client.call_tool("update_memory", {
    "memory_id": "mem_abc123",
    "content": "I prefer dark mode and light text",
    "user_id": "alice"
})
```

### Delete Memory

```python
result = await client.call_tool("delete_memory", {
    "memory_id": "mem_abc123",
    "user_id": "alice"
})
```

### Get Memory

```python
result = await client.call_tool("get_memory", {
    "memory_id": "mem_abc123",
    "user_id": "alice"
})
```

## Multi-Tenant Scoping

```python
# User-scoped
user_scope = {"user_id": "alice"}

# User + Agent scoped
agent_scope = {"user_id": "alice", "agent_id": "desktop-assistant"}

# User + Agent + Session scoped
session_scope = {
    "user_id": "alice",
    "agent_id": "desktop-assistant",
    "session_id": "chat-123"
}
```

## Docker Deployment

```bash
# Using docker-compose
docker-compose up -d

# mem0-mcp available at http://localhost:8050
# Redis available at localhost:6379
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `TRANSPORT` | `sse` | Transport type (stdio, sse) |
| `HOST` | `0.0.0.0` | SSE bind address |
| `PORT` | `8080` | SSE bind port |
| `LOGGING_LEVEL` | `INFO` | Log verbosity |

## Troubleshooting

### Memory Not Initialized

```
ERR_MEM_001: Mem0 AsyncMemory not initialized or unavailable
```

**Solution**: Ensure Redis is running and settings are configured correctly.

### Vector Store Connection Failed

```
ERR_VEC_001: Vector store connection failed during search
```

**Solution**: Check Redis connectivity and `redis_url` in config.

### Invalid Scope

```
ERR_SCOPE_001: Invalid scope hierarchy
```

**Solution**: Ensure `user_id` is provided and non-empty.

## Next Steps

- [Advanced Usage](./advanced_usage.md) - Complex scenarios
- [API Reference](../api/README.md) - Full API documentation
- [Architecture Overview](../architecture/overview.md) - System design