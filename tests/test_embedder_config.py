"""
# UT-7: Embedding Options tests
# Validates: FR-22, AC-53, AC-54
# Scenario: Embedder provider/model configuration and configurable dimensions
# AC-53: embedder config accepts provider and model
# AC-54: Configurable dimensions

Unit tests for Embedding Options functionality.
Tests EmbedderConfig validation, provider/model extraction, and configurable dimensions.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.config.settings import EmbedderConfig
from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)


class TestEmbedderConfig:
    """# FR-22: Embedding Options - Multiple embedding models supported"""

    def test_default_embedder_config(self):
        """# AC-53: Embedder config accepts provider and model (default values)"""
        config = EmbedderConfig()
        assert config.provider == "openai"
        assert config.model == "text-embedding-3-small"
        assert config.dimension == 1536

    def test_custom_embedder_config(self):
        """# AC-53: Embedder config accepts custom provider and model"""
        config = EmbedderConfig(
            provider="huggingface",
            model="embed-english-v2.0",
            dimension=768
        )
        assert config.provider == "huggingface"
        assert config.model == "embed-english-v2.0"
        assert config.dimension == 768

    def test_provider_case_insensitive(self):
        """# FR-22: Multiple embedding models - case insensitive provider"""
        config = EmbedderConfig(provider="HUGGINGFACE", model="embed-english-v2.0")
        assert config.provider == "huggingface"

    def test_valid_providers(self):
        """# FR-22: Multiple embedding models supported - all valid providers"""
        valid_providers = ["openai", "huggingface", "vertexai", "ollama", "gemini", "azure_openai", "together", "lmstudio", "aws_bedrock", "fastembed"]
        for provider in valid_providers:
            config = EmbedderConfig(provider=provider, model="test-model")
            assert config.provider == provider

    def test_invalid_provider_rejected(self):
        """# FR-22: Multiple embedding models - invalid provider rejected"""
        with pytest.raises(ValueError) as exc_info:
            EmbedderConfig(provider="invalid_provider", model="test-model")
        assert "invalid_provider" in str(exc_info.value)
        assert "openai" in str(exc_info.value)  # Shows valid options

    def test_dimension_validation(self):
        """# AC-54: Configurable dimensions - dimension must be positive"""
        # Valid dimension
        config = EmbedderConfig(dimension=384)
        assert config.dimension == 384

        config = EmbedderConfig(dimension=3072)
        assert config.dimension == 3072

        # Invalid dimension zero
        with pytest.raises(ValueError) as exc_info:
            EmbedderConfig(dimension=0)
        assert "0" in str(exc_info.value)

        # Invalid dimension negative
        with pytest.raises(ValueError):
            EmbedderConfig(dimension=-1)

    def test_various_dimensions(self):
        """# AC-54: Configurable dimensions - various dimension values supported"""
        common_dimensions = [256, 384, 512, 768, 1024, 1536, 3072]
        for dim in common_dimensions:
            config = EmbedderConfig(dimension=dim)
            assert config.dimension == dim


class TestEmbedderConfigToMem0:
    """# FR-22: Convert embedder config to Mem0 format"""

    def test_to_mem0_embedder_config(self):
        """# AC-53: embedder config accepts provider and model
        # AC-54: Dimensions extracted for Mem0 initialization"""
        config = EmbedderConfig(
            provider="openai",
            model="text-embedding-3-large",
            dimension=1536
        )
        mem0_config = config.to_mem0_embedder_config()

        assert mem0_config["provider"] == "openai"
        assert mem0_config["config"]["model"] == "text-embedding-3-large"
        assert mem0_config["config"]["embedding_dims"] == 1536

    def test_to_mem0_embedder_config_default(self):
        """# AC-53: Default embedder config converts correctly"""
        config = EmbedderConfig()
        mem0_config = config.to_mem0_embedder_config()

        assert mem0_config["provider"] == "openai"
        assert mem0_config["config"]["model"] == "text-embedding-3-small"
        assert mem0_config["config"]["embedding_dims"] == 1536

    def test_to_mem0_embedder_config_custom_dimensions(self):
        """# AC-54: Custom dimensions included in Mem0 config"""
        config = EmbedderConfig(
            provider="huggingface",
            model="embed-english-v3.0",
            dimension=1024
        )
        mem0_config = config.to_mem0_embedder_config()

        assert mem0_config["provider"] == "huggingface"
        assert mem0_config["config"]["model"] == "embed-english-v3.0"
        assert mem0_config["config"]["embedding_dims"] == 1024


