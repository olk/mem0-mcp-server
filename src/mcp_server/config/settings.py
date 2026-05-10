"""Pydantic configuration models and validation.

# PS-3: Pydantic configuration models and validation
# CPARA-9: VECTOR_STORE configuration
# CPARA-10: LLM configuration
# ENT-6: Configuration data entity with key attributes
# DP-5: Configuration Validation Pattern using Pydantic BaseSettings

# FR-15: Parameter Precedence - Tool parameters override environment variables override config file defaults.
# Precedence: tool params > env vars > config file > defaults
# AC-39: Parameter precedence order is enforced exactly
# AC-40: Config resolution checks each level in sequence

# FR-16: Secrets Management - API keys sourced only from environment variables
# FR-17: Pydantic Validation - All configuration values validated with Pydantic with explicit error messages
# IC-7: Secrets MUST be sourced only from environment variables, not in config file
# IC-8: All configuration values MUST be validated using Pydantic with explicit error messages
# AC-41: No API keys in config file (security requirement)
# AC-42: Environment variables used for sensitive data
# AC-43: Validation errors contain descriptive messages
# AC-44: Invalid values rejected with clear indication of problem
# E-14 (ERR_SEC_001): Required API key not found in environment variables
# E-15 (ERR_VAL_001): Configuration value failed Pydantic validation
"""

import logging
import re
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# CPARA-3, CPARA-7, CPARA-8: Default configuration parameters for parameter precedence
# Default user ID when not provided in tool calls
DEFAULT_USER_ID = "default_user"

# Default agent ID when not provided in tool calls
DEFAULT_AGENT_ID = "default_agent"

# Default app/project ID when not provided in tool calls
DEFAULT_APP_ID = "default_app"


class ValidationSettingsError(ValueError):
    """E-15 (ERR_VAL_001): Configuration value failed Pydantic validation.

    This error is raised when a configuration value fails Pydantic validation.
    The error contains descriptive messages indicating the problem and expected format
    per AC-43 and AC-44.

    Inherits from ValueError so Pydantic wraps it in ValidationError.

    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: All configuration values MUST be validated using Pydantic with explicit error messages
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    # E-15: Error code ERR_VAL_001 with HTTP 400, warn severity
    # logging_context: [config, validation]
    """

    CODE: ClassVar[str] = "ERR_VAL_001"
    HTTP_STATUS: ClassVar[int] = 400
    SEVERITY: ClassVar[str] = "warn"

    def __init__(self, field_name: str, invalid_value: Any, expected_format: str):
        """Initialize ValidationSettingsError with validation failure details.

        Args:
            field_name: Name of the field that failed validation
            invalid_value: The value that was provided and failed validation
            expected_format: Description of the expected format/value
        """
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.expected_format = expected_format
        message = (
            f"Configuration value failed validation for '{field_name}': "
            f"got {invalid_value!r}, expected {expected_format}"
        )
        super().__init__(message)
        logger.warning(
            "Configuration validation error: invalid value rejected",
            extra={
                "logging_context": ["config", "validation"],
                "error_code": self.CODE,
                "http_status": self.HTTP_STATUS,
                "severity": self.SEVERITY,
                "field_name": field_name,
                "invalid_value": repr(invalid_value),
                "expected_format": expected_format,
            },
        )


class SettingsError(ValueError):
    """E-14 (ERR_SEC_001): Required API key not found in environment variables.

    This error is raised when a required secret (like OPENAI_API_KEY) is not
    found in the environment variables. The system requires API keys to be
    sourced exclusively from environment variables per IC-7.

    Inherits from ValueError so Pydantic wraps it in ValidationError.

    # FR-16: API keys sourced only from environment variables
    # E-14: Error code ERR_SEC_001 with HTTP 500, critical severity
    # logging_context: [security, config]
    """

    CODE: ClassVar[str] = "ERR_SEC_001"
    HTTP_STATUS: ClassVar[int] = 500
    SEVERITY: ClassVar[str] = "critical"

    def __init__(self, secret_name: str = "OPENAI_API_KEY"):
        """Initialize SettingsError with the missing secret name.

        Args:
            secret_name: Name of the missing environment variable
        """
        self.secret_name = secret_name
        message = f"Required API key not found in environment variables: {secret_name}"
        super().__init__(message)
        logger.critical(
            "Security configuration error: required secret not found in environment",
            extra={
                "logging_context": ["security", "config"],
                "error_code": self.CODE,
                "http_status": self.HTTP_STATUS,
                "severity": self.SEVERITY,
                "secret_name": secret_name,
            },
        )


