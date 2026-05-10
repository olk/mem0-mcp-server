# Component Interactions

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent (MCP Client)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  COMP-2: FastMCP Server                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  __init__.py: Singleton FastMCP instance (IC-2)                     │  │
│  │  lifespan.py: Resource lifecycle management (IC-3)                  │  │
│  │  transport.py: Transport strategy selection (IC-4)                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    COMP-1       │    │    COMP-3       │    │    COMP-5       │
│  ConfigLoader   │    │  MemoryManager  │    │   SafeLogger    │
│                 │    │                 │    │                 │
│ - loader.py     │    │ - manager.py    │    │ - safe_logger.py│
│ - settings.py   │    │ - lifespan.py   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │
         │                      │
         └─────────┬────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  COMP-4: MCP Tools                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   add    │ │  search  │ │   get    │ │  update  │ │  delete  │          │
│  │ _memory  │ │_memories │ │ _memory  │ │ _memory  │ │ _memory  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└────────────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### FastMCP Server → ConfigLoader

**Interaction:** Server initializes ConfigLoader to get settings

```python
# In lifespan.py
settings = getattr(server, '_settings', None)  # From ConfigLoader
```

**Flow:**
1. Server startup triggers lifespan
2. ConfigLoader reads from `~/.config/mem0-mcp-server/settings.json`
3. Pydantic validates all configuration values
4. Settings passed to AsyncMemory initialization

### FastMCP Server → MemoryManager

**Interaction:** Server creates MemoryManager via async context manager

```python
# In lifespan.py
async with memory_lifespan(...) as memory_lifespan_result:
    manager = memory_lifespan_result.get("manager")
    server.state.memory = manager
```

**Flow:**
1. Lifespan creates AsyncMemory with config
2. MemoryManager wraps AsyncMemory
3. Manager attached to server state
4. Tools access via context

### MemoryManager → Mem0 AsyncMemory

**Interaction:** MemoryManager delegates to Mem0 AsyncMemory

```python
# In manager.py
result = await self.client.add(
    messages=[{"role": "user", "content": content}],
    user_id=mem0_user_id,
    metadata=memory_metadata
)
```

**Flow:**
1. Tool calls MemoryManager method
2. Manager validates TenantScope
3. Operations delegated to AsyncMemory
4. Results wrapped in MemoryEntry

### MCP Tools → MemoryManager

**Interaction:** Tools use MemoryManager for all operations

```python
# In tools/add_memory.py
memory = ctx.request_context.lifespan_context.get("memory")
result = await memory.add(...)
```

**Flow:**
1. MCP tool receives request
2. Tool validates input with Pydantic
3. Tool gets MemoryManager from context
4. MemoryManager executes operation
5. Results returned to MCP client

### FastMCP Server → SafeLogger

**Interaction:** Server configures SafeLogger for output separation

```python
# In main.py or transport.py
SafeLogger.configure_logging(LoggingLevel.INFO)
```

**Flow:**
1. Server initializes SafeLogger
2. Library logs routed to stderr
3. MCP messages written directly to stdout

### Transport Selection → FastMCP Server

**Interaction:** Transport config determines how server runs

```python
# In transport.py
if transport_type == TransportType.STDIO:
    await _run_stdio_transport(mcp_server)
else:
    await _run_sse_transport(host, port, mcp_server)
```

**Flow:**
1. Transport value read from config
2. Strategy pattern selects transport function
3. Server runs with selected transport
4. Health check registered for SSE

## Function Calls

### Tool Registration Flow

```python
# __init__.py (FastMCP singleton)
mcp = get_mcp_instance()

# tools/add_memory.py
def register_add_memory_tool(mcp):
    @mcp.tool()
    async def add_memory(...):
        pass
    logger.debug("add_memory tool registered")

# main.py
from mcp_server.tools import register_all_tools
register_all_tools(mcp)
```

### Memory Operation Flow

```python
# 1. MCP Client sends request
client.call_tool("add_memory", {...})

# 2. FastMCP routes to tool
@mcp.tool()
async def add_memory(ctx, ...):
    # 3. Get memory from context
    memory = ctx.request_context.lifespan_context.get("memory")

    # 4. Call MemoryManager
    entry = await memory.add_memory(scope, content, metadata)

    # 5. Return result
    return AddMemoryOutput(results=[...])
```

### Search Flow with Reranking

```python
# 1. Search request
result = await memory.search_memories(
    scope=scope,
    query="preferences",
    rerank=True
)

# 2. MemoryManager calls AsyncMemory.search
results = await self.client.search(
    query=query,
    filters={"user_id": mem0_user_id},
    top_k=limit,
    rerank=True
)

# 3. Reranker reorders results (if enabled)
# 4. Results returned with scores
```

## State Management

### Server State

```python
# In lifespan.py
if hasattr(server, 'state'):
    server.state.memory = manager
else:
    server._memory = manager
```

### Context State

```python
# In tools/
lifespan_context = ctx.request_context.lifespan_context
memory = lifespan_context.get("memory")
```

## Error Propagation

```
MCP Client
    │
    ▼ (RuntimeError)
MCP Tool
    │
    ▼ (ScopeValidationError)
MemoryManager
    │
    ▼ (Mem0 Exception)
Mem0 AsyncMemory
    │
    ▼
Vector Store (Redis)
```

## See Also

- [System Overview](./overview.md) - High-level architecture
- [API Reference](../api/README.md) - Component APIs
- [Pattern Guides](../patterns/README.md) - Design patterns