class TestMemoryManagerEmbedderConfig:
    """# FR-22: MemoryManager with Embedding Options"""

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

    def test_memory_manager_with_embedder_config(self, mock_mem0_client):
        """# AC-53: MemoryManager accepts embedder config with provider and model"""
        embedder_config = EmbedderConfig(provider="openai", model="text-embedding-3-large")
        manager = MemoryManager(mem0_client=mock_mem0_client, embedder_config=embedder_config)

        assert manager.embedder_provider == "openai"
        assert manager.embedder_model == "text-embedding-3-large"

    def test_memory_manager_without_embedder_config(self, mock_mem0_client):
        """# AC-53: MemoryManager uses default embedder config when not provided"""
        manager = MemoryManager(mem0_client=mock_mem0_client)

        assert manager.embedder_provider == "openai"
        assert manager.embedder_model == "text-embedding-3-small"
        assert manager.embedder_dimensions == 1536

    def test_memory_manager_embedder_properties(self, mock_mem0_client):
        """# AC-53: Embedder provider and model accessible via properties
        # AC-54: Embedder dimensions accessible via property"""
        config = EmbedderConfig(provider="huggingface", model="embed-english-v2.0", dimension=768)
        manager = MemoryManager(mem0_client=mock_mem0_client, embedder_config=config)

        # AC-53: Provider extracted from config
        assert manager.embedder_provider == "huggingface"

        # AC-53: Model extracted from config
        assert manager.embedder_model == "embed-english-v2.0"

        # AC-54: Dimensions extracted from config
        assert manager.embedder_dimensions == 768

    @pytest.mark.asyncio
    async def test_add_memory_with_embedder_config(self, mock_mem0_client):
        """# FR-22: Memory operations work with custom embedder config"""
        embedder_config = EmbedderConfig(provider="huggingface", model="embed-english-v3.0", dimension=1024)
        manager = MemoryManager(mem0_client=mock_mem0_client, embedder_config=embedder_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.add_memory(
            scope=scope,
            content="Test memory content"
        )

        assert result.id == "mem-123"
        assert result.content == "Test memory content"

        # Verify embedder config is still accessible
        assert manager.embedder_provider == "huggingface"
        assert manager.embedder_model == "embed-english-v3.0"
        assert manager.embedder_dimensions == 1024


class TestMultipleEmbeddingModels:
    """# FR-22: Multiple embedding models supported"""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[])
        client.get_all = AsyncMock(return_value=[])
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    @pytest.mark.parametrize("provider,model,dimension", [
        ("openai", "text-embedding-3-small", 1536),
        ("openai", "text-embedding-3-large", 3072),
        ("openai", "text-embedding-ada-002", 1536),
        ("huggingface", "embed-english-v2.0", 768),
        ("huggingface", "embed-english-light-v3.0", 384),
        ("vertexai", "text-embedding-005", 768),
        ("ollama", "nomic-embed-text",  768),
        ("gemini", "models/gemini-embedding-001", 1536),
        ("together", "togethercomputer/m2-bert-80k-8k", 1024),
    ])
    def test_various_embedder_providers_accepted(self, mock_mem0_client, provider, model, dimension):
        """# FR-22: Various embedding providers and models configurable
        # AC-54: Various dimensions supported"""
        config = EmbedderConfig(provider=provider, model=model, dimension=dimension)
        manager = MemoryManager(mem0_client=mock_mem0_client, embedder_config=config)

        assert manager.embedder_provider == provider
        assert manager.embedder_model == model
        assert manager.embedder_dimensions == dimension

    def test_embedder_config_in_logging(self, mock_mem0_client):
        """# FR-22: Embedding Options - provider, model, and dimensions visible in initialization"""
        config = EmbedderConfig(
            provider="openai",
            model="text-embedding-3-large",
            dimension=3072
        )
        # MemoryManager logs info on init with embedder info
        manager = MemoryManager(mem0_client=mock_mem0_client, embedder_config=config)

        # Manager should be initialized with the correct config
        assert manager.embedder_provider == "openai"
        assert manager.embedder_model == "text-embedding-3-large"
        assert manager.embedder_dimensions == 3072


