# Repository Pattern

## Overview

The Repository Pattern abstracts Mem0 AsyncMemory operations behind a repository interface, separating memory storage logic from tool implementations.

## Problem

Direct coupling between MCP tools and Mem0 AsyncMemory creates:
- Tight coupling to Mem0 client API
- Difficult testing (can't mock easily)
- Hard to switch storage backends
- Duplicated query logic across tools

## Solution

MemoryManager acts as repository with async methods:
- `add_memory()` - Store new memory
- `search_memories()` - Semantic search
- `get_memory()` - Retrieve by ID
- `update_memory()` - Modify existing
- `delete_memory()` - Remove memory
- `list_memories()` - List with filtering

## Implementation

```python
# src/mcp_server/memory/manager.py

class MemoryManager:
    """Multi-tenant memory manager using Mem0 AsyncMemory."""

    def __init__(
        self,
        mem0_client: Any,
        llm_config: LLMConfig | None = None,
        vector_store_config: VectorStoreConfig | None = None,
        embedder_config: EmbedderConfig | None = None,
        reranker_config: RerankerConfig | None = None
    ):
        self.client = mem0_client
        self.llm_config = llm_config or LLMConfig()
        self.vector_store_config = vector_store_config or VectorStoreConfig()
        self.embedder_config = embedder_config or EmbedderConfig()
        self.reranker_config = reranker_config

    async def add_memory(
        self,
        scope: TenantScope,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Add a memory entry with tenant scope."""
        ScopeValidator.validate_scope(scope)
        mem0_user_id = scope.to_mem0_user_id()

        result = await self.client.add(
            messages=[{"role": "user", "content": content}],
            user_id=mem0_user_id,
            metadata={**metadata or {}, "user_id": scope.user_id}
        )
        # ... return MemoryEntry
```

## Multi-Tenant Scoping

The repository enforces multi-tenant isolation:

```python
# user_id encoding: {user_id}:{agent_id}:{session_id}
scope = TenantScope(user_id="alice", agent_id="agent1")
mem0_user_id = scope.to_mem0_user_id()  # "alice:agent1"

# All operations scope to tenant
await memory_manager.search_memories(
    scope=scope,
    query="preferences"
)
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `TenantScope` | Scope hierarchy (user/agent/session) |
| `ScopeValidator` | Validates scope inputs |
| `MemoryEntry` | Memory result data model |
| `MemoryManager` | Repository implementation |

## Benefits

| Benefit | Description |
|---------|-------------|
| **Testability** | Mock repository in unit tests |
| **Abstraction** | Tools don't depend on Mem0 API |
| **Flexibility** | Easy to add caching, metrics |
| **Single responsibility** | Memory logic isolated in manager |

## Constraints

- **DP-3**: Repository Pattern for memory operations
- **FR-10**: Multi-tenant Support with isolated memory spaces
- **AC-28**: Data isolation enforced between tenants

## Usage

```python
from mcp_server.memory.manager import MemoryManager, TenantScope

# In lifespan, manager is created and attached to server state
manager = MemoryManager(mem0_client)
server.state.memory = manager

# In tools, access via context
memory = ctx.request_context.lifespan_context.get("memory")
scope = TenantScope(user_id="alice")
result = await memory.add_memory(scope, "User prefers dark mode")
```

## Alternative Implementations

### Specification Pattern
When filtering and search are complex, use Specification Pattern:
- Build filter specifications
- Combine with AND/OR/NOT
- Apply to repository methods

### Simple Repository
For straightforward operations, Simple Repository is adequate:
- Direct Mem0 client wrapper
- Minimal abstraction
- Lower maintenance burden

## Related Patterns

- [Async Context Manager Pattern](./async_context_manager.md) - Lifecycle management
- [Multi-Tenant Isolation Pattern](./multi_tenant_isolation.md) - Tenant scoping

## ADR Reference

- ADR-7: Repository Pattern for Mem0 operations

## Implementation Files

- `src/mcp_server/memory/manager.py`