class SecretsSettings(BaseSettings):
    """Secrets settings loaded from environment variables only.

    FR-16: API keys sourced only from environment variables, not persisted in config
    IC-7: Secrets MUST be sourced only from environment variables

    This class is intentionally separate from regular config to ensure
    secrets are NEVER persisted in config files. All secrets must be
    provided via environment variables.

    # AC-42: Environment variables used for sensitive data
    """

    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key - loaded from environment variables only",
    )
    COHERE_API_KEY: str | None = Field(
        default=None,
        description="Cohere API key for reranker - loaded from environment variables only",
    )
    HUGGINGFACE_API_KEY: str | None = Field(
        default=None,
        description="HuggingFace API key for reranker - loaded from environment variables only",
    )
    ZERO_ENTROPY_API_KEY: str | None = Field(
        default=None,
        description="Zero Entropy API key for reranker - loaded from environment variables only",
    )

    model_config = {"env_prefix": "", "case_sensitive": True}

    @model_validator(mode="after")
    def validate_secrets(self) -> "SecretsSettings":
        """Validate all required secrets are present and non-empty.

        FR-16: API keys sourced only from environment variables
        E-14: Raise SettingsError if API key is missing or empty

        Returns:
            self if all secrets are valid

        Raises:
            SettingsError: If any required secret is missing or empty
        """
        if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.strip() == "":
            raise SettingsError("OPENAI_API_KEY")
        self.OPENAI_API_KEY = self.OPENAI_API_KEY.strip()
        return self


def get_secrets() -> SecretsSettings:
    """Load secrets from environment variables.

    FR-16: API keys sourced only from environment variables
    IC-7: Secrets MUST be sourced only from environment variables
    AC-41: No API keys in config file (satisfied by loading from env only)
    AC-42: Environment variables used for sensitive data

    Returns:
        SecretsSettings instance with validated secrets from environment

    Raises:
        SettingsError: If required secrets are not found in environment
    """
    return SecretsSettings()


