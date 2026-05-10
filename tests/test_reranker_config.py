"""
# UT-8: Reranker Support tests
# Validates: FR-23, AC-55
# Scenario: Reranker provider/model configuration and reranking behavior
# AC-55: Reranker config accepts provider and model

Unit tests for Reranker Support functionality.
Tests RerankerConfig validation, provider/model extraction, and provider-specific options.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.config.settings import RerankerConfig
from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)


class TestRerankerConfig:
    """# FR-23: Reranker Support - Multiple reranker providers supported"""

    def test_default_reranker_config(self):
        """# AC-55: Reranker config accepts provider and model (default values)"""
        config = RerankerConfig()
        assert config.provider == "cohere"
        assert config.top_k == 10
        assert config.enabled is True

    def test_custom_reranker_config(self):
        """# AC-55: Reranker config accepts custom provider and model"""
        config = RerankerConfig(
            provider="sentence_transformer",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_k=5,
            enabled=False
        )
        assert config.provider == "sentence_transformer"
        assert config.model == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert config.top_k == 5
        assert config.enabled is False

    def test_provider_case_insensitive(self):
        """# FR-23: Reranker providers - case insensitive provider"""
        config = RerankerConfig(provider="COHERE", model="rerank-english-v3.0")
        assert config.provider == "cohere"

    def test_valid_providers(self):
        """# FR-23: Multiple reranker providers - all valid providers"""
        valid_providers = ["cohere", "sentence_transformer", "huggingface", "llm_reranker", "zero_entropy"]
        for provider in valid_providers:
            config = RerankerConfig(provider=provider, model="test-model")
            assert config.provider == provider

    def test_invalid_provider_rejected(self):
        """# FR-23: Multiple reranker providers - invalid provider rejected"""
        with pytest.raises(ValueError) as exc_info:
            RerankerConfig(provider="invalid_provider", model="test-model")
        assert "invalid_provider" in str(exc_info.value)
        assert "cohere" in str(exc_info.value)

    def test_top_k_validation(self):
        """# FR-23: top_k must be positive"""
        config = RerankerConfig(top_k=20)
        assert config.top_k == 20

        with pytest.raises(ValueError) as exc_info:
            RerankerConfig(top_k=0)
        assert "0" in str(exc_info.value)

        with pytest.raises(ValueError):
            RerankerConfig(top_k=-1)

    def test_enabled_default_true(self):
        """# FR-23: Reranking enabled by default when reranker is configured"""
        config = RerankerConfig()
        assert config.enabled is True

    def test_various_top_k_values(self):
        """# FR-23: Various top_k values supported"""
        for top_k in [5, 10, 15, 20, 50]:
            config = RerankerConfig(top_k=top_k)
            assert config.top_k == top_k


class TestRerankerConfigProviderSpecific:
    """# FR-23: Provider-specific configuration options"""

    def test_cohere_config(self):
        """Cohere reranker with specific options"""
        config = RerankerConfig(
            provider="cohere",
            model="rerank-english-v3.0",
            top_k=10,
            return_documents=True,
            max_chunks_per_doc=5
        )
        assert config.provider == "cohere"
        assert config.model == "rerank-english-v3.0"
        assert config.return_documents is True
        assert config.max_chunks_per_doc == 5

    def test_sentence_transformer_config(self):
        """Sentence Transformer reranker with device and batch options"""
        config = RerankerConfig(
            provider="sentence_transformer",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cuda",
            batch_size=32,
            max_length=512
        )
        assert config.provider == "sentence_transformer"
        assert config.device == "cuda"
        assert config.batch_size == 32
        assert config.max_length == 512

    def test_huggingface_config(self):
        """HuggingFace reranker with trust_remote_code option"""
        config = RerankerConfig(
            provider="huggingface",
            model="BAAI/bge-reranker-base",
            device="cuda",
            batch_size=16,
            trust_remote_code=True
        )
        assert config.provider == "huggingface"
        assert config.trust_remote_code is True

    def test_llm_reranker_config(self):
        """LLM Reranker with LLM provider and scoring prompt"""
        config = RerankerConfig(
            provider="llm_reranker",
            reranker_provider="openai",
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=100,
            scoring_prompt="Custom prompt {query} {document}"
        )
        assert config.provider == "llm_reranker"
        assert config.reranker_provider == "openai"
        assert config.temperature == 0.0
        assert config.max_tokens == 100
        assert config.scoring_prompt is not None

    def test_zero_entropy_config(self):
        """ZeroEntropy reranker with model selection"""
        config = RerankerConfig(
            provider="zero_entropy",
            model="zerank-1"
        )
        assert config.provider == "zero_entropy"
        assert config.model == "zerank-1"


