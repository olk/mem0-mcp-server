# Configuration Settings (`mcp_server/config/settings.py`)

## Overview

Pydantic configuration models and validation. Implements Configuration Validation Pattern (DP-5) with explicit error messages.

## Error Classes

### `ValidationSettingsError`

E-15 (ERR_VAL_001): Configuration value failed Pydantic validation.

**Attributes:**
- `field_name` (`str`): Name of the field that failed
- `invalid_value` (`Any`): The value that failed
- `expected_format` (`str`): Description of expected format

### `SettingsError`

E-14 (ERR_SEC_001): Required API key not found in environment variables.

**Attributes:**
- `secret_name` (`str`): Name of the missing environment variable

## Configuration Models

### `SecretsSettings`

Secrets settings loaded from environment variables only.

**Attributes:**
- `OPENAI_API_KEY` (`str | None`): OpenAI API key (required)
- `COHERE_API_KEY` (`str | None`): Cohere API key for reranker
- `HUGGINGFACE_API_KEY` (`str | None`): HuggingFace API key for reranker
- `ZERO_ENTROPY_API_KEY` (`str | None`): Zero Entropy API key for reranker

**Validation:**
- `OPENAI_API_KEY` must be present and non-empty

### `VectorStoreConfig`

Vector store configuration for memory embeddings.

**Attributes:**
- `provider` (`str`, default="redis"): Vector store provider
- `collection_name` (`str`, default="mem0"): Collection/index name
- `embedding_model_dims` (`int`, default=1536): Embedding dimension
- Provider-specific config fields (redis_url, qdrant_host, chroma_path, etc.)

**Supported Providers:**
- redis, qdrant, chroma, milvus, faiss, pgvector, pinecone, mongodb, weaviate, opensearch, elasticsearch, upstash_vector, supabase, azure_ai_search, valkey, s3_vectors

**Methods:**
- `to_mem0_vector_store_config() -> dict`: Convert to Mem0 format

### `LLMConfig`

LLM provider configuration for mem0.

**Attributes:**
- `provider` (`str`, default="openai"): LLM provider
- `model` (`str`, default="gpt-4o"): Model name
- `temperature` (`float`, default=0.2): Temperature (0-2)
- `max_tokens` (`int`, default=2000): Maximum tokens
- `top_p` (`float | None`): Nucleus sampling
- `top_k` (`int | None`): Top-k sampling
- Provider-specific config fields (openai_base_url, anthropic_base_url, etc.)

**Supported Providers:**
- openai, anthropic, azure_openai, gemini, groq, ollama, together, aws_bedrock, deepseek, minimax, xai, sarvam, lmstudio, vllm, litellm, huggingface

**Methods:**
- `to_mem0_llm_config() -> dict`: Convert to Mem0 format

### `EmbedderConfig`

Embedder configuration for text embeddings.

**Attributes:**
- `provider` (`str`, default="openai"): Embedder provider
- `model` (`str`, default="text-embedding-3-small"): Embedding model
- `dimension` (`int`, default=1536): Embedding dimension
- Provider-specific config fields

**Supported Providers:**
- openai, ollama, huggingface, azure_openai, gemini, vertexai, together, lmstudio, langchain, aws_bedrock, fastembed

**Methods:**
- `to_mem0_embedder_config() -> dict`: Convert to Mem0 format

### `RerankerConfig`

Reranker configuration for reordering vector search results.

**Attributes:**
- `provider` (`str`, default="cohere"): Reranker provider
- `top_k` (`int`, default=10): Maximum results after reranking
- `enabled` (`bool`, default=True): Whether reranking is enabled
- `model` (`str | None`): Reranker model name
- `api_key` (`str | None`): API key for hosted rerankers
- Provider-specific config fields

**Supported Providers:**
- cohere, sentence_transformer, huggingface, llm_reranker, zero_entropy

**Methods:**
- `to_mem0_reranker_config() -> dict`: Convert to Mem0 format

### `ServerSettings`

Server configuration settings with validation.

**Attributes:**
- `config_id` (`str`, default="default"): Unique identifier
- `memory_expiry` (`int`, default=3600): Memory TTL in seconds (min 60)
- `logging_level` (`str`, default="INFO"): Logging level
- `host` (`str`, default="0.0.0.0"): Server host address
- `port` (`int`, default=8080): Server port (1-65535)
- `transport` (`str`, default="sse"): Transport type (stdio, sse)
- `vector_store` (`VectorStoreConfig`): Vector store configuration
- `llm` (`LLMConfig`): LLM configuration
- `embedder` (`EmbedderConfig`): Embedder configuration
- `reranker` (`RerankerConfig | None`): Reranker configuration
- `created_at` (`str`): Configuration timestamp

**Validators:**
- `logging_level`: Must be DEBUG, INFO, WARNING, ERROR, or CRITICAL
- `transport`: Must be stdio or sse
- `port`: Must be between 1 and 65535
- `memory_expiry`: Must be at least 60 seconds
- `host`: Must be valid hostname or IP address

### `Settings`

MCP Server configuration with parameter precedence resolution.

**Parameter Precedence (highest to lowest):**
1. Tool parameters (direct initialization)
2. Environment variables (with MCP_ prefix)
3. Config file values
4. Hardcoded defaults

**Attributes:**
- `config_id`, `memory_expiry`, `logging_level`, `host`, `port`, `transport`
- `vector_store`, `llm`, `embedder` (as dicts)
- `user_id`, `agent_id`, `app_id` (with defaults)

**Methods:**
- `get_precedence_chain() -> list[str]`: Returns precedence chain
- `is_precedence_respected(**overrides) -> bool`: Validates precedence

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_USER_ID` | `"default_user"` | Default user ID |
| `DEFAULT_AGENT_ID` | `"default_agent"` | Default agent ID |
| `DEFAULT_APP_ID` | `"default_app"` | Default app/project ID |

## Usage Example

```python
from mcp_server.config.settings import (
    Settings, get_settings, create_settings,
    VectorStoreConfig, LLMConfig, EmbedderConfig
)

# Get global settings
settings = get_settings()

# Create with overrides
settings = create_settings(
    host="127.0.0.1",
    port=9000,
    transport="stdio"
)

# Vector store config
vs_config = VectorStoreConfig(
    provider="redis",
    redis_url="redis://localhost:6379"
)

# LLM config
llm_config = LLMConfig(
    provider="openai",
    model="gpt-4o",
    temperature=0.3
)
```

## See Also

- [loader.py](./config_loader.md) - Configuration file loading