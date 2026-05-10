# Search Memories Tool (`mcp_server/tools/search_memories.py`)

## Overview

MCP tool implementation for searching long-term memory using semantic similarity. Directly exposes Mem0 AsyncMemory.search() functionality via MCP protocol.

## Input Model

### `SearchMemoriesInput`

**Attributes:**
- `query` (`str`, required): Search query text (1-1000 chars)
- `filters` (`dict[str, Any]`, optional): Filter object with entity IDs and/or metadata filters
- `limit` (`int`, default=10): Maximum results (1-100)
- `page` (`int | None`, optional): Page number for pagination (>=1)
- `page_size` (`int | None`, optional): Results per page (1-100, default 100)
- `rerank` (`bool | None`, optional): Enable/disable reranking (uses config default if None)

**Filter Format:**
```python
filters = {
    "user_id": "alice",           # Entity ID filter
    "AND": [                       # Logical operators
        {"user_id": "alice"},
        {"created_at": {"gte": "2024-01-01"}}
    ]
}
```

**Filter Operators:**
- `in`: Matches any of the values
- `gte`, `lte`, `gt`, `lt`: Comparison operators
- `ne`: Not equal
- `icontains`: Case-insensitive containment
- `*`: Wildcard

**Validators:**
- `validate_query`: Ensures query is non-empty
- `validate_entity_ids_in_filters`: Ensures at least one entity ID in filters

## Output Model

### `MemorySearchResult`

**Attributes:**
- `memory_id` (`str`): Unique identifier for the memory
- `content` (`str`): Memory content text
- `score` (`float`): Relevance score (0.0-1.0)
- `rerank_score` (`float | None`): Reranker score when reranking applied
- `metadata` (`dict[str, Any] | None`): Memory metadata

### `SearchMemoriesOutput`

**Attributes:**
- `results` (`list[MemorySearchResult]`): List of matching memories ranked by relevance

## MCP Tool

### `search_memories(query, filters=None, limit=10, page=None, page_size=None, rerank=None, ctx=None) -> SearchMemoriesOutput`

Search memories using semantic similarity.

**Parameters:**
- `query` (`str`): Search query text (non-empty, max 1000 chars)
- `filters` (`dict[str, Any] | None`): Filter with entity IDs and/or metadata filters
- `limit` (`int`): Maximum results (default 10, max 100)
- `page` (`int | None`): Page number for pagination
- `page_size` (`int | None`): Results per page (default 100, max 100)
- `rerank` (`bool | None`): Enable/disable reranking
- `ctx` (`Context | None`): FastMCP context

**Returns:**
- `SearchMemoriesOutput`: Matching memories with relevance scores

**Raises:**
- `ValueError`: E-5 (ERR_400) if query invalid or no entity ID
- `RuntimeError`: E-3 (ERR_VEC_001) if vector store connection fails
- `RuntimeError`: E-2 (ERR_MEM_001) if memory not initialized

## Usage Example

```python
# Basic search
result = await ctx.tool.call("search_memories", {
    "query": "theme preferences",
    "filters": {"user_id": "alice"},
    "limit": 5
})

# Search with reranking
result = await ctx.tool.call("search_memories", {
    "query": "user interface settings",
    "filters": {"user_id": "alice"},
    "limit": 10,
    "rerank": True
})

# Response structure
# {
#     "results": [
#         {
#             "memory_id": "mem_abc123",
#             "content": "I prefer dark mode",
#             "score": 0.92,
#             "rerank_score": 0.88,
#             "metadata": {"user_id": "alice"}
#         }
#     ]
# }
```

## Error Handling

| Error | Code | Condition |
|-------|------|-----------|
| E-5 | ERR_400 | Invalid query or no entity ID in filters |
| E-3 | ERR_VEC_001 | Vector store connection failed |
| E-2 | ERR_MEM_001 | AsyncMemory not initialized |

## See Also

- [add_memory.py](./tools_add_memory.md) - Add memory tool
- [memory/manager.py](./memory_manager.md) - MemoryManager class