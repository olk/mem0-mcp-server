"""
# UT-6: Vector Database Flexibility tests
# Validates: FR-21, AC-51, AC-52, CPARA-9
# Scenario: SCEN-16 (vector_store config extraction), SCEN-17 (Redis backend support)
# AC-51: vector_store config with provider and config
# AC-52: Redis backend supported
# FR-21: Vector Database Flexibility - Support multiple vector store backends

Unit tests for vector store configuration and multi-backend support.
Tests provider extraction, config structure, and Redis backend functionality.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.config.settings import VectorStoreConfig
from mcp_server.memory.manager import MemoryManager


class TestVectorStoreConfig:
    """# FR-21: Vector Database Flexibility - Support multiple vector store backends
    # AC-51: vector_store config with provider and config
    # CPARA-9: VECTOR_STORE configuration
    """

    def test_default_redis_provider(self):
        """# AC-52: Redis backend supported as default"""
        config = VectorStoreConfig()
        assert config.provider == "redis"

    def test_redis_backend_supported(self):
        """# AC-52: Redis backend is a valid provider"""
        config = VectorStoreConfig(provider="redis")
        assert config.provider == "redis"

    def test_qdrant_backend_supported(self):
        """# FR-21: Multiple backends - Qdrant is a valid provider"""
        config = VectorStoreConfig(provider="qdrant")
        assert config.provider == "qdrant"

    def test_chroma_backend_supported(self):
        """# FR-21: Multiple backends - Chroma is a valid provider"""
        config = VectorStoreConfig(provider="chroma")
        assert config.provider == "chroma"

    def test_invalid_provider_rejected(self):
        """# FR-21: Invalid provider rejected"""
        with pytest.raises(ValueError) as exc_info:
            VectorStoreConfig(provider="invalid_provider")
        assert "invalid_provider" in str(exc_info.value)

    def test_provider_case_insensitive(self):
        """# FR-21: Provider validation is case insensitive"""
        config = VectorStoreConfig(provider="REDIS")
        assert config.provider == "redis"

    def test_redis_url_default(self):
        """# AC-52: Redis backend has default redis_url"""
        config = VectorStoreConfig()
        assert config.redis_url is None or config.redis_url == "redis://localhost:6379"

    def test_redis_url_custom(self):
        """# AC-52: Redis backend supports custom redis_url"""
        config = VectorStoreConfig(redis_url="redis://custom:6379")
        assert config.redis_url == "redis://custom:6379"

    def test_embedding_model_dims_default(self):
        """# CPARA-9: Default embedding_model_dims is 1536"""
        config = VectorStoreConfig()
        assert config.embedding_model_dims == 1536

    def test_embedding_model_dims_custom(self):
        """# CPARA-9: Custom embedding_model_dims supported"""
        config = VectorStoreConfig(embedding_model_dims=768)
        assert config.embedding_model_dims == 768

    def test_collection_name_default(self):
        """# CPARA-9: Default collection_name is 'mem0'"""
        config = VectorStoreConfig()
        assert config.collection_name == "mem0"

    def test_collection_name_custom(self):
        """# CPARA-9: Custom collection_name supported"""
        config = VectorStoreConfig(collection_name="custom_collection")
        assert config.collection_name == "custom_collection"


class TestVectorStoreConfigToMem0:
    """# AC-51: vector_store config with provider and config
    # AC-52: Redis backend configured with redis_url, collection_name, embedding_model_dims
    # CPARA-9: VECTOR_STORE configuration structure
    """

    def test_to_mem0_config_redis(self):
        """# AC-51: Provider and config extracted for Mem0
        # AC-52: Redis backend config format"""
        config = VectorStoreConfig(
            provider="redis",
            redis_url="redis://localhost:6379",
            collection_name="mem0",
            embedding_model_dims=1536
        )
        mem0_config = config.to_mem0_vector_store_config()

        assert mem0_config["provider"] == "redis"
        assert "config" in mem0_config
        assert mem0_config["config"]["collection_name"] == "mem0"
        assert mem0_config["config"]["embedding_model_dims"] == 1536
        assert mem0_config["config"]["redis_url"] == "redis://localhost:6379"

    def test_to_mem0_config_qdrant(self):
        """# FR-21: Qdrant backend config format"""
        config = VectorStoreConfig(
            provider="qdrant",
            location=":memory:",
            collection_name="mem0"
        )
        mem0_config = config.to_mem0_vector_store_config()

        assert mem0_config["provider"] == "qdrant"
        assert "config" in mem0_config

    def test_to_mem0_config_contains_provider_and_config(self):
        """# AC-51: Config structure has provider and config keys"""
        config = VectorStoreConfig()
        mem0_config = config.to_mem0_vector_store_config()

        assert "provider" in mem0_config
        assert "config" in mem0_config
        assert isinstance(mem0_config["config"], dict)


