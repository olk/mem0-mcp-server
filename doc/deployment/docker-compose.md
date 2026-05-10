# Docker Compose Deployment

This document describes the Docker Compose configuration for the mem0-mcp server.

## Services Overview

```
┌────────────────────────────────────────────────────────────┐
│                    mem0-network                            │
│                                                            │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│  │  mem0-mcp    │  │ ollama-qwen3-   │  │  ollama-qwen │   │
│  │  :8050       │──│ embedding:11434 │  │  :11435      │   │
│  └──────────────┘  └─────────────────┘  └──────────────┘   │
│                         │                     │            │
│                         └──────────┬──────────┘            │
└────────────────────────────────────────────────────────────┘
```

## mem0-mcp Service

Bridge service exposing Mem0 v2 API via MCP protocol.

**Image:** `mem0-mcp-server:latest`
**Ports:** `8050:8050`
**Runtime:** NVIDIA GPU required

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEFAULT_USER_ID` | `default_user` | Fallback user ID |
| `DEFAULT_AGENT_ID` | `default_agent` | Fallback agent ID |
| `DEFAULT_APP_ID` | `default_app` | Fallback app ID |
| `NVIDIA_VISIBLE_DEVICES` | `all` | GPU allocation |

### Health Check

```bash
curl -f http://localhost:8050/health
```

### Volumes

- `./config:/app/config` - Server configuration
- `./scripts:/scripts` - Startup scripts (e.g., wait-for-ollama.sh)

## Ollama Services

Two separate Ollama instances are used because each is optimized for different context lengths:

| Service | Model | Context | Purpose |
|---------|-------|---------|---------|
| `ollama-qwen3-embedding` | `qwen3-embedding:8b` | 32768 | Vector embeddings for semantic search |
| `ollama-qwen` | `qwen2.5:7b` | 32768 | Chat completions for LLM operations |

### Why Separate Instances?

Mem0 requires distinct endpoints for LLM (chat) and embedder (embeddings). Using separate Ollama instances prevents "requested context size too large" warnings when models share context settings.

### Ports

| Service | External Port | Internal Port |
|---------|---------------|---------------|
| `ollama-qwen3-embedding` | 11434 | 11434 |
| `ollama-qwen` | 11435 | 11434 |

### Health Check

Each Ollama service verifies availability via TCP socket check:

```bash
bash -c '{ printf "GET / HTTP/1.0\r\n\r\n"; cat } < /dev/tcp/localhost/11434 | grep -q "Ollama is running"
```

## Startup Behavior

The `mem0-mcp` service uses an entrypoint script (`/scripts/wait-for-ollama.sh`) that blocks startup until both Ollama services report healthy. This ensures embeddings and chat models are available before the MCP server starts accepting requests.

## Quick Start

```bash
docker-compose up -d
```

This will:
1. Start both Ollama services
2. Pull the specified models on first run
3. Wait for services to be healthy
4. Start the mem0-mcp server

Check status:

```bash
docker-compose ps
docker-compose logs -f mem0-mcp
```

## GPU Configuration

All services require NVIDIA GPU support. Ensure:

1. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) is installed
2. [NVIDIA Docker runtime](https://github.com/NVIDIA/nvidia-docker) is configured
3. `nvidia-smi` works inside containers

## Networking

All services communicate over the `mem0-network` bridge network, allowing:
- mem0-mcp → ollama-qwen3-embedding (embedding requests)
- mem0-mcp → ollama-qwen (chat completions)
