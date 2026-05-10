# Advanced Usage

This guide covers complex scenarios and advanced configurations.

## Custom LLM Providers

### Anthropic

```json
{
  "llm": {
    "provider": "anthropic",
    "config": {
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.3,
      "max_tokens": 2000
    }
  }
}
```

### Local Ollama

```json
{
  "llm": {
    "provider": "ollama",
    "config": {
      "model": "llama3",
      "ollama_base_url": "http://localhost:11434"
    }
  },
  "embedder": {
    "provider": "ollama",
    "config": {
      "model": "nomic-embed-text",
      "ollama_base_url": "http://localhost:11434"
    }
  }
}
```

### Azure OpenAI

```json
{
  "llm": {
    "provider": "azure_openai",
    "config": {
      "model": "gpt-4o",
      "azure_deployment": "gpt-4o",
      "azure_api_version": "2024-02-01",
      "azure_endpoint": "https://your-resource.openai.azure.com"
    }
  }
}
```

## Vector Store Configuration

### Redis (Default)

```json
{
  "vector_store": {
    "provider": "redis",
    "config": {
      "redis_url": "redis://localhost:6379",
      "collection_name": "mem0",
      "embedding_model_dims": 1536
    }
  }
}
```

### Chroma (Local)

```json
{
  "vector_store": {
    "provider": "chroma",
    "config": {
      "chroma_path": "/path/to/chroma_db"
    }
  }
}
```

### Qdrant (Cloud)

```json
{
  "vector_store": {
    "provider": "qdrant",
    "config": {
      "qdrant_url": "https://your-cluster.qdrant.io",
      "qdrant_api_key": "your-api-key",
      "collection_name": "mem0"
    }
  }
}
```

### PostgreSQL pgvector

```json
{
  "vector_store": {
    "provider": "pgvector",
    "config": {
      "pgvector_connection_string": "postgresql://user:pass@localhost:5432/mem0",
      "pgvector_hnsw": true
    }
  }
}
```

## Reranker Configuration

Rerankers improve search relevance by reordering vector search results.

### Cohere (Default)

```json
{
  "reranker": {
    "provider": "cohere",
    "config": {
      "model": "rerank-english-v3.0",
      "top_k": 10
    }
  }
}
```

### HuggingFace Local

```json
{
  "reranker": {
    "provider": "huggingface",
    "config": {
      "model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
      "device": "cpu",
      "batch_size": 32
    }
  }
}
```

### Disable Reranking

```python
result = await client.call_tool("search_memories", {
    "query": "theme",
    "filters": {"user_id": "alice"},
    "rerank": False  # Disable reranking for this query
})
```

## Advanced Search Filters

### Date Range Filtering

```python
result = await client.call_tool("search_memories", {
    "query": "project updates",
    "filters": {
        "AND": [
            {"user_id": "alice"},
            {"created_at": {"gte": "2024-01-01"}}
        ]
    }
})
```

### Metadata Filtering

```python
result = await client.call_tool("search_memories", {
    "query": "important",
    "filters": {
        "user_id": "alice",
        "metadata": {
            "priority": "high"
        }
    }
})
```

### Multi-Entity Filtering

```python
result = await client.call_tool("search_memories", {
    "query": "context",
    "filters": {
        "OR": [
            {"user_id": "alice"},
            {"user_id": "bob"}
        ]
    }
})
```

## Batch Operations

### Multiple Memory Addition

```python
# Add multiple memories
memories = [
    {"role": "user", "content": "User prefers email notifications"},
    {"role": "user", "content": "User works on Pacific timezone"},
    {"role": "user", "content": "User's favorite language is Python"}
]

for memory in memories:
    await client.call_tool("add_memory", {
        "messages": [memory],
        "user_id": "alice"
    })
```

### Pagination

```python
# Get first page
result1 = await client.call_tool("search_memories", {
    "query": "preferences",
    "filters": {"user_id": "alice"},
    "limit": 10,
    "page": 1,
    "page_size": 10
})

# Get second page
result2 = await client.call_tool("search_memories", {
    "query": "preferences",
    "filters": {"user_id": "alice"},
    "limit": 10,
    "page": 2,
    "page_size": 10
})
```

## Multi-Agent Scenarios

```python
# Different agents for different tasks
agents = {
    "email-assistant": {"user_id": "alice", "agent_id": "email-assistant"},
    "code-assistant": {"user_id": "alice", "agent_id": "code-assistant"},
    "research-assistant": {"user_id": "alice", "agent_id": "research-assistant"}
}

# Each agent has isolated memory
for agent_id, scope in agents.items():
    await client.call_tool("add_memory", {
        "messages": [{"role": "user", "content": f"Agent {agent_id} initialized"}],
        **scope
    })
```

## Session Tracking

```python
# Track conversation sessions
session_scope = {
    "user_id": "alice",
    "agent_id": "chatbot",
    "session_id": "session-2024-05-09-001"
}

# Store session context
await client.call_tool("add_memory", {
    "messages": [{"role": "user", "content": "Let's discuss project timeline"}],
    **session_scope
})

# Retrieve session memories
result = await client.call_tool("search_memories", {
    "query": "project timeline",
    "filters": session_scope
})
```

## Custom Metadata

```python
# Store additional context
await client.call_tool("add_memory", {
    "messages": [{"role": "user", "content": "Meeting scheduled for tomorrow"}],
    "user_id": "alice",
    "metadata": {
        "type": "calendar_event",
        "priority": "high",
        "tags": ["meeting", "schedule"]
    }
})
```

## Error Handling Best Practices

```python
try:
    result = await client.call_tool("add_memory", {
        "messages": [{"role": "user", "content": "test"}],
        "user_id": "alice"
    })
except Exception as e:
    if "ERR_MEM_001" in str(e):
        # Memory not initialized - check Redis and config
        print("Memory service unavailable")
    elif "ERR_SCOPE_001" in str(e):
        # Invalid scope - check user_id
        print("Invalid scope provided")
    else:
        # Unknown error - log and retry
        print(f"Unexpected error: {e}")
```

## Performance Optimization

### Connection Pooling

Redis connection pooling is handled automatically by Mem0.

### Batch Embedding

For bulk operations, group messages to minimize API calls:

```python
# Instead of individual calls, batch similar operations
batch_messages = [
    {"role": "user", "content": "Setting 1"},
    {"role": "user", "content": "Setting 2"},
    # ...
]
await client.call_tool("add_memory", {
    "messages": batch_messages,
    "user_id": "alice"
})
```

## See Also

- [Basic Usage](./basic_usage.md) - Getting started guide
- [API Reference](../api/README.md) - Full API documentation
- [Architecture Overview](../architecture/overview.md) - System design