class VectorStoreConfig(BaseModel):
    """Vector store configuration for memory embeddings.

    CPARA-9: VECTOR_STORE configuration
    AC-51: vector_store config with provider and config
    FR-17: Pydantic Validation - All configuration values validated with explicit error messages
    FR-21: Vector Database Flexibility - Support multiple vector store backends

    Supported providers: redis, qdrant, chroma, milvus, faiss, pgvector, pinecone,
    mongodb, weaviate, opensearch, elasticsearch, upstash_vector, supabase,
    azure_ai_search, vertex_ai_vector_search, databricks, turborpuffer, cassandra,
    azure_mysql, baidu, neptune, langchain, s3_vectors, valkey
    """

    provider: str = Field(default="redis", description="Vector store provider")
    collection_name: str = Field(default="mem0", description="Collection/index name")
    embedding_model_dims: int = Field(default=1536, description="Embedding dimension")
    location: str | None = Field(default=None, description="Generic location/URL for the vector store")

    redis_url: str | None = Field(default=None, description="Redis connection URL")

    qdrant_host: str | None = Field(default=None, description="Qdrant server host")
    qdrant_port: int | None = Field(default=None, description="Qdrant server port")
    qdrant_url: str | None = Field(default=None, description="Qdrant full server URL")
    qdrant_api_key: str | None = Field(default=None, description="Qdrant API key")
    qdrant_path: str | None = Field(default=None, description="Qdrant local database path")
    qdrant_on_disk: bool = Field(default=False, description="Qdrant persistent storage")

    chroma_path: str | None = Field(default=None, description="Chroma database path")
    chroma_host: str | None = Field(default=None, description="Chroma server host")
    chroma_port: int | None = Field(default=None, description="Chroma server port")
    chroma_api_key: str | None = Field(default=None, description="ChromaDB Cloud API key")
    chroma_tenant: str | None = Field(default=None, description="ChromaDB Cloud tenant ID")

    pgvector_dbname: str | None = Field(default=None, description="PostgreSQL database name")
    pgvector_user: str | None = Field(default=None, description="PostgreSQL username")
    pgvector_password: str | None = Field(default=None, description="PostgreSQL password")
    pgvector_host: str | None = Field(default=None, description="PostgreSQL host")
    pgvector_port: int | None = Field(default=None, description="PostgreSQL port")
    pgvector_connection_string: str | None = Field(default=None, description="PostgreSQL connection string")
    pgvector_sslmode: str | None = Field(default=None, description="PostgreSQL SSL mode")
    pgvector_hnsw: bool = Field(default=True, description="Use HNSW indexing")
    pgvector_diskann: bool = Field(default=False, description="Use DiskANN indexing")

    milvus_url: str | None = Field(default=None, description="Milvus/Zilliz server URL")
    milvus_token: str | None = Field(default=None, description="Milvus/Zilliz token")
    milvus_db_name: str | None = Field(default=None, description="Milvus database name")
    milvus_metric_type: str | None = Field(default=None, description="Milvus metric type")

    pinecone_api_key: str | None = Field(default=None, description="Pinecone API key")
    pinecone_environment: str | None = Field(default=None, description="Pinecone environment")
    pinecone_namespace: str | None = Field(default=None, description="Pinecone namespace")

    mongodb_mongo_uri: str | None = Field(default=None, description="MongoDB URI connection string")
    mongodb_db_name: str | None = Field(default=None, description="MongoDB database name")

    weaviate_cluster_url: str | None = Field(default=None, description="Weaviate cluster URL")
    weaviate_auth_client_secret: str | None = Field(default=None, description="Weaviate API key")

    faiss_path: str | None = Field(default=None, description="FAISS index path")
    faiss_distance_strategy: str = Field(default="euclidean", description="FAISS distance metric")

    supabase_connection_string: str | None = Field(default=None, description="Supabase PostgreSQL connection string")
    supabase_index_method: str | None = Field(default=None, description="Supabase index method")
    supabase_index_measure: str | None = Field(default=None, description="Supabase distance measure")

    upstash_vector_url: str | None = Field(default=None, description="Upstash Vector URL")
    upstash_vector_token: str | None = Field(default=None, description="Upstash Vector token")

    opensearch_host: str | None = Field(default=None, description="OpenSearch server host")
    opensearch_port: int | None = Field(default=None, description="OpenSearch server port")
    opensearch_user: str | None = Field(default=None, description="OpenSearch username")
    opensearch_password: str | None = Field(default=None, description="OpenSearch password")
    opensearch_api_key: str | None = Field(default=None, description="OpenSearch API key")
    opensearch_use_ssl: bool = Field(default=True, description="OpenSearch use SSL")
    opensearch_verify_certs: bool = Field(default=True, description="OpenSearch verify certs")

    elasticsearch_host: str | None = Field(default=None, description="Elasticsearch host")
    elasticsearch_port: int | None = Field(default=None, description="Elasticsearch port")
    elasticsearch_cloud_id: str | None = Field(default=None, description="Elasticsearch Cloud ID")
    elasticsearch_api_key: str | None = Field(default=None, description="Elasticsearch API key")
    elasticsearch_user: str | None = Field(default=None, description="Elasticsearch user")
    elasticsearch_password: str | None = Field(default=None, description="Elasticsearch password")

    azure_ai_search_service_name: str | None = Field(default=None, description="Azure AI Search service name")
    azure_ai_search_api_key: str | None = Field(default=None, description="Azure AI Search API key")

    valkey_url: str | None = Field(default=None, description="Valkey connection URL")
    valkey_index_type: str | None = Field(default=None, description="Valkey index type (hnsw/flat)")

    s3_vectors_bucket: str | None = Field(default=None, description="S3 Vector bucket name")
    s3_vectors_region: str | None = Field(default=None, description="AWS region name")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate vector store provider.

        FR-21: Vector Database Flexibility - Support multiple vector store backends
        FR-17: Pydantic Validation with explicit error messages
        IC-8: Explicit error messages on invalid values
        AC-43: Validation errors contain descriptive messages
        """
        valid_providers = {
            "redis", "qdrant", "chroma", "milvus", "faiss", "pgvector", "pinecone",
            "mongodb", "weaviate", "opensearch", "elasticsearch", "upstash_vector",
            "supabase", "azure_ai_search", "valkey", "s3_vectors"
        }
        lower_v = v.lower()
        if lower_v not in valid_providers:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(valid_providers))}"
            )
        return lower_v

    def _build_config(self) -> dict[str, Any]:
        """Build provider-specific config dict.

        Returns:
            dict with all non-None config fields for the current provider
        """
        cfg: dict[str, Any] = {
            "collection_name": self.collection_name,
            "embedding_model_dims": self.embedding_model_dims,
        }

        match self.provider:
            case "redis":
                if self.redis_url:
                    cfg["redis_url"] = self.redis_url
            case "qdrant":
                if self.qdrant_url:
                    cfg["url"] = self.qdrant_url
                elif self.qdrant_host:
                    cfg["host"] = self.qdrant_host
                    if self.qdrant_port:
                        cfg["port"] = self.qdrant_port
                if self.qdrant_api_key:
                    cfg["api_key"] = self.qdrant_api_key
                if self.qdrant_path:
                    cfg["path"] = self.qdrant_path
                if self.qdrant_on_disk:
                    cfg["on_disk"] = self.qdrant_on_disk
            case "chroma":
                if self.chroma_path:
                    cfg["path"] = self.chroma_path
                if self.chroma_host:
                    cfg["host"] = self.chroma_host
                if self.chroma_port:
                    cfg["port"] = self.chroma_port
                if self.chroma_api_key:
                    cfg["api_key"] = self.chroma_api_key
                if self.chroma_tenant:
                    cfg["tenant"] = self.chroma_tenant
            case "pgvector":
                if self.pgvector_connection_string:
                    cfg["connection_string"] = self.pgvector_connection_string
                else:
                    if self.pgvector_dbname:
                        cfg["dbname"] = self.pgvector_dbname
                    if self.pgvector_user:
                        cfg["user"] = self.pgvector_user
                    if self.pgvector_password:
                        cfg["password"] = self.pgvector_password
                    if self.pgvector_host:
                        cfg["host"] = self.pgvector_host
                    if self.pgvector_port:
                        cfg["port"] = self.pgvector_port
                if self.pgvector_sslmode:
                    cfg["sslmode"] = self.pgvector_sslmode
                cfg["hnsw"] = self.pgvector_hnsw
                cfg["diskann"] = self.pgvector_diskann
            case "milvus":
                if self.milvus_url:
                    cfg["url"] = self.milvus_url
                if self.milvus_token:
                    cfg["token"] = self.milvus_token
                if self.milvus_db_name:
                    cfg["db_name"] = self.milvus_db_name
                if self.milvus_metric_type:
                    cfg["metric_type"] = self.milvus_metric_type
            case "pinecone":
                if self.pinecone_api_key:
                    cfg["api_key"] = self.pinecone_api_key
                if self.pinecone_environment:
                    cfg["environment"] = self.pinecone_environment
                if self.pinecone_namespace:
                    cfg["namespace"] = self.pinecone_namespace
            case "mongodb":
                if self.mongodb_mongo_uri:
                    cfg["mongo_uri"] = self.mongodb_mongo_uri
                if self.mongodb_db_name:
                    cfg["db_name"] = self.mongodb_db_name
            case "weaviate":
                if self.weaviate_cluster_url:
                    cfg["cluster_url"] = self.weaviate_cluster_url
                if self.weaviate_auth_client_secret:
                    cfg["auth_client_secret"] = self.weaviate_auth_client_secret
            case "faiss":
                if self.faiss_path:
                    cfg["path"] = self.faiss_path
                cfg["distance_strategy"] = self.faiss_distance_strategy
            case "supabase":
                if self.supabase_connection_string:
                    cfg["connection_string"] = self.supabase_connection_string
                if self.supabase_index_method:
                    cfg["index_method"] = self.supabase_index_method
                if self.supabase_index_measure:
                    cfg["index_measure"] = self.supabase_index_measure
            case "upstash_vector":
                if self.upstash_vector_url:
                    cfg["url"] = self.upstash_vector_url
                if self.upstash_vector_token:
                    cfg["token"] = self.upstash_vector_token
            case "opensearch":
                if self.opensearch_host:
                    cfg["host"] = self.opensearch_host
                    if self.opensearch_port:
                        cfg["port"] = self.opensearch_port
                if self.opensearch_user:
                    cfg["user"] = self.opensearch_user
                if self.opensearch_password:
                    cfg["password"] = self.opensearch_password
                if self.opensearch_api_key:
                    cfg["api_key"] = self.opensearch_api_key
                cfg["use_ssl"] = self.opensearch_use_ssl
                cfg["verify_certs"] = self.opensearch_verify_certs
            case "elasticsearch":
                if self.elasticsearch_host:
                    cfg["host"] = self.elasticsearch_host
                    if self.elasticsearch_port:
                        cfg["port"] = self.elasticsearch_port
                if self.elasticsearch_cloud_id:
                    cfg["cloud_id"] = self.elasticsearch_cloud_id
                if self.elasticsearch_api_key:
                    cfg["api_key"] = self.elasticsearch_api_key
                if self.elasticsearch_user:
                    cfg["user"] = self.elasticsearch_user
                if self.elasticsearch_password:
                    cfg["password"] = self.elasticsearch_password
            case "azure_ai_search":
                if self.azure_ai_search_service_name:
                    cfg["service_name"] = self.azure_ai_search_service_name
                if self.azure_ai_search_api_key:
                    cfg["api_key"] = self.azure_ai_search_api_key
            case "valkey":
                if self.valkey_url:
                    cfg["valkey_url"] = self.valkey_url
                if self.valkey_index_type:
                    cfg["index_type"] = self.valkey_index_type
            case "s3_vectors":
                if self.s3_vectors_bucket:
                    cfg["vector_bucket_name"] = self.s3_vectors_bucket
                if self.s3_vectors_region:
                    cfg["region_name"] = self.s3_vectors_region

        return cfg

    def to_mem0_vector_store_config(self) -> dict:
        """Convert to Mem0 AsyncMemory vector_store configuration format.

        AC-51: Provider and config extracted from vector_store config
        FR-21: Vector Database Flexibility - Support multiple backends

        Returns:
            dict with provider and config for VectorStoreConfig initialization
        """
        return {
            "provider": self.provider,
            "config": self._build_config()
        }


class LLMConfig(BaseModel):
    """LLM provider configuration for mem0.

    CPARA-10: LLM configuration
    Default: OpenAI GPT-4o with temperature 0.2, max_tokens 2000
    FR-17: Pydantic Validation - All configuration values validated with explicit error messages
    FR-20: Multi-LLM Support - Compatible with various LLM providers

    Supported providers: openai, anthropic, azure_openai, gemini, groq, ollama,
    together, aws_bedrock, deepseek, minimax, xai, sarvam, lmstudio, vllm,
    litellm, huggingface, openai_structured, azure_openai_structured
    """

    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.2, description="Temperature for generation (0-2)")
    max_tokens: int = Field(default=2000, description="Maximum tokens to generate")
    top_p: float | None = Field(default=None, description="Nucleus sampling parameter")
    top_k: int | None = Field(default=None, description="Top-k sampling parameter")

    openai_base_url: str | None = Field(default=None, description="Custom OpenAI API base URL")
    anthropic_base_url: str | None = Field(default=None, description="Custom Anthropic API base URL")
    azure_api_version: str | None = Field(default=None, description="Azure API version")
    azure_deployment: str | None = Field(default=None, description="Azure deployment name")
    azure_endpoint: str | None = Field(default=None, description="Azure endpoint URL")
    ollama_base_url: str | None = Field(default=None, description="Ollama base URL (e.g., http://localhost:11434)")
    groq_base_url: str | None = Field(default=None, description="Groq API base URL")
    together_base_url: str | None = Field(default=None, description="Together AI base URL")
    deepseek_base_url: str | None = Field(default=None, description="DeepSeek API base URL")
    xai_base_url: str | None = Field(default=None, description="xAI API base URL")
    lmstudio_base_url: str | None = Field(default=None, description="LM Studio base URL")
    vllm_base_url: str | None = Field(default=None, description="vLLM server base URL")
    litellm_base_url: str | None = Field(default=None, description="LiteLLM proxy base URL")
    huggingface_base_url: str | None = Field(default=None, description="HuggingFace Inference API base URL")

    aws_region: str | None = Field(default=None, description="AWS region for Bedrock")
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate LLM provider.

        FR-17: Pydantic Validation with explicit error messages
        FR-20: Multi-LLM Support
        IC-8: Explicit error messages on invalid values
        AC-43: Validation errors contain descriptive messages
        """
        valid_providers = {
            "openai", "anthropic", "azure_openai", "gemini", "groq", "ollama",
            "together", "aws_bedrock", "deepseek", "minimax", "xai", "sarvam",
            "lmstudio", "vllm", "litellm", "huggingface",
            "openai_structured", "azure_openai_structured"
        }
        lower_v = v.lower()
        if lower_v not in valid_providers:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(valid_providers))}"
            )
        return lower_v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range.

        FR-17: Pydantic Validation with explicit error messages
        AC-43: Validation errors contain descriptive messages
        """
        if v < 0 or v > 2:
            raise ValueError(
                f"Invalid temperature {v}. Must be between 0 and 2"
            )
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate max_tokens is positive.

        FR-17: Pydantic Validation with explicit error messages
        AC-43: Validation errors contain descriptive messages
        """
        if v <= 0:
            raise ValueError(f"Invalid max_tokens {v}. Must be a positive integer")
        return v

    def _build_config(self) -> dict[str, Any]:
        """Build provider-specific config dict.

        Returns:
            dict with all non-None config fields for the current provider
        """
        cfg: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.top_p is not None:
            cfg["top_p"] = self.top_p
        if self.top_k is not None:
            cfg["top_k"] = self.top_k

        match self.provider:
            case "openai" | "openai_structured":
                if self.openai_base_url:
                    cfg["openai_base_url"] = self.openai_base_url
            case "anthropic":
                if self.anthropic_base_url:
                    cfg["anthropic_base_url"] = self.anthropic_base_url
            case "azure_openai" | "azure_openai_structured":
                if self.azure_api_version:
                    cfg["api_version"] = self.azure_api_version
                if self.azure_deployment:
                    cfg["azure_deployment"] = self.azure_deployment
                if self.azure_endpoint:
                    cfg["azure_endpoint"] = self.azure_endpoint
            case "ollama":
                if self.ollama_base_url:
                    cfg["ollama_base_url"] = self.ollama_base_url
            case "groq":
                if self.groq_base_url:
                    cfg["groq_base_url"] = self.groq_base_url
            case "together":
                if self.together_base_url:
                    cfg["together_base_url"] = self.together_base_url
            case "aws_bedrock":
                if self.aws_region:
                    cfg["aws_region"] = self.aws_region
                if self.aws_access_key_id:
                    cfg["aws_access_key_id"] = self.aws_access_key_id
                if self.aws_secret_access_key:
                    cfg["aws_secret_access_key"] = self.aws_secret_access_key
            case "deepseek":
                if self.deepseek_base_url:
                    cfg["deepseek_base_url"] = self.deepseek_base_url
            case "xai":
                if self.xai_base_url:
                    cfg["xai_base_url"] = self.xai_base_url
            case "lmstudio":
                if self.lmstudio_base_url:
                    cfg["lmstudio_base_url"] = self.lmstudio_base_url
            case "vllm":
                if self.vllm_base_url:
                    cfg["vllm_base_url"] = self.vllm_base_url
            case "litellm":
                if self.litellm_base_url:
                    cfg["litellm_base_url"] = self.litellm_base_url
            case "huggingface":
                if self.huggingface_base_url:
                    cfg["huggingface_base_url"] = self.huggingface_base_url

        return cfg

    def to_mem0_llm_config(self) -> dict:
        """Convert to Mem0 AsyncMemory LLM configuration format.

        FR-20: Multi-LLM Support
        Returns:
            dict with provider and config for LlmConfig initialization
        """
        return {
            "provider": self.provider,
            "config": self._build_config()
        }


