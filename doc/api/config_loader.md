# Configuration Loader (`mcp_server/config/loader.py`)

## Overview

Configuration file loader with tilde expansion and auto-creation. Supports loading from `~/.config/mem0-mcp-server/settings.json` with JSON parsing.

## Error Classes

### `ConfigFileNotFoundError`

Raised when configuration file is not found at expected path. E-12 (ERR_CONFIG_001).

**Attributes:**
- `path` (`Path`): The path where config was expected
- `error_code` (`str`): "ERR_CONFIG_001"
- `message` (`str`): Human-readable error message

### `ConfigDirectoryCreationError`

Raised when config directory cannot be created. E-13 (ERR_CONFIG_002).

**Attributes:**
- `path` (`Path`): The path that failed creation
- `reason` (`str`): Reason for failure
- `error_code` (`str`): "ERR_CONFIG_002"
- `message` (`str`): Human-readable error message

## Functions

### `get_default_config_path() -> Path`

Get the default configuration file path with tilde expansion.

**Returns:**
- `Path`: Path to `~/.config/mem0-mcp-server/settings.json`

**Usage:**

```python
from mcp_server.config.loader import get_default_config_path

config_path = get_default_config_path()
# Path('~/.config/mem0-mcp-server/settings.json')
```

### `load_config(config_path: str | Path | None = None) -> dict[str, Any]`

Load configuration from JSON file with tilde expansion.

**Parameters:**
- `config_path` (`str | Path | None`): Optional custom path. Defaults to `~/.config/mem0-mcp-server/settings.json`

**Returns:**
- `dict[str, Any]`: Parsed configuration dictionary

**Raises:**
- `ConfigFileNotFoundError`: When config file doesn't exist (E-12)
- `ValueError`: If config path contains ".." traversal
- `json.JSONDecodeError`: If file is not valid JSON

**Usage:**

```python
from mcp_server.config.loader import load_config

# Load from default path
config = load_config()

# Load from custom path
config = load_config("/path/to/config.json")
```

### `create_default_config() -> dict[str, Any]`

Create default configuration values.

**Returns:**
- `dict[str, Any]`: Default configuration compliant with mem0-config format

**Default Values:**
```python
{
    "vector_store": {
        "provider": "redis",
        "config": {
            "collection_name": "mem0",
            "embedding_model_dims": 1536,
            "redis_url": "redis://localhost:6379"
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.2,
            "max_tokens": 2000
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "embedding_dims": 1536
        }
    },
    "reranker": {
        "provider": "cohere",
        "config": {
            "model": "rerank-english-v3.0",
            "top_k": 10
        }
    }
}
```

### `load_settings(config_path: str | Path | None = None) -> ServerSettings`

Load and validate configuration as Pydantic settings.

**Parameters:**
- `config_path` (`str | Path | None`): Optional custom path

**Returns:**
- `ServerSettings`: Validated ServerSettings instance

**Raises:**
- `ConfigFileNotFoundError`: When config file doesn't exist

**Usage:**

```python
from mcp_server.config.loader import load_settings

settings = load_settings()
print(f"Host: {settings.host}, Port: {settings.port}")
```

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MEMORY_EXPIRY` | `"30 days"` | Default memory TTL |
| `DEFAULT_LOGGING_LEVEL` | `"info"` | Default logging level |

## Error Handling

| Error | Code | Condition |
|-------|------|-----------|
| E-12 | ERR_CONFIG_001 | Configuration file not found |
| E-13 | ERR_CONFIG_002 | Failed to create config directory |

## See Also

- [settings.py](./config_settings.md) - Pydantic configuration models