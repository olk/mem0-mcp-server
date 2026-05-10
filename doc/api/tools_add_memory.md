# Add Memory Tool (`mcp_server/tools/add_memory.py`)

## Overview

MCP tool implementation for storing information in long-term memory. Directly exposes Mem0 AsyncMemory.add() functionality via MCP protocol.

## Input Model

### `AddMemoryInput`

**Attributes:**
- `messages` (`list[dict[str, str]]`, required): Conversation turns with 'role' and 'content'. Min length: 1.
- `user_id` (`str | None`, optional): User identifier for memory scoping. Max 255 chars.
- `agent_id` (`str | None`, optional): Agent identifier for memory scoping. Max 255 chars.
- `run_id` (`str | None`, optional): Run identifier for memory scoping. Max 255 chars.
- `metadata` (`dict[str, Any] | None`, optional): Custom key-value metadata.
- `infer` (`bool`, default=True): Set to False to skip LLM inference and store text as-is.

**Validators:**
- `validate_messages`: Ensures messages is non-empty with valid role/content dicts.
- `validate_entity_ids`: Ensures at least one of user_id, agent_id, or run_id is provided.

## Output Model

### `MemoryResult`

**Attributes:**
- `id` (`str`): Unique identifier for the created memory
- `memory` (`str`): Memory content
- `metadata` (`dict[str, Any] | None`): Memory metadata
- `event` (`str`): Event type (e.g., 'ADD')

### `AddMemoryOutput`

**Attributes:**
- `results` (`list[MemoryResult]`): List of created memory entries

## MCP Tool

### `add_memory(messages, user_id=None, agent_id=None, run_id=None, metadata=None, infer=True, ctx=None) -> AddMemoryOutput`

Store information in long-term memory with semantic indexing.

**Parameters:**
- `messages` (`list[dict[str, str]]`): List of message dicts with 'role' and 'content'
- `user_id` (`str | None`): Optional user identifier for memory scoping
- `agent_id` (`str | None`): Optional agent identifier for memory scoping
- `run_id` (`str | None`): Optional run identifier for memory scoping
- `metadata` (`dict[str, Any] | None`): Optional custom key-value metadata
- `infer` (`bool`): If False, skip LLM inference (default True)
- `ctx` (`Context | None`): FastMCP context for accessing lifespan state

**Returns:**
- `AddMemoryOutput`: List of created memory entries with ids and metadata

**Raises:**
- `ValueError`: E-4 (ERR_400) if messages invalid or no entity ID
- `RuntimeError`: E-2 (ERR_MEM_001) if memory not initialized

## Usage Example

```python
# MCP tool call
result = await ctx.tool.call("add_memory", {
    "messages": [{"role": "user", "content": "I prefer dark mode"}],
    "user_id": "alice",
    "agent_id": "desktop-assistant"
})

# Result structure
# {
#     "results": [
#         {
#             "id": "mem_abc123",
#             "memory": "I prefer dark mode",
#             "metadata": {"user_id": "alice", "agent_id": "desktop-assistant"},
#             "event": "ADD"
#         }
#     ]
# }
```

## Error Handling

| Error | Code | Condition |
|-------|------|-----------|
| E-4 | ERR_400 | Invalid messages or missing entity ID |
| E-2 | ERR_MEM_001 | AsyncMemory not initialized |

## See Also

- [search_memories.py](./tools_search_memories.md) - Search tool
- [memory/manager.py](./memory_manager.md) - MemoryManager class