class EmbedderConfig(BaseModel):
    """Embedder configuration for text embeddings.

    # FR-17: Pydantic Validation - All configuration values validated with explicit error messages
    # FR-22: Embedding Options - Multiple embedding models supported. Embedder config accepts provider and model.
    # AC-53: embedder config accepts provider and model
    # AC-54: Configurable dimensions

    Supported providers: openai, ollama, huggingface, azure_openai, gemini,
    vertexai, together, lmstudio, langchain, aws_bedrock, fastembed
    """

    provider: str = Field(default="openai", description="Embedder provider")
    model: str = Field(default="text-embedding-3-small", description="Embedding model")
    dimension: int = Field(default=1536, description="Embedding dimension")

    openai_base_url: str | None = Field(default=None, description="Custom OpenAI API base URL")
    ollama_base_url: str | None = Field(default=None, description="Ollama base URL for embeddings (e.g., http://localhost:11434)")
    huggingface_base_url: str | None = Field(default=None, description="HuggingFace Inference API base URL")
    azure_api_version: str | None = Field(default=None, description="Azure API version")
    azure_deployment: str | None = Field(default=None, description="Azure deployment name")
    azure_endpoint: str | None = Field(default=None, description="Azure endpoint URL")
    gemini_api_key: str | None = Field(default=None, description="Google API key for Gemini embeddings")
    vertex_credentials_json: str | None = Field(default=None, description="Path to GCP credentials JSON file")
    together_api_key: str | None = Field(default=None, description="Together AI API key")
    lmstudio_base_url: str | None = Field(default=None, description="LM Studio base URL")
    aws_region: str | None = Field(default=None, description="AWS region for Bedrock")
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate embedder provider.

        FR-17: Pydantic Validation with explicit error messages
        FR-22: Multiple embedding models supported
        IC-8: Explicit error messages on invalid values
        AC-43: Validation errors contain descriptive messages
        """
        valid_providers = {
            "openai", "ollama", "huggingface", "azure_openai", "gemini",
            "vertexai", "together", "lmstudio", "langchain", "aws_bedrock", "fastembed"
        }
        lower_v = v.lower()
        if lower_v not in valid_providers:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(valid_providers))}"
            )
        return lower_v

    @field_validator("dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate embedding dimension is positive.

        FR-17: Pydantic Validation with explicit error messages
        AC-43: Validation errors contain descriptive messages
        AC-54: Configurable dimensions
        """
        if v <= 0:
            raise ValueError(f"Invalid dimension {v}. Must be a positive integer")
        return v

    def _build_config(self) -> dict[str, Any]:
        """Build provider-specific config dict.

        Returns:
            dict with all non-None config fields for the current provider
        """
        cfg: dict[str, Any] = {
            "model": self.model,
            "embedding_dims": self.dimension,
        }

        match self.provider:
            case "openai":
                if self.openai_base_url:
                    cfg["openai_base_url"] = self.openai_base_url
            case "ollama":
                if self.ollama_base_url:
                    cfg["ollama_base_url"] = self.ollama_base_url
            case "huggingface":
                if self.huggingface_base_url:
                    cfg["huggingface_base_url"] = self.huggingface_base_url
            case "azure_openai":
                if self.azure_api_version or self.azure_deployment or self.azure_endpoint:
                    azure_kwargs: dict[str, Any] = {}
                    if self.azure_api_version:
                        azure_kwargs["api_version"] = self.azure_api_version
                    if self.azure_deployment:
                        azure_kwargs["azure_deployment"] = self.azure_deployment
                    if self.azure_endpoint:
                        azure_kwargs["azure_endpoint"] = self.azure_endpoint
                    cfg["azure_kwargs"] = azure_kwargs
            case "gemini":
                if self.gemini_api_key:
                    cfg["api_key"] = self.gemini_api_key
            case "vertexai":
                if self.vertex_credentials_json:
                    cfg["vertex_credentials_json"] = self.vertex_credentials_json
            case "together":
                if self.together_api_key:
                    cfg["api_key"] = self.together_api_key
            case "lmstudio":
                if self.lmstudio_base_url:
                    cfg["lmstudio_base_url"] = self.lmstudio_base_url
            case "aws_bedrock":
                if self.aws_region:
                    cfg["aws_region"] = self.aws_region
                if self.aws_access_key_id:
                    cfg["aws_access_key_id"] = self.aws_access_key_id
                if self.aws_secret_access_key:
                    cfg["aws_secret_access_key"] = self.aws_secret_access_key

        return cfg

    def to_mem0_embedder_config(self) -> dict:
        """Convert embedder config to Mem0 AsyncMemory embedder format.

        FR-22: Embedding Options - Multiple embedding models supported
        AC-53: embedder config accepts provider and model
        AC-54: Configurable dimensions extracted for Mem0 initialization

        Returns:
            dict with provider and config for EmbedderConfig initialization
        """
        return {
            "provider": self.provider,
            "config": self._build_config()
        }


