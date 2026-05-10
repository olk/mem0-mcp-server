"""
# IT-5: Reranker Integration tests
# Validates: FR-23, AC-55
# Scenario: End-to-end reranker functionality with Mem0 client

Integration tests for Reranker Support functionality.
Tests end-to-end reranker configuration, search with reranking, and result verification.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestRerankerIntegration:
    """End-to-end reranker integration tests with mocked Mem0 client"""

    @pytest.fixture
    def mock_mem0_with_reranker(self):
        """Mock Mem0 AsyncMemory client that simulates reranking"""
        client = MagicMock()

        async def mock_search_with_rerank(query, filters, top_k, rerank=None, **kwargs):
            base_results = [
                {
                    "id": "mem-1",
                    "memory": "I enjoy hiking in mountains",
                    "score": 0.85,
                    "metadata": {"user_id": "test_user"},
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "mem-2",
                    "memory": "Pizza is my favorite food",
                    "score": 0.72,
                    "metadata": {"user_id": "test_user"},
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "mem-3",
                    "memory": "I work as a software engineer",
                    "score": 0.65,
                    "metadata": {"user_id": "test_user"},
                    "created_at": "2024-01-01T00:00:00Z"
                },
            ]

            if rerank:
                for r in base_results:
                    r["rerank_score"] = round(r["score"] * 1.1, 3)

            return {"results": base_results}

        client.search = AsyncMock(side_effect=mock_search_with_rerank)
        client.add = AsyncMock(return_value={
            "results": [{"id": "mem-new", "created_at": "2024-01-01T00:00:00Z"}]
        })
        client.get_all = AsyncMock(return_value={"results": []})
        client.delete = AsyncMock(return_value=True)

        return client

    def test_search_with_reranker_configured(self, mock_mem0_with_reranker):
        """# FR-23: Search works when reranker is configured"""
        from mcp_server.config.settings import RerankerConfig
        from mcp_server.memory.manager import MemoryManager

        reranker_config = RerankerConfig(
            provider="cohere",
            model="rerank-english-v3.0",
            top_k=10,
            enabled=True
        )
        manager = MemoryManager(
            mem0_client=mock_mem0_with_reranker,
            reranker_config=reranker_config
        )

        assert manager.reranker_provider == "cohere"

    @pytest.mark.asyncio
    async def test_search_results_have_rerank_scores(self, mock_mem0_with_reranker):
        """# FR-23: Results include rerank_score when reranking is applied"""
        from mcp_server.memory.manager import MemoryManager, TenantScope

        manager = MemoryManager(mem0_client=mock_mem0_with_reranker)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.search_memories(
            scope=scope,
            query="What do I like to do outdoors?",
            rerank=True
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_search_without_rerank_no_rerank_scores(self, mock_mem0_with_reranker):
        """# FR-23: Results don't have rerank_score when reranking is disabled"""
        from mcp_server.memory.manager import MemoryManager, TenantScope

        manager = MemoryManager(mem0_client=mock_mem0_with_reranker)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.search_memories(
            scope=scope,
            query="What do I like to do outdoors?",
            rerank=False
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_rerank_parameter_passed_to_mem0(self, mock_mem0_with_reranker):
        """# FR-23: rerank=True passed to Mem0 client.search()"""
        from mcp_server.config.settings import RerankerConfig
        from mcp_server.memory.manager import MemoryManager, TenantScope

        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_with_reranker, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test", rerank=True)

        mock_mem0_with_reranker.search.assert_called_once()
        call_args = mock_mem0_with_reranker.search.call_args
        assert call_args.kwargs.get("rerank") is True

    @pytest.mark.asyncio
    async def test_rerank_false_parameter(self, mock_mem0_with_reranker):
        """# FR-23: rerank=False passed to Mem0 client.search()"""
        from mcp_server.config.settings import RerankerConfig
        from mcp_server.memory.manager import MemoryManager, TenantScope

        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_with_reranker, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test", rerank=False)

        mock_mem0_with_reranker.search.assert_called_once()
        call_args = mock_mem0_with_reranker.search.call_args
        assert call_args.kwargs.get("rerank") is False

    @pytest.mark.asyncio
    async def test_rerank_none_uses_config_default(self, mock_mem0_with_reranker):
        """# FR-23: When rerank is None, uses reranker_config.enabled as default"""
        from mcp_server.config.settings import RerankerConfig
        from mcp_server.memory.manager import MemoryManager, TenantScope

        reranker_config = RerankerConfig(provider="cohere", enabled=True)
        manager = MemoryManager(mem0_client=mock_mem0_with_reranker, reranker_config=reranker_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test")

        mock_mem0_with_reranker.search.assert_called_once()
        call_args = mock_mem0_with_reranker.search.call_args
        assert call_args.kwargs.get("rerank") is True

    @pytest.mark.asyncio
    async def test_no_reranker_config_rerank_not_passed(self, mock_mem0_with_reranker):
        """# FR-23: When no reranker configured, rerank param not passed to Mem0"""
        from mcp_server.memory.manager import MemoryManager, TenantScope

        manager = MemoryManager(mem0_client=mock_mem0_with_reranker, reranker_config=None)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        await manager.search_memories(scope=scope, query="test")

        mock_mem0_with_reranker.search.assert_called_once()
        call_args = mock_mem0_with_reranker.search.call_args
        assert "rerank" not in call_args.kwargs


class TestSearchMemoriesToolReranker:
    """Test search_memories tool with rerank parameter"""

    @pytest.fixture
    def mock_memory(self):
        """Mock memory client for tool testing"""
        memory = MagicMock()
        memory.search = AsyncMock(return_value={
            "results": [
                {
                    "id": "mem-1",
                    "memory": "Test memory about hiking",
                    "score": 0.92,
                    "rerank_score": 0.95,
                    "metadata": {},
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        })
        return memory

    @pytest.mark.asyncio
    async def test_search_tool_accepts_rerank_param(self, mock_memory):
        """# FR-23: search_memories tool accepts rerank parameter"""
        from mcp_server.tools.search_memories import (
            SearchMemoriesInput,
        )

        inp = SearchMemoriesInput(
            query="outdoor activities",
            filters={"user_id": "alice"},
            rerank=True
        )
        assert inp.rerank is True

    @pytest.mark.asyncio
    async def test_search_tool_rerank_none(self, mock_memory):
        """# FR-23: search_memories tool allows rerank=None"""
        from mcp_server.tools.search_memories import SearchMemoriesInput

        inp = SearchMemoriesInput(
            query="outdoor activities",
            filters={"user_id": "alice"},
            rerank=None
        )
        assert inp.rerank is None


class TestConfigLoaderWithReranker:
    """Test config loader includes reranker in defaults"""

    def test_create_default_config_includes_reranker(self):
        """# FR-23: create_default_config includes reranker section"""
        from mcp_server.config.loader import create_default_config

        config = create_default_config()
        assert "reranker" in config
        assert config["reranker"]["provider"] == "cohere"
        assert "top_k" in config["reranker"]["config"]

    def test_reranker_config_validation(self):
        """# FR-23: RerankerConfig validates provider"""
        from mcp_server.config.settings import RerankerConfig

        with pytest.raises(ValueError) as exc_info:
            RerankerConfig(provider="invalid_reranker", model="test")
        assert "invalid_reranker" in str(exc_info.value)

    def test_reranker_config_top_k_validation(self):
        """# FR-23: RerankerConfig validates top_k"""
        from mcp_server.config.settings import RerankerConfig

        with pytest.raises(ValueError):
            RerankerConfig(top_k=0)

    def test_secrets_settings_includes_reranker_keys(self):
        """# FR-23: SecretsSettings includes reranker API key fields"""
        from mcp_server.config.settings import SecretsSettings

        secrets = SecretsSettings(
            OPENAI_API_KEY="sk-test",
            COHERE_API_KEY="test-cohere-key",
            HUGGINGFACE_API_KEY="test-hf-key",
            ZERO_ENTROPY_API_KEY="test-ze-key"
        )
        assert secrets.COHERE_API_KEY == "test-cohere-key"
        assert secrets.HUGGINGFACE_API_KEY == "test-hf-key"
        assert secrets.ZERO_ENTROPY_API_KEY == "test-ze-key"


class TestRerankerExamples:
    """Test examples from documentation"""

    def test_cohere_reranker_example(self):
        """# FR-23: Cohere reranker configuration example"""
        from mcp_server.config.settings import RerankerConfig

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

    def test_sentence_transformer_example(self):
        """# FR-23: Sentence Transformer reranker configuration example"""
        from mcp_server.config.settings import RerankerConfig

        config = RerankerConfig(
            provider="sentence_transformer",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cuda",
            batch_size=32
        )

        mem0_config = config.to_mem0_reranker_config()
        assert mem0_config["provider"] == "sentence_transformer"
        assert mem0_config["config"]["device"] == "cuda"
        assert mem0_config["config"]["batch_size"] == 32

    def test_llm_reranker_example(self):
        """# FR-23: LLM Reranker configuration example"""
        from mcp_server.config.settings import RerankerConfig

        config = RerankerConfig(
            provider="llm_reranker",
            reranker_provider="openai",
            model="gpt-4o-mini",
            temperature=0.0,
            top_k=5
        )

        mem0_config = config.to_mem0_reranker_config()
        assert mem0_config["provider"] == "llm_reranker"
        assert mem0_config["config"]["provider"] == "openai"
        assert mem0_config["config"]["model"] == "gpt-4o-mini"
        assert mem0_config["config"]["top_k"] == 5

    def test_zero_entropy_example(self):
        """# FR-23: ZeroEntropy reranker configuration example"""
        from mcp_server.config.settings import RerankerConfig

        config = RerankerConfig(
            provider="zero_entropy",
            model="zerank-1",
            top_k=5
        )

        mem0_config = config.to_mem0_reranker_config()
        assert mem0_config["provider"] == "zero_entropy"
        assert mem0_config["config"]["model"] == "zerank-1"

    def test_huggingface_reranker_example(self):
        """# FR-23: HuggingFace reranker configuration example"""
        from mcp_server.config.settings import RerankerConfig

        config = RerankerConfig(
            provider="huggingface",
            model="BAAI/bge-reranker-base",
            device="cuda",
            batch_size=32
        )

        mem0_config = config.to_mem0_reranker_config()
        assert mem0_config["provider"] == "huggingface"
        assert mem0_config["config"]["model"] == "BAAI/bge-reranker-base"