class TestEmbedderConfigBuildConfig:
    """Test EmbedderConfig._build_config() for all providers.

    These tests cover the missing lines 701-752 in settings.py where
    each embedder provider's configuration is built differently.
    """

    def test_build_config_openai(self):
        """Test OpenAI embedder config building."""
        config = EmbedderConfig(
            provider="openai",
            model="text-embedding-3-small",
            dimension=1536,
            openai_base_url="https://api.openai.com/v1"
        )
        cfg = config._build_config()
        assert cfg["model"] == "text-embedding-3-small"
        assert cfg["embedding_dims"] == 1536
        assert cfg["openai_base_url"] == "https://api.openai.com/v1"

    def test_build_config_ollama(self):
        """Test Ollama embedder config building."""
        config = EmbedderConfig(
            provider="ollama",
            model="nomic-embed-text",
            dimension=768,
            ollama_base_url="http://localhost:11434"
        )
        cfg = config._build_config()
        assert cfg["ollama_base_url"] == "http://localhost:11434"

    def test_build_config_huggingface(self):
        """Test HuggingFace embedder config building."""
        config = EmbedderConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2",
            dimension=384,
            huggingface_base_url="https://api-inference.huggingface.co/models"
        )
        cfg = config._build_config()
        assert cfg["huggingface_base_url"] == "https://api-inference.huggingface.co/models"

    def test_build_config_azure_openai(self):
        """Test Azure OpenAI embedder config building."""
        config = EmbedderConfig(
            provider="azure_openai",
            model="text-embedding-3-small",
            azure_api_version="2024-02-01",
            azure_deployment="embedding-deployment",
            azure_endpoint="https://example.openai.azure.com"
        )
        cfg = config._build_config()
        assert "azure_kwargs" in cfg
        assert cfg["azure_kwargs"]["api_version"] == "2024-02-01"
        assert cfg["azure_kwargs"]["azure_deployment"] == "embedding-deployment"
        assert cfg["azure_kwargs"]["azure_endpoint"] == "https://example.openai.azure.com"

    def test_build_config_gemini(self):
        """Test Gemini embedder config building."""
        config = EmbedderConfig(
            provider="gemini",
            model="models/gemini-embedding-001",
            dimension=768,
            gemini_api_key="secret-key"
        )
        cfg = config._build_config()
        assert cfg["api_key"] == "secret-key"

    def test_build_config_vertexai(self):
        """Test Vertex AI embedder config building."""
        config = EmbedderConfig(
            provider="vertexai",
            model="text-embedding-005",
            dimension=768,
            vertex_credentials_json="/path/to/credentials.json"
        )
        cfg = config._build_config()
        assert cfg["vertex_credentials_json"] == "/path/to/credentials.json"

    def test_build_config_together(self):
        """Test Together AI embedder config building."""
        config = EmbedderConfig(
            provider="together",
            model="togethercomputer/m2-bert-80k-8k",
            dimension=1024,
            together_api_key="secret-key"
        )
        cfg = config._build_config()
        assert cfg["api_key"] == "secret-key"

    def test_build_config_lmstudio(self):
        """Test LM Studio embedder config building."""
        config = EmbedderConfig(
            provider="lmstudio",
            model="local-embedding-model",
            dimension=768,
            lmstudio_base_url="http://localhost:1234/v1"
        )
        cfg = config._build_config()
        assert cfg["lmstudio_base_url"] == "http://localhost:1234/v1"

    def test_build_config_aws_bedrock(self):
        """Test AWS Bedrock embedder config building."""
        config = EmbedderConfig(
            provider="aws_bedrock",
            model="amazon.titan-embed-text-v1",
            dimension=1536,
            aws_region="us-west-2",
            aws_access_key_id="AKIA...",
            aws_secret_access_key="secret"
        )
        cfg = config._build_config()
        assert cfg["aws_region"] == "us-west-2"
        assert cfg["aws_access_key_id"] == "AKIA..."
        assert cfg["aws_secret_access_key"] == "secret"

    def test_build_config_openai_no_base_url(self):
        """Test OpenAI embedder config without optional base URL."""
        config = EmbedderConfig(
            provider="openai",
            model="text-embedding-3-small",
            dimension=1536
        )
        cfg = config._build_config()
        assert cfg["model"] == "text-embedding-3-small"
        assert "openai_base_url" not in cfg