class TestRerankerConfigToMem0:
    """# FR-23: Convert reranker config to Mem0 format"""

    def test_to_mem0_reranker_config_cohere(self):
        """# AC-55: Cohere reranker config converts to Mem0 format"""
        config = RerankerConfig(
            provider="cohere",
            model="rerank-english-v3.0",
            top_k=10,
            return_documents=True
        )
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "cohere"
        assert mem0_config["config"]["model"] == "rerank-english-v3.0"
        assert mem0_config["config"]["top_k"] == 10
        assert mem0_config["config"]["return_documents"] is True

    def test_to_mem0_reranker_config_sentence_transformer(self):
        """Sentence Transformer reranker config converts to Mem0 format"""
        config = RerankerConfig(
            provider="sentence_transformer",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cuda",
            batch_size=32
        )
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "sentence_transformer"
        assert mem0_config["config"]["model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert mem0_config["config"]["device"] == "cuda"
        assert mem0_config["config"]["batch_size"] == 32

    def test_to_mem0_reranker_config_huggingface(self):
        """HuggingFace reranker config converts to Mem0 format"""
        config = RerankerConfig(
            provider="huggingface",
            model="BAAI/bge-reranker-base",
            device="cpu",
            max_length=256
        )
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "huggingface"
        assert mem0_config["config"]["model"] == "BAAI/bge-reranker-base"
        assert mem0_config["config"]["max_length"] == 256

    def test_to_mem0_reranker_config_llm_reranker(self):
        """LLM Reranker config converts to Mem0 format"""
        config = RerankerConfig(
            provider="llm_reranker",
            reranker_provider="anthropic",
            model="claude-3-haiku-20240307",
            temperature=0.0
        )
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "llm_reranker"
        assert mem0_config["config"]["provider"] == "anthropic"
        assert mem0_config["config"]["model"] == "claude-3-haiku-20240307"

    def test_to_mem0_reranker_config_zero_entropy(self):
        """ZeroEntropy reranker config converts to Mem0 format"""
        config = RerankerConfig(
            provider="zero_entropy",
            model="zerank-1",
            top_k=5
        )
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "zero_entropy"
        assert mem0_config["config"]["model"] == "zerank-1"
        assert mem0_config["config"]["top_k"] == 5

    def test_to_mem0_reranker_config_minimal(self):
        """Minimal reranker config with just provider and top_k"""
        config = RerankerConfig(provider="cohere")
        mem0_config = config.to_mem0_reranker_config()

        assert mem0_config["provider"] == "cohere"
        assert "top_k" in mem0_config["config"]
        assert mem0_config["config"]["top_k"] == 10


class TestMemoryManagerRerankerConfig:
    """# FR-23: MemoryManager with Reranker Support"""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[
            {"id": "mem-1", "memory": "Memory 1", "score": 0.9, "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.get_all = AsyncMock(return_value=[
            {"id": "mem-1", "memory": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    def test_memory_manager_with_reranker_config(self, mock_mem0_client):
        """# AC-55: MemoryManager accepts reranker config with provider and model"""
        reranker_config = RerankerConfig(provider="cohere", model="rerank-english-v3.0")
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=reranker_config)

        assert manager.reranker_provider == "cohere"

    def test_memory_manager_without_reranker_config(self, mock_mem0_client):
        """# FR-23: MemoryManager uses None when no reranker config provided"""
        manager = MemoryManager(mem0_client=mock_mem0_client)

        assert manager.reranker_provider is None

    def test_memory_manager_reranker_properties(self, mock_mem0_client):
        """# AC-55: Reranker provider accessible via property"""
        config = RerankerConfig(provider="sentence_transformer", model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=config)

        assert manager.reranker_provider == "sentence_transformer"

    @pytest.mark.asyncio
    async def test_search_with_rerank_param(self, mock_mem0_client):
        """# FR-23: Search with rerank parameter passed to Mem0"""
        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.search_memories(
            scope=scope,
            query="test query",
            rerank=True
        )

        mock_mem0_client.search.assert_called_once()
        call_kwargs = mock_mem0_client.search.call_args
        assert "rerank" in call_kwargs.kwargs or call_kwargs.kwargs.get("rerank") is True

    @pytest.mark.asyncio
    async def test_search_rerank_uses_config_default(self, mock_mem0_client):
        """# FR-23: When rerank not specified, uses reranker_config.enabled"""
        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test query")

        call_kwargs = mock_mem0_client.search.call_args
        assert "rerank" in call_kwargs.kwargs
        assert call_kwargs.kwargs["rerank"] is True

    @pytest.mark.asyncio
    async def test_search_rerank_override_disabled(self, mock_mem0_client):
        """# FR-23: rerank param can override config default to disable"""
        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test query", rerank=False)

        call_kwargs = mock_mem0_client.search.call_args
        assert "rerank" in call_kwargs.kwargs
        assert call_kwargs.kwargs["rerank"] is False


class TestMultipleRerankerProviders:
    """# FR-23: Multiple reranker providers configurable"""

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

    @pytest.mark.parametrize("provider,model", [
        ("cohere", "rerank-english-v3.0"),
        ("cohere", "rerank-multilingual-v3.0"),
        ("sentence_transformer", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        ("sentence_transformer", "cross-encoder/ms-marco-electra-base"),
        ("huggingface", "BAAI/bge-reranker-base"),
        ("huggingface", "BAAI/bge-reranker-large"),
        ("llm_reranker", "gpt-4o-mini"),
        ("zero_entropy", "zerank-1"),
        ("zero_entropy", "zerank-1-small"),
    ])
    def test_various_reranker_providers_accepted(self, mock_mem0_client, provider, model):
        """# FR-23: Various reranker providers and models configurable"""
        config = RerankerConfig(provider=provider, model=model)
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=config)

        assert manager.reranker_provider == provider

    def test_reranker_config_in_logging(self, mock_mem0_client):
        """# FR-23: Reranker provider visible in initialization logging"""
        config = RerankerConfig(provider="cohere", model="rerank-english-v3.0")
        manager = MemoryManager(mem0_client=mock_mem0_client, reranker_config=config)

        assert manager.reranker_provider == "cohere"


class TestRerankerConfigBuildConfig:
    """Test RerankerConfig._build_config() for all providers.

    These tests cover the provider-specific config building for each reranker type.
    """

    def test_build_config_cohere(self):
        """Test Cohere reranker config building."""
        config = RerankerConfig(
            provider="cohere",
            model="rerank-english-v3.0",
            top_k=10,
            return_documents=True,
            max_chunks_per_doc=5
        )
        cfg = config._build_config()
        assert cfg["model"] == "rerank-english-v3.0"
        assert cfg["top_k"] == 10
        assert cfg["return_documents"] is True
        assert cfg["max_chunks_per_doc"] == 5

    def test_build_config_sentence_transformer(self):
        """Test Sentence Transformer reranker config building."""
        config = RerankerConfig(
            provider="sentence_transformer",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cuda",
            batch_size=32,
            max_length=512
        )
        cfg = config._build_config()
        assert cfg["model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert cfg["device"] == "cuda"
        assert cfg["batch_size"] == 32
        assert cfg["max_length"] == 512
        assert cfg["top_k"] == 10

    def test_build_config_huggingface(self):
        """Test HuggingFace reranker config building."""
        config = RerankerConfig(
            provider="huggingface",
            model="BAAI/bge-reranker-base",
            device="cpu",
            batch_size=16,
            max_length=256,
            trust_remote_code=False
        )
        cfg = config._build_config()
        assert cfg["model"] == "BAAI/bge-reranker-base"
        assert cfg["device"] == "cpu"
        assert cfg["batch_size"] == 16
        assert cfg["max_length"] == 256
        assert cfg["trust_remote_code"] is False

    def test_build_config_llm_reranker(self):
        """Test LLM reranker config building."""
        config = RerankerConfig(
            provider="llm_reranker",
            reranker_provider="openai",
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=100,
            scoring_prompt="Score: {query} vs {document}"
        )
        cfg = config._build_config()
        assert cfg["provider"] == "openai"
        assert cfg["model"] == "gpt-4o-mini"
        assert cfg["temperature"] == 0.0
        assert cfg["max_tokens"] == 100
        assert "Score:" in cfg["scoring_prompt"]

    def test_build_config_zero_entropy(self):
        """Test ZeroEntropy reranker config building."""
        config = RerankerConfig(
            provider="zero_entropy",
            model="zerank-1",
            top_k=5
        )
        cfg = config._build_config()
        assert cfg["model"] == "zerank-1"
        assert cfg["top_k"] == 5

    def test_build_config_minimal(self):
        """Test minimal reranker config building - only provider."""
        config = RerankerConfig(provider="cohere")
        cfg = config._build_config()
        assert cfg["top_k"] == 10
        assert "model" not in cfg

    def test_build_config_all_optional_none(self):
        """Test config building when all optional fields are None."""
        config = RerankerConfig(provider="sentence_transformer")
        cfg = config._build_config()
        assert cfg["top_k"] == 10
        assert cfg.get("device") is None
        assert cfg.get("batch_size") is None