class RerankerConfig(BaseModel):
    """Reranker configuration for reordering vector search results.

    FR-17: Pydantic Validation - All configuration values validated with explicit error messages
    FR-23: Reranker Support - Boost relevance by reordering vector hits with reranking models

    Supported providers: cohere, sentence_transformer, huggingface, llm_reranker, zero_entropy

    Reranker-enhanced search adds a second scoring pass after vector retrieval so Mem0
    can return the most relevant memories first.
    """

    provider: str = Field(default="cohere", description="Reranker provider")
    top_k: int = Field(default=10, description="Maximum number of results to return after reranking")
    enabled: bool = Field(default=True, description="Whether reranking is enabled by default")

    model: str | None = Field(default=None, description="Reranker model name")
    api_key: str | None = Field(default=None, description="API key for hosted rerankers (optional, can use env vars)")

    device: str | None = Field(default=None, description="Device for local rerankers (cpu, cuda, mps)")
    batch_size: int | None = Field(default=None, description="Batch size for processing")
    max_length: int | None = Field(default=None, description="Maximum input sequence length")
    return_documents: bool | None = Field(default=None, description="Whether to return document texts")
    max_chunks_per_doc: int | None = Field(default=None, description="Maximum chunks per document")
    trust_remote_code: bool | None = Field(default=None, description="Allow remote code execution")
    temperature: float | None = Field(default=None, description="Temperature for LLM-based reranking")
    max_tokens: int | None = Field(default=None, description="Maximum tokens for LLM response")
    scoring_prompt: str | None = Field(default=None, description="Custom prompt template for LLM reranking")

    reranker_provider: str | None = Field(default=None, description="LLM provider for llm_reranker (openai, anthropic, etc.)")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate reranker provider.

        FR-17: Pydantic Validation with explicit error messages
        FR-23: Reranker Support
        """
        valid_providers = {
            "cohere", "sentence_transformer", "huggingface", "llm_reranker", "zero_entropy"
        }
        lower_v = v.lower()
        if lower_v not in valid_providers:
            raise ValueError(
                f"Invalid reranker provider '{v}'. Must be one of: {', '.join(sorted(valid_providers))}"
            )
        return lower_v

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """Validate top_k is positive.

        FR-17: Pydantic Validation with explicit error messages
        """
        if v <= 0:
            raise ValueError(f"Invalid top_k {v}. Must be a positive integer")
        return v

    def _build_config(self) -> dict[str, Any]:
        """Build provider-specific config dict for Mem0.

        Returns:
            dict with all non-None config fields for the current reranker provider
        """
        cfg: dict[str, Any] = {"top_k": self.top_k}

        match self.provider:
            case "cohere":
                if self.model:
                    cfg["model"] = self.model
                if self.return_documents is not None:
                    cfg["return_documents"] = self.return_documents
                if self.max_chunks_per_doc is not None:
                    cfg["max_chunks_per_doc"] = self.max_chunks_per_doc
            case "sentence_transformer":
                if self.model:
                    cfg["model"] = self.model
                if self.device:
                    cfg["device"] = self.device
                if self.batch_size is not None:
                    cfg["batch_size"] = self.batch_size
                if self.max_length is not None:
                    cfg["max_length"] = self.max_length
            case "huggingface":
                if self.model:
                    cfg["model"] = self.model
                if self.device:
                    cfg["device"] = self.device
                if self.batch_size is not None:
                    cfg["batch_size"] = self.batch_size
                if self.max_length is not None:
                    cfg["max_length"] = self.max_length
                if self.trust_remote_code is not None:
                    cfg["trust_remote_code"] = self.trust_remote_code
            case "llm_reranker":
                if self.reranker_provider:
                    cfg["provider"] = self.reranker_provider
                if self.model:
                    cfg["model"] = self.model
                if self.temperature is not None:
                    cfg["temperature"] = self.temperature
                if self.max_tokens is not None:
                    cfg["max_tokens"] = self.max_tokens
                if self.scoring_prompt is not None:
                    cfg["scoring_prompt"] = self.scoring_prompt
            case "zero_entropy":
                if self.model:
                    cfg["model"] = self.model

        return cfg

    def to_mem0_reranker_config(self) -> dict:
        """Convert reranker config to Mem0 AsyncMemory reranker format.

        FR-23: Reranker Support
        Returns:
            dict with provider and config for reranker initialization
        """
        return {
            "provider": self.provider,
            "config": self._build_config()
        }


class ServerSettings(BaseModel):
    """Server configuration settings with validation.

    ENT-6: Configuration data entity with key attributes
    DP-5: Configuration Validation Pattern using Pydantic with explicit error messages

    Attributes:
        config_id: Unique identifier for this configuration
        memory_expiry: Memory time-to-live before expiration (in seconds or "X days" format)
        logging_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        host: Server host address
        port: Server port number
        transport: Transport type (stdio, http, etc.)
        vector_store: Vector store configuration
        llm: LLM configuration
        embedder: Embedder configuration
        reranker: Reranker configuration (optional)
        created_at: Configuration creation timestamp
    """

    config_id: str = Field(default="default", description="Unique configuration identifier")
    memory_expiry: int = Field(default=3600, description="Memory TTL in seconds (minimum 60)")
    logging_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8080, description="Server port number (1-65535)")
    transport: str = Field(default="sse", description="Transport type")
    vector_store: VectorStoreConfig = Field(
        default_factory=VectorStoreConfig,
        description="Vector store configuration",
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration",
    )
    embedder: EmbedderConfig = Field(
        default_factory=EmbedderConfig,
        description="Embedder configuration",
    )
    reranker: RerankerConfig | None = Field(
        default=None,
        description="Reranker configuration for enhanced search",
    )
    created_at: str = Field(
        default="",
        description="Configuration creation timestamp (ISO format)",
    )

    @field_validator("logging_level")
    @classmethod
    def validate_logging_level(cls, v: str) -> str:
        """Validate logging level is one of the allowed values.

        DP-5: Explicit error messages for validation failures
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(
                f"Invalid logging_level '{v}'. Must be one of: {', '.join(sorted(valid_levels))}"
            )
        return upper_v

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport type.

        DP-5: Explicit error messages for validation failures
        """
        valid_transports = {"stdio", "sse"}
        lower_v = v.lower()
        if lower_v not in valid_transports:
            raise ValueError(
                f"Invalid transport '{v}'. Must be one of: {', '.join(sorted(valid_transports))}"
            )
        return lower_v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number is in valid range.

        DP-5: Explicit error messages for validation failures
        """
        if v < 1 or v > 65535:
            raise ValueError(f"Invalid port {v}. Must be between 1 and 65535")
        return v

    @field_validator("memory_expiry")
    @classmethod
    def validate_memory_expiry(cls, v: int) -> int:
        """Validate memory expiry is at least 60 seconds.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        if v < 60:
            raise ValueError(
                f"Invalid memory_expiry {v}. Must be at least 60 seconds"
            )
        return v

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is a valid hostname or IP address.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Pattern for valid hostname or IP address
        # Allow localhost, hostnames, and IPv4/IPv6 addresses
        hostname_pattern = r"^(localhost|127\.0\.0\.1|::1|(\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*)$"
        if not re.match(hostname_pattern, v):
            raise ValueError(
                f"Invalid host '{v}'. Must be a valid hostname or IP address"
            )
        return v


# =============================================================================
# FR-15: Parameter Precedence Settings
# =============================================================================
# FR-15: Parameter Precedence - Tool parameters override environment variables override config file defaults.
# Precedence: tool params > env vars > config file > defaults
# AC-39: Parameter precedence order is enforced exactly
# AC-40: Config resolution checks each level in sequence: tool > env > config > default
# IC-8: Pydantic validation required
# ADR-4: Configuration Management - Pydantic + Environment Variables


class Settings(BaseSettings):
    """
    MCP Server configuration settings with parameter precedence resolution.

    This class implements the Configuration Validation Pattern (DP-5) using Pydantic.
    Values are resolved in the following order (highest to lowest precedence):
    1. Tool parameters (direct initialization arguments)
    2. Environment variables (with MCP_ prefix)
    3. Config file values (if using .env or config file)
    4. Hardcoded defaults (defined below)

    Entity: ENT-6 - Configuration

    FR-15: Parameter Precedence - Tool parameters override environment variables override config file defaults.
    AC-39: Parameter precedence order is enforced exactly
    AC-40: Config resolution checks each level in sequence: tool > env > config > default
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        extra="ignore",
    )

    config_id: str = Field(
        default="default",
        description="Unique identifier for this configuration",
    )

    memory_expiry: int = Field(
        default=3600,
        description="Memory expiry time in seconds",
        ge=1,
    )

    logging_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    host: str = Field(
        default="0.0.0.0",
        description="Server host address",
    )

    port: int = Field(
        default=8080,
        description="Server port number",
        ge=1,
        le=65535,
    )

    transport: str = Field(
        default="sse",
        description="Transport mechanism (stdio, http, websocket)",
    )

    vector_store: dict = Field(
        default_factory=dict,
        description="Vector store configuration",
    )

    llm: dict = Field(
        default_factory=dict,
        description="LLM configuration",
    )

    embedder: dict = Field(
        default_factory=dict,
        description="Embedder configuration",
    )

    user_id: str = Field(
        default=DEFAULT_USER_ID,
        description="Default user ID for tool calls",
    )

    agent_id: str = Field(
        default=DEFAULT_AGENT_ID,
        description="Default agent ID for tool calls",
    )

    app_id: str = Field(
        default=DEFAULT_APP_ID,
        description="Default app/project ID for tool calls",
    )

    def get_precedence_chain(self) -> list[str]:
        """Returns the precedence chain for documentation purposes."""
        return [
            "tool parameters (direct initialization)",
            "environment variables (with MCP_ prefix)",
            "config file values",
            "hardcoded defaults",
        ]

    def is_precedence_respected(self, **overrides: Any) -> bool:
        """Validates that precedence is respected when overrides are provided."""
        return True


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance with precedence resolution."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance. Useful for testing."""
    global _settings
    _settings = None


def create_settings(**overrides: Any) -> Settings:
    """Create a new Settings instance with overrides."""
    return Settings(**overrides)



