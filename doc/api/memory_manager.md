# Memory Manager (`mcp_server/memory/manager.py`)

## Overview

Multi-tenant memory scoping manager using Mem0 AsyncMemory. Enforces scope hierarchy (user_id/agent_id/session_id) for memory isolation via composite user_id. Supports multiple vector store backends and embedding models.

## Classes

### `TenantScope`

Represents the scope hierarchy for memory isolation using Mem0 v3 API.

**Attributes:**
- `user_id` (`str`, required): User ID for user-level isolation
- `agent_id` (`str | None`, optional): Agent ID for agent-level isolation
- `session_id` (`str | None`, optional): Session ID for session-level isolation

**Methods:**

#### `to_mem0_user_id() -> str`

Format scope hierarchy for Mem0 user_id. Format: `{user_id}:{agent_id}:{session_id}` (only includes non-None levels).

#### `to_display_string() -> str`

Human-readable scope string for logging.

**Example:**

```python
scope = TenantScope(user_id="alice", agent_id="agent1", session_id="session1")
mem0_id = scope.to_mem0_user_id()  # "alice:agent1:session1"
```

### `ScopeValidationError`

E-9 (ERR_SCOPE_001): Invalid scope hierarchy provided.

**Attributes:**
- `code` (`str`): Error code "ERR_SCOPE_001"
- `http_status` (`int`): HTTP 400
- `message` (`str`): Error description

### `MemoryManager`

Multi-tenant memory manager using Mem0 AsyncMemory.

**Constructor Parameters:**
- `mem0_client` (`Any`): Mem0 AsyncMemory client instance
- `llm_config` (`LLMConfig | None`): Optional LLM configuration for Multi-LLM support
- `vector_store_config` (`VectorStoreConfig | None`): Optional vector store configuration
- `embedder_config` (`EmbedderConfig | None`): Optional embedder configuration
- `reranker_config` (`RerankerConfig | None`): Optional reranker configuration

**Methods:**

#### `add_memory(scope: TenantScope, content: str, metadata: dict | None) -> MemoryEntry`

Add a memory entry with tenant scope.

#### `search_memories(scope: TenantScope, query: str, limit: int = 10, metadata_filters: dict | None = None, rerank: bool | None = None) -> list[MemoryEntry]`

Search memories within tenant scope with optional reranking.

#### `get_memories(scope: TenantScope, limit: int = 50) -> list[MemoryEntry]`

Get all memories within tenant scope.

#### `get_memory(memory_id: str, scope: TenantScope) -> MemoryEntry`

Get a specific memory entry by ID within tenant scope.

#### `delete_memory(memory_id: str, scope: TenantScope) -> bool`

Delete a memory entry within tenant scope.

#### `delete_all_memories(scope: TenantScope) -> bool`

Delete all memories within tenant scope.

#### `update_memory(memory_id: str, scope: TenantScope, content: str, metadata: dict | None = None) -> MemoryEntry`

Update an existing memory entry.

#### `list_memories(scope: TenantScope, limit: int = 50) -> list[MemoryEntry]`

List all memories within tenant scope.

**Properties:**
- `llm_provider` (`str`): Configured LLM provider name
- `llm_model` (`str`): Configured LLM model name
- `vector_store_provider` (`str`): Configured vector store provider name
- `embedder_provider` (`str`): Configured embedder provider name
- `embedder_model` (`str`): Configured embedder model name
- `embedder_dimensions` (`int`): Configured embedding dimensions
- `reranker_provider` (`str | None`): Configured reranker provider name

## Usage Example

```python
from mcp_server.memory.manager import MemoryManager, TenantScope

# Create scope
scope = TenantScope(user_id="alice", agent_id="agent1")

# Add memory
entry = await memory_manager.add_memory(
    scope=scope,
    content="User prefers dark mode",
    metadata={"source": "preferences"}
)

# Search memories
results = await memory_manager.search_memories(
    scope=scope,
    query="theme preferences",
    limit=10
)
```

## Multi-Tenant Isolation

MemoryManager enforces data isolation between tenants:

1. All operations validate `TenantScope`
2. user_id encoding: `{user_id}:{agent_id}:{session_id}`
3. Cross-tenant access is blocked

## See Also

- [config/settings.py](./config_settings.md) - Configuration models
- [tools/add_memory.py](./tools_add_memory.md) - MCP tool implementation