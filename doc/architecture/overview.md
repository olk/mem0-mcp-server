# Architecture Overview

## System Architecture

The mem0-mcp server is an MCP (Model Context Protocol) server that exposes Mem0 v2 AsyncMemory functionality via MCP tools. It supports stdio and SSE transports for flexible deployment.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent (MCP Client)                          │
│                         (Claude, GPT, other MCP clients)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ MCP JSON-RPC
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          Mem0-MCP Server                                   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        FastMCP Server                               │   │
│  │  ┌────────────┐  ┌───────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │ add_memory │  │search_memories│  │update_memory│  │delete_mem │  │   │
│  │  │   tool     │  │     tool      │  │    tool     │  │    ory    │  │   │
│  │  └──────┬─────┘  └────────┬──────┘  └──────┬──────┘  └─────┬─────┘  │   │
│  │         │                 │                │               │        │   │
│  │  ┌──────┴─────────────────┴────────────────┴───────────────┴─────┐  │   │
│  │  │                      MemoryManager                            │  │   │
│  │  │         (Repository Pattern + Multi-Tenant Isolation)         │  │   │
│  │  └──────┬───────────────────────────────────────────────┬────────┘  │   │
│  └─────────┼───────────────────────────────────────────────┼───────────┘   │
│            │                                               │               │
│  ┌─────────┴───────────────────────────────────────────────┴────────────┐  │
│  │                     Mem0 AsyncMemory                                 │  │
│  │                                                                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │   LLM    │  │ Embedder │  │ Reranker │  │ Vector   │              │  │
│  │  │ (Config) │  │ (Config) │  │ (Config) │  │ Store    │              │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Transport Layer                                │   │
│  │                     (Strategy Pattern)                              │   │
│  │  ┌─────────────────────┐      ┌─────────────────────┐               │   │
│  │  │   stdio Transport   │      │    SSE Transport    │               │   │
│  │  │   (stdin/stdout)    │      │    (HTTP/SSE)       │               │   │
│  │  └─────────────────────┘      └─────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Configuration Layer                            │   │
│  │                    (DP-5: Validation Pattern)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │   Config    │  │   Secrets   │  │  Settings   │                  │   │
│  │  │   Loader    │  │  (Env Var)  │  │  (Pydantic) │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       SafeLogger                                    │   │
│  │              (DP-8: Output Stream Separation)                       │   │
│  │       stdout (MCP JSON-RPC) │ stderr (Library Logs)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              External Services                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Redis    │  │   OpenAI    │  │   Cohere    │  │  Other      │         │
│  │ (Vector DB) │  │   (LLM)     │  │ (Reranker)  │  │  Providers  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### COMP-1: ConfigLoader

Loads and validates configuration from file, environment, and parameter sources.

**Location:** `src/mcp_server/config/`

**Responsibilities:**
- Configuration file loading with tilde expansion
- JSON parsing and validation
- Auto-creation of default config directory
- Parameter precedence resolution

**Dependencies:** None

**Exposes:** Pydantic settings models

### COMP-2: FastMCP Server

MCP protocol server managing transport, tool registration, and request handling.

**Location:** `src/mcp_server/__init__.py`, `src/mcp_server/lifespan.py`, `src/mcp_server/transport.py`

**Responsibilities:**
- Single FastMCP instance management (IC-2)
- Transport selection (stdio vs SSE)
- Lifespan management for resource cleanup
- Graceful shutdown handling

**Dependencies:** ConfigLoader, MemoryManager, SafeLogger

**Exposes:** MCP tools (add_memory, search_memories, etc.)

### COMP-3: Mem0 Memory Manager

Manages Mem0 AsyncMemory lifecycle and provides repository interface for memory operations.

**Location:** `src/mcp_server/memory/manager.py`, `src/mcp_server/memory/lifespan.py`

**Responsibilities:**
- Multi-tenant scope hierarchy (user/agent/session)
- Memory operations: add, search, get, update, delete, list
- Tenant isolation enforcement
- Vector store and embedder configuration

**Dependencies:** ConfigLoader

**Exposes:** MemoryManager, TenantScope

### COMP-4: MCP Tools

MCP tool definitions wrapping Mem0 operations.

**Location:** `src/mcp_server/tools/`

**Tools:**
- `add_memory` - Store information in long-term memory
- `search_memories` - Semantic similarity search
- `get_memory` - Retrieve specific memory by ID
- `update_memory` - Update existing memory
- `delete_memory` - Remove memory
- `list_memories` - List with filtering/pagination

**Dependencies:** MemoryManager

**Exposes:** MCP protocol tools

### COMP-5: SafeLogger

Separates MCP protocol output (stdout) from library logs (stderr).

**Location:** `src/mcp_server/utils/safe_logger.py`

**Responsibilities:**
- MCP message routing to stdout
- Library log routing to stderr
- Logging level configuration

**Dependencies:** None

**Exposes:** SafeLogger class, MCPWriter

## Data Flow

### DF-1: Memory Operations Flow

```
MCP Client → MCP Tool → MemoryManager → Mem0 AsyncMemory → Redis Vector Store
```

1. AI agent calls MCP tool with content/user_id
2. Tool validates input via Pydantic models
3. MemoryManager adds memory with tenant scope
4. Mem0 encodes memory with embeddings
5. Stored in Redis vector store

### DF-2: Semantic Search Flow

```
MCP Client → Search Tool → MemoryManager → Mem0 AsyncMemory → Redis → Results
```

1. AI agent calls search_memories with query
2. Query embedded via configured embedder
3. Vector similarity search in Redis
4. Results ranked and returned with scores

### DF-3: Configuration Loading Flow

```
Config File/ENV → ConfigLoader → Pydantic Validation → Server Settings
```

1. Config loaded from `~/.config/mem0-mcp-server/settings.json`
2. Or from environment variables with MCP_ prefix
3. Pydantic validates all values
4. Settings passed to components via lifespan

### DF-4: Transport Selection Flow

```
Config → FastMCP Server → Transport Strategy → stdio or SSE
```

1. TRANSPORT config determines transport type
2. Strategy pattern selects appropriate transport
3. Server runs with selected transport
4. Health check available on SSE transport

### DF-5: Graceful Shutdown Flow

```
SIGTERM/SIGINT → Lifespan Cleanup → MemoryManager → Redis
```

1. OS signal received
2. Lifespan initiates cleanup
3. MemoryManager closes AsyncMemory
4. Redis connections closed

## Technology Stack

| Component | Technology |
|-----------|------------|
| MCP Server | FastMCP 2.x |
| Memory | Mem0 v2 AsyncMemory |
| Vector Store | Redis (configurable) |
| Embedding | OpenAI (configurable) |
| LLM | OpenAI GPT-4o (configurable) |
| Reranker | Cohere (configurable) |
| Config Validation | Pydantic 2.x |
| Runtime | Python 3.12 |

## Design Patterns

| Pattern | Component | Purpose |
|---------|-----------|---------|
| Singleton | FastMCP Server | Ensure single FastMCP instance |
| Async Context Manager | Lifespan | Manage AsyncMemory lifecycle |
| Repository | MemoryManager | Abstract memory operations |
| Multi-Tenant Isolation | TenantScope | Enforce data isolation |
| Strategy | Transport | Select transport at runtime |
| Output Separation | SafeLogger | Separate stdout/stderr |
| Validation | Pydantic | Validate configuration |

## See Also

- [Components](../architecture/components.md) - Detailed component interactions
- [Pattern Guides](../patterns/README.md) - Design pattern documentation
- [API Reference](../api/README.md) - API documentation