class TestMemoryManagerVectorStore:
    """# FR-21: Vector Database Flexibility - MemoryManager with vector_store support
    # AC-51: MemoryManager extracts vector_store config
    # AC-52: Redis backend available
    """

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.get_all = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    def test_memory_manager_with_vector_store_config(self, mock_mem0_client):
        """# AC-51: MemoryManager accepts vector_store_config"""
        vector_config = VectorStoreConfig(
            provider="redis",
            redis_url="redis://localhost:6379",
            collection_name="mem0",
            embedding_model_dims=1536
        )
        manager = MemoryManager(mock_mem0_client, vector_store_config=vector_config)

        assert manager.vector_store_config.provider == "redis"
        assert manager.vector_store_provider == "redis"

    def test_memory_manager_default_vector_store_config(self, mock_mem0_client):
        """# AC-52: Default vector_store_config is Redis"""
        manager = MemoryManager(mock_mem0_client)

        assert manager.vector_store_config.provider == "redis"
        assert manager.vector_store_provider == "redis"

    def test_vector_store_provider_property(self, mock_mem0_client):
        """# AC-51: vector_store_provider property extracts provider"""
        vector_config = VectorStoreConfig(provider="qdrant")
        manager = MemoryManager(mock_mem0_client, vector_store_config=vector_config)

        assert manager.vector_store_provider == "qdrant"

    def test_multiple_providers_support(self, mock_mem0_client):
        """# FR-21: Support multiple vector store backends"""
        providers = ["redis", "qdrant", "chroma", "milvus", "faiss", "pgvector"]

        for provider in providers:
            vector_config = VectorStoreConfig(provider=provider)
            manager = MemoryManager(mock_mem0_client, vector_store_config=vector_config)
            assert manager.vector_store_provider == provider

    @pytest.mark.asyncio
    async def test_add_memory_with_vector_store(self, mock_mem0_client):
        """# AC-51: Memory operations work with vector_store config"""
        from mcp_server.memory.manager import TenantScope

        vector_config = VectorStoreConfig(provider="redis")
        manager = MemoryManager(mock_mem0_client, vector_store_config=vector_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.add_memory(scope=scope, content="Test memory")

        assert result.id == "mem-123"
        assert result.content == "Test memory"
        mock_mem0_client.add.assert_called_once()


class TestVectorStoreConfigBuildConfig:
    """Test VectorStoreConfig._build_config() for all providers.

    These tests cover the missing lines 321-449 in settings.py where
    each provider's configuration is built differently.
    """

    def test_build_config_redis_with_url(self):
        """Test Redis config building with redis_url."""
        config = VectorStoreConfig(
            provider="redis",
            redis_url="redis://localhost:6379",
            collection_name="mem0",
            embedding_model_dims=1536
        )
        cfg = config._build_config()
        assert cfg["redis_url"] == "redis://localhost:6379"
        assert cfg["collection_name"] == "mem0"

    def test_build_config_qdrant_with_url(self):
        """Test Qdrant config building with qdrant_url."""
        config = VectorStoreConfig(
            provider="qdrant",
            qdrant_url="http://localhost:6333",
            qdrant_api_key="secret-key",
            collection_name="mem0"
        )
        cfg = config._build_config()
        assert cfg["url"] == "http://localhost:6333"
        assert cfg["api_key"] == "secret-key"

    def test_build_config_qdrant_with_host_port(self):
        """Test Qdrant config building with host and port."""
        config = VectorStoreConfig(
            provider="qdrant",
            qdrant_host="localhost",
            qdrant_port=6334,
            collection_name="mem0"
        )
        cfg = config._build_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 6334

    def test_build_config_qdrant_with_path(self):
        """Test Qdrant config building with local path."""
        config = VectorStoreConfig(
            provider="qdrant",
            qdrant_path="/tmp/qdrant",
            qdrant_on_disk=True
        )
        cfg = config._build_config()
        assert cfg["path"] == "/tmp/qdrant"
        assert cfg["on_disk"] is True

    def test_build_config_chroma_with_path(self):
        """Test Chroma config building with path."""
        config = VectorStoreConfig(
            provider="chroma",
            chroma_path="/tmp/chroma"
        )
        cfg = config._build_config()
        assert cfg["path"] == "/tmp/chroma"

    def test_build_config_chroma_with_host_port(self):
        """Test Chroma config building with host and port."""
        config = VectorStoreConfig(
            provider="chroma",
            chroma_host="localhost",
            chroma_port=8000
        )
        cfg = config._build_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 8000

    def test_build_config_chroma_with_api_key(self):
        """Test Chroma config building with API key."""
        config = VectorStoreConfig(
            provider="chroma",
            chroma_api_key="secret-key",
            chroma_tenant="tenant-1"
        )
        cfg = config._build_config()
        assert cfg["api_key"] == "secret-key"
        assert cfg["tenant"] == "tenant-1"

    def test_build_config_pgvector_with_connection_string(self):
        """Test PostgreSQL/pgvector config building with connection string."""
        config = VectorStoreConfig(
            provider="pgvector",
            pgvector_connection_string="postgresql://user:pass@localhost:5432/db",
            pgvector_hnsw=True,
            pgvector_diskann=False
        )
        cfg = config._build_config()
        assert cfg["connection_string"] == "postgresql://user:pass@localhost:5432/db"
        assert cfg["hnsw"] is True
        assert cfg["diskann"] is False

    def test_build_config_pgvector_with_individual_params(self):
        """Test PostgreSQL/pgvector config building with individual params."""
        config = VectorStoreConfig(
            provider="pgvector",
            pgvector_dbname="mydb",
            pgvector_user="user",
            pgvector_password="pass",
            pgvector_host="localhost",
            pgvector_port=5432,
            pgvector_sslmode="require"
        )
        cfg = config._build_config()
        assert cfg["dbname"] == "mydb"
        assert cfg["user"] == "user"
        assert cfg["password"] == "pass"
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 5432
        assert cfg["sslmode"] == "require"

    def test_build_config_milvus(self):
        """Test Milvus config building."""
        config = VectorStoreConfig(
            provider="milvus",
            milvus_url="http://localhost:19530",
            milvus_token="token",
            milvus_db_name="default",
            milvus_metric_type="IP"
        )
        cfg = config._build_config()
        assert cfg["url"] == "http://localhost:19530"
        assert cfg["token"] == "token"
        assert cfg["db_name"] == "default"
        assert cfg["metric_type"] == "IP"

    def test_build_config_pinecone(self):
        """Test Pinecone config building."""
        config = VectorStoreConfig(
            provider="pinecone",
            pinecone_api_key="secret-key",
            pinecone_environment="us-east-1",
            pinecone_namespace="namespace"
        )
        cfg = config._build_config()
        assert cfg["api_key"] == "secret-key"
        assert cfg["environment"] == "us-east-1"
        assert cfg["namespace"] == "namespace"

    def test_build_config_mongodb(self):
        """Test MongoDB config building."""
        config = VectorStoreConfig(
            provider="mongodb",
            mongodb_mongo_uri="mongodb://localhost:27017",
            mongodb_db_name="mem0"
        )
        cfg = config._build_config()
        assert cfg["mongo_uri"] == "mongodb://localhost:27017"
        assert cfg["db_name"] == "mem0"

    def test_build_config_weaviate(self):
        """Test Weaviate config building."""
        config = VectorStoreConfig(
            provider="weaviate",
            weaviate_cluster_url="http://localhost:8080",
            weaviate_auth_client_secret="secret"
        )
        cfg = config._build_config()
        assert cfg["cluster_url"] == "http://localhost:8080"
        assert cfg["auth_client_secret"] == "secret"

    def test_build_config_faiss(self):
        """Test FAISS config building."""
        config = VectorStoreConfig(
            provider="faiss",
            faiss_path="/tmp/faiss",
            faiss_distance_strategy="cosine"
        )
        cfg = config._build_config()
        assert cfg["path"] == "/tmp/faiss"
        assert cfg["distance_strategy"] == "cosine"

    def test_build_config_supabase(self):
        """Test Supabase config building."""
        config = VectorStoreConfig(
            provider="supabase",
            supabase_connection_string="postgresql://...",
            supabase_index_method="hnsw",
            supabase_index_measure="cosine"
        )
        cfg = config._build_config()
        assert cfg["connection_string"] == "postgresql://..."
        assert cfg["index_method"] == "hnsw"
        assert cfg["index_measure"] == "cosine"

    def test_build_config_upstash_vector(self):
        """Test Upstash Vector config building."""
        config = VectorStoreConfig(
            provider="upstash_vector",
            upstash_vector_url="https://xxx.upstash.io",
            upstash_vector_token="token"
        )
        cfg = config._build_config()
        assert cfg["url"] == "https://xxx.upstash.io"
        assert cfg["token"] == "token"

    def test_build_config_opensearch(self):
        """Test OpenSearch config building."""
        config = VectorStoreConfig(
            provider="opensearch",
            opensearch_host="localhost",
            opensearch_port=9200,
            opensearch_user="admin",
            opensearch_password="password",
            opensearch_use_ssl=True,
            opensearch_verify_certs=True
        )
        cfg = config._build_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 9200
        assert cfg["user"] == "admin"
        assert cfg["password"] == "password"
        assert cfg["use_ssl"] is True
        assert cfg["verify_certs"] is True

    def test_build_config_opensearch_with_api_key(self):
        """Test OpenSearch config building with API key."""
        config = VectorStoreConfig(
            provider="opensearch",
            opensearch_api_key="api-key"
        )
        cfg = config._build_config()
        assert cfg["api_key"] == "api-key"

    def test_build_config_elasticsearch(self):
        """Test Elasticsearch config building."""
        config = VectorStoreConfig(
            provider="elasticsearch",
            elasticsearch_host="localhost",
            elasticsearch_port=9200,
            elasticsearch_cloud_id="cluster:dXMtZWFzd...",
            elasticsearch_api_key="api-key",
            elasticsearch_user="elastic",
            elasticsearch_password="password"
        )
        cfg = config._build_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 9200
        assert cfg["cloud_id"] == "cluster:dXMtZWFzd..."
        assert cfg["api_key"] == "api-key"
        assert cfg["user"] == "elastic"
        assert cfg["password"] == "password"

    def test_build_config_azure_ai_search(self):
        """Test Azure AI Search config building."""
        config = VectorStoreConfig(
            provider="azure_ai_search",
            azure_ai_search_service_name="myservice",
            azure_ai_search_api_key="key"
        )
        cfg = config._build_config()
        assert cfg["service_name"] == "myservice"
        assert cfg["api_key"] == "key"

    def test_build_config_valkey(self):
        """Test Valkey config building."""
        config = VectorStoreConfig(
            provider="valkey",
            valkey_url="valkey://localhost:6379",
            valkey_index_type="hnsw"
        )
        cfg = config._build_config()
        assert cfg["valkey_url"] == "valkey://localhost:6379"
        assert cfg["index_type"] == "hnsw"

    def test_build_config_s3_vectors(self):
        """Test S3 Vectors config building."""
        config = VectorStoreConfig(
            provider="s3_vectors",
            s3_vectors_bucket="my-bucket",
            s3_vectors_region="us-east-1"
        )
        cfg = config._build_config()
        assert cfg["vector_bucket_name"] == "my-bucket"
        assert cfg["region_name"] == "us-east-1"

    def test_build_config_redis_no_url(self):
        """Test Redis config building without redis_url (optional)."""
        config = VectorStoreConfig(
            provider="redis",
            collection_name="mem0",
            embedding_model_dims=1536
        )
        cfg = config._build_config()
        assert "redis_url" not in cfg
        assert cfg["collection_name"] == "mem0"
