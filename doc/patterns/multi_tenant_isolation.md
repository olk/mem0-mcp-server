# Multi-Tenant Isolation Pattern

## Overview

The Multi-Tenant Isolation Pattern enforces data isolation between tenants using Mem0's user_id hierarchy with composite encoding.

## Problem

Multi-tenant memory systems must ensure:
- Users cannot access other users' memories
- Agent-scoped memories are isolated
- Session-specific data doesn't leak
- Scope hierarchy is enforced consistently

## Solution

Use composite user_id encoding: `{user_id}:{agent_id}:{session_id}`

```python
class TenantScope(BaseModel):
    """Scope hierarchy for memory isolation."""
    user_id: str = Field(..., description="User ID for user-level isolation")
    agent_id: str | None = Field(None, description="Agent ID for agent-level isolation")
    session_id: str | None = Field(None, description="Session ID for session-level isolation")

    def to_mem0_user_id(self) -> str:
        """Format scope hierarchy for Mem0 user_id."""
        parts = [self.user_id]
        if self.agent_id:
            parts.append(self.agent_id)
        if self.session_id:
            parts.append(self.session_id)
        return ":".join(parts)
```

## Isolation Levels

| Level | Encoding | Example |
|-------|----------|---------|
| User | `user_id` | `alice` |
| User+Agent | `user_id:agent_id` | `alice:agent1` |
| User+Agent+Session | `user_id:agent_id:session_id` | `alice:agent1:session1` |

## Validation

ScopeValidator enforces non-empty IDs:

```python
@staticmethod
def validate_scope(scope: TenantScope) -> bool:
    """Validate required scope components are present."""
    if not scope.user_id or not scope.user_id.strip():
        raise ScopeValidationError(
            message="Invalid scope hierarchy: user_id is required",
            code="ERR_SCOPE_001",
            http_status=400
        )
    # ... validate agent_id and session_id if provided
```

## Cross-Tenant Access Prevention

```python
async def get_memory(memory_id: str, scope: TenantScope) -> MemoryEntry:
    """Get memory with tenant isolation enforcement."""
    mem0_user_id = scope.to_mem0_user_id()

    result = await self.client.get(memory_id=memory_id)
    memory_user_id = result.get("user_id") or result.get("metadata", {}).get("user_id", "")

    if memory_user_id != mem0_user_id:
        logger.warning("Tenant isolation violation: attempted to access memory from different tenant")
        raise ValueError(f"Memory {memory_id} not found")

    return MemoryEntry(...)
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `TenantScope` | Scope hierarchy model |
| `ScopeValidator` | Validates scope parameters |
| `ScopeValidationError` | Error for invalid scope |
| `to_mem0_user_id()` | Encodes scope as Mem0 user_id |

## Constraints

- **FR-10**: Multi-tenant Support for multiple users/agents/apps
- **AC-27**: Full scope hierarchy (org_id/project_id/user_id/agent_id/session_id)
- **AC-28**: Data isolation enforced between tenants
- **E-9 (ERR_SCOPE_001)**: Invalid scope hierarchy

## Benefits

| Benefit | Description |
|---------|-------------|
| **Security** | Guaranteed tenant isolation |
| **Compliance** | Enforces data separation requirements |
| **Simplicity** | Mem0 handles embedding/similarity |
| **Consistency** | Single encoding method across all operations |

## Trade-offs

- **Encoding limits**: Mem0 user_id length constraints apply
- **Query complexity**: Cross-tenant queries not possible (by design)
- **Schema changes**: Scope changes require migration

## Usage

```python
from mcp_server.memory.manager import TenantScope, ScopeValidationError

# User-scoped
user_scope = TenantScope(user_id="alice")
memories = await memory_manager.get_memories(user_scope)

# User+Agent scoped
agent_scope = TenantScope(user_id="alice", agent_id="desktop-assistant")
memories = await memory_manager.search_memories(agent_scope, "preferences")

# User+Agent+Session scoped
session_scope = TenantScope(
    user_id="alice",
    agent_id="desktop-assistant",
    session_id="chat-123"
)
memory = await memory_manager.get_memory("mem_abc", session_scope)

# Invalid scope raises error
try:
    invalid_scope = TenantScope(user_id="")  # Empty user_id
    ScopeValidator.validate_scope(invalid_scope)
except ScopeValidationError as e:
    print(f"Scope error: {e}")
```

## Related Patterns

- [Repository Pattern](./repository_pattern.md) - Memory operations
- [Configuration Validation Pattern](./configuration_validation.md) - Settings validation

## ADR Reference

- ADR-5: Multi-Tenant Isolation Pattern

## Implementation Files

- `src/mcp_server/memory/manager.py`