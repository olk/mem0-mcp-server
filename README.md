# mem0-mcp-server

MCP server exposing Mem0 v2 API for AI agents to store, retrieve, and search long-term memories using semantic search through the standardized MCP protocol.

## Overview

Mem0-MCP Server is a self-hosted MCP (Model Context Protocol) server that bridges AI agents with persistent memory storage. It enables intelligent context retention across conversations and sessions using Mem0's AsyncMemory API.

**Key Features:**
- MCP Protocol Integration - Exposes Mem0 functionality via MCP tools
- Semantic Memory Search - Similarity-based memory retrieval with vector search
- Multi-Tenant Isolation - User/Agent/Session scoped memory isolation
- Flexible Transport - stdio for local agents, SSE for remote connections
- Configuration Management - Pydantic-based validation with environment variable support

## Documentation

| Section | Description |
|---------|-------------|
| [API Reference](./doc/api/) | Complete API documentation for all modules and tools |
| [Pattern Guides](./doc/patterns/) | Design pattern documentation (Singleton, Repository, etc.) |
| [Usage Examples](./doc/examples/) | Getting started and advanced usage guides |
| [Deployment](./doc/deployment/docker-compose.md) | Docker Compose configuration and service details |
| [Architecture](./doc/architecture/) | System architecture and component interactions |

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/your-org/mem0-mcp-server.git
cd mem0-mcp-server
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
      "model": "gpt-4o"
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

### Running the Server

```bash
# SSE Transport (remote connections)
uv run python -m mcp_server.main

# stdio Transport (local AI agents)
export MCP_TRANSPORT=stdio
uv run python -m mcp_server.main
```

### OpenCode Configuration

In `~/config/opencode/opencode.json`


### OpenCode Configuration

In `~/config/opencode/opencode.json`

```json
	"mcp": {
		"mem0": {
			"type": "remote",
			"enabled": true,
			"url": "http://localhost:8050/sse"
		}
    }

```
## MCP Tools

| Tool | Description |
|------|-------------|
| `add_memory` | Store information in long-term memory with semantic indexing |
| `search_memories` | Search memories using semantic similarity |
| `get_memory` | Retrieve specific memory by ID |
| `update_memory` | Update existing memory content |
| `delete_memory` | Remove memory from storage |
| `list_memories` | List memories with filtering and pagination |

## Usage Example

```python
# Add memory
result = await client.call_tool("add_memory", {
    "messages": [{"role": "user", "content": "I prefer dark mode"}],
    "user_id": "alice"
})

# Search memories
result = await client.call_tool("search_memories", {
    "query": "theme preferences",
    "filters": {"user_id": "alice"},
    "limit": 5
})
```

## Architecture

```
AI Agent → FastMCP Server → MemoryManager → Mem0 AsyncMemory → Redis
              │                                  │
              ├── SafeLogger (stdout/stderr)     │
              ├── Transport (stdio/SSE)          │
              └── Config (Pydantic validation)   │
```

**Components:**
- **COMP-1**: ConfigLoader - Configuration loading and validation
- **COMP-2**: FastMCP Server - MCP protocol server
- **COMP-3**: MemoryManager - Memory operations with multi-tenant isolation
- **COMP-4**: MCP Tools - Tool definitions
- **COMP-5**: SafeLogger - Output stream separation

## Configuration

### Parameter Precedence

Configuration values are resolved in order:
1. Tool parameters (direct)
2. Environment variables (with MCP_ prefix)
3. Config file values
4. Hardcoded defaults

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key for LLM |
| `MCP_TRANSPORT` | `sse` | Transport type (stdio, sse) |
| `MCP_HOST` | `0.0.0.0` | Server bind address |
| `MCP_PORT` | `8080` | Server bind port |

## Deployment

### Docker

```bash
# Using docker-compose
docker-compose up -d

# Using Makefile
make docker-up      # Start services with docker compose
make docker-down    # Stop services
make docker-logs    # Show logs
```

**Services:**

| Service | Description |
|---------|-------------|
| `mem0-mcp` | MCP server exposing Mem0 API on port 8050 |
| `ollama-qwen3-embedding` | Ollama with `qwen3-embedding:8b` for vector embeddings (port 11434) |
| `ollama-qwen` | Ollama with `qwen2.5:7b` for chat completions (port 11435) |

See [Deployment → Docker](./doc/deployment/docker-compose.md) for detailed configuration.

### Kubernetes

```bash
# Using Helm chart
helm install mem0-mcp ./charts/mem0-mcp-server
```

## Development

| Command | Description |
|---------|-------------|
| `make install` | Install dependencies with uv |
| `make lint` | Lint code with ruff |
| `make lint-fix` | Auto-fix linting issues |
| `make typecheck` | Type check with pyright |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-coverage` | Run tests with coverage report |
| `make build` | Build Docker image |
| `make run` | Run development server |

Run multiple commands: `make install && make lint && make typecheck && make test`

See [`Makefile`](./Makefile) for all available commands including Docker management (`docker-up`, `docker-down`, `docker-logs`, etc.).

## Project Structure

```
mem0-mcp/
├── src/mcp_server/
│   ├── __init__.py          # FastMCP singleton
│   ├── lifespan.py          # Resource lifecycle
│   ├── transport.py         # Transport selection
│   ├── memory/
│   │   ├── manager.py        # MemoryManager
│   │   └── lifespan.py       # AsyncMemory lifecycle
│   ├── config/
│   │   ├── settings.py       # Pydantic models
│   │   └── loader.py        # Config file loading
│   ├── tools/
│   │   ├── add_memory.py
│   │   ├── search_memories.py
│   │   └── ...
│   └── utils/
│       └── safe_logger.py   # Output separation
├── doc/
│   ├── api/                 # API reference
│   ├── patterns/            # Pattern guides
│   ├── examples/            # Usage examples
│   └── architecture/        # Architecture docs
├── tests/
├── Makefile
├── Dockerfile
└── docker-compose.yml
```

## License

MIT License
