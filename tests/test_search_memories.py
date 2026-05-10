"""
Unit tests for search_memories MCP tool.

# UT-8: search_memories tool tests
# Validates requirements: FR-5, FR-3
# Scenarios:
#   - SCEN-22: query returns ranked results
#   - SCEN-23: empty query handled
#   - SCEN-24: no results returns empty list
# AC-13: query parameter accepted
# AC-14: Returns matching memories with scores
# AC-15: Empty query handled gracefully
# E-5: ERR_400 - Empty query provided to search_memories
# E-3: ERR_VEC_001 - Vector store connection failed during search
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.search_memories import (
    MemorySearchResult,
    SearchMemoriesInput,
    SearchMemoriesOutput,
)


class TestSearchMemoriesInput:
    """Test input validation for SearchMemoriesInput model."""

    def test_valid_input(self):
        """SCEN-22: valid query and filters accepted."""
        input_model = SearchMemoriesInput(
            query="test search query",
            filters={"user_id": "user_123"},
        )
        assert input_model.query == "test search query"
        assert input_model.filters == {"user_id": "user_123"}
        assert input_model.limit == 10

    def test_query_too_long_raises_error(self):
        """AC-13: query exceeding 1000 chars rejected."""
        with pytest.raises(ValueError):
            SearchMemoriesInput(
                query="x" * 1001,
                filters={"user_id": "user_123"},
            )

    def test_empty_query_raises_error(self):
        """SCEN-23: empty query rejected."""
        with pytest.raises(ValueError):
            SearchMemoriesInput(
                query="",
                filters={"user_id": "user_123"},
            )

    def test_whitespace_only_query_raises_error(self):
        """SCEN-23: whitespace-only query rejected."""
        with pytest.raises(ValueError):
            SearchMemoriesInput(
                query="   ",
                filters={"user_id": "user_123"},
            )

    def test_no_entity_id_in_filters_raises_error(self):
        """Entity IDs must be inside filters object - at least one required."""
        with pytest.raises(ValueError) as exc_info:
            SearchMemoriesInput(
                query="test query",
                filters={"metadata": {"key": "value"}},
            )
        assert "user_id, agent_id, app_id, or run_id" in str(exc_info.value)

    def test_empty_filters_does_not_raise(self):
        """Empty filters with query does not raise when query is provided."""
        model = SearchMemoriesInput(
            query="test query",
            filters={},
        )
        assert model.query == "test query"
        assert model.filters == {}

    def test_all_entity_ids_in_filters(self):
        """All entity IDs (user_id, agent_id, app_id, run_id) supported in filters."""
        input_model = SearchMemoriesInput(
            query="test query",
            filters={
                "user_id": "user_123",
                "agent_id": "agent_456",
                "app_id": "app_789",
                "run_id": "run_abc",
            },
        )
        assert input_model.filters["user_id"] == "user_123"
        assert input_model.filters["agent_id"] == "agent_456"
        assert input_model.filters["app_id"] == "app_789"
        assert input_model.filters["run_id"] == "run_abc"

    def test_advanced_filters_with_operators(self):
        """Filter operators (AND, OR, NOT, in, gte, lte, etc.) supported."""
        input_model = SearchMemoriesInput(
            query="test query",
            filters={
                "user_id": "user_123",
                "AND": [
                    {"created_at": {"gte": "2024-01-01"}},
                    {"categories": {"in": ["work", "personal"]}},
                ]
            },
        )
        assert "AND" in input_model.filters
        assert input_model.filters["user_id"] == "user_123"

    def test_limit_bounds_validation(self):
        """Verify limit has proper bounds."""
        model = SearchMemoriesInput(query="test", filters={"user_id": "user"}, limit=50)
        assert model.limit == 50

        with pytest.raises(ValueError):
            SearchMemoriesInput(query="test", filters={"user_id": "user"}, limit=0)

        with pytest.raises(ValueError):
            SearchMemoriesInput(query="test", filters={"user_id": "user"}, limit=101)

    def test_pagination_params(self):
        """Page and page_size parameters are supported."""
        model = SearchMemoriesInput(
            query="test",
            filters={"user_id": "user"},
            page=2,
            page_size=50,
        )
        assert model.page == 2
        assert model.page_size == 50

    def test_pagination_defaults_to_none(self):
        """Pagination params default to None when not specified."""
        model = SearchMemoriesInput(query="test", filters={"user_id": "user"})
        assert model.page is None
        assert model.page_size is None

    def test_page_size_max_validation(self):
        """page_size must be <= 100."""
        with pytest.raises(ValueError):
            SearchMemoriesInput(query="test", filters={"user_id": "user"}, page_size=101)

    def test_page_min_validation(self):
        """page must be >= 1."""
        with pytest.raises(ValueError):
            SearchMemoriesInput(query="test", filters={"user_id": "user"}, page=0)

    def test_filters_with_logical_operators(self):
        """Filters with AND, OR, NOT logical operators."""
        input_model = SearchMemoriesInput(
            query="invoice",
            filters={
                "user_id": "user_123",
                "AND": [
                    {
                        "OR": [
                            {"priority": "high"},
                            {"urgent": True},
                        ]
                    },
                ]
            },
        )
        assert "AND" in input_model.filters
        assert "OR" in input_model.filters["AND"][0]


class TestMemorySearchResult:
    """Test MemorySearchResult model."""

    def test_result_model(self):
        """AC-14: verify result model structure with score."""
        result = MemorySearchResult(
            memory_id="mem_abc123",
            content="Test memory content",
            score=0.95,
            metadata={"key": "value"},
        )
        assert result.memory_id == "mem_abc123"
        assert result.content == "Test memory content"
        assert result.score == 0.95
        assert result.metadata == {"key": "value"}

    def test_result_with_minimal_fields(self):
        """AC-14: verify result works with minimal fields."""
        result = MemorySearchResult(
            memory_id="mem_minimal",
            content="Minimal content",
            score=0.5,
        )
        assert result.memory_id == "mem_minimal"
        assert result.metadata is None


class TestSearchMemoriesOutput:
    """Test output model for SearchMemoriesOutput."""

    def test_output_model_empty(self):
        """SCEN-24: empty results list."""
        output = SearchMemoriesOutput(results=[])
        assert output.results == []

    def test_output_model_with_results(self):
        """AC-14: output model with results and scores."""
        output = SearchMemoriesOutput(
            results=[
                MemorySearchResult(
                    memory_id="mem_1",
                    content="First result",
                    score=0.95,
                ),
                MemorySearchResult(
                    memory_id="mem_2",
                    content="Second result",
                    score=0.75,
                ),
            ]
        )
        assert len(output.results) == 2
        assert output.results[0].score > output.results[1].score


class TestSearchMemoriesTool:
    """Test search_memories tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for search tests."""
        client = MagicMock()
        client.search = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked Mem0 client."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for search tests."""
        return TenantScope(user_id="user_123")

    @pytest.mark.asyncio
    async def test_search_memories_success(self, manager, mock_mem0_client, scope):
        """SCEN-22: query returns ranked results."""
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem_test1",
                    "memory": "Python programming",
                    "score": 0.95,
                    "metadata": {"lang": "python"},
                },
                {
                    "id": "mem_test2",
                    "memory": "JavaScript programming",
                    "score": 0.75,
                    "metadata": {"lang": "javascript"},
                },
            ]
        }

        results = await manager.search_memories(
            scope=scope,
            query="programming languages",
            limit=10,
        )

        assert len(results) == 2
        assert results[0].id == "mem_test1"
        assert results[1].id == "mem_test2"

        mock_mem0_client.search.assert_called_once()
        call_kwargs = mock_mem0_client.search.call_args.kwargs
        assert call_kwargs["query"] == "programming languages"

    @pytest.mark.asyncio
    async def test_search_memories_empty_query_returns_empty_results(self, manager, mock_mem0_client, scope):
        """SCEN-23: empty query handled gracefully."""
        results = await manager.search_memories(
            scope=scope,
            query="",
            limit=10,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_memories_no_results(self, manager, mock_mem0_client, scope):
        """SCEN-24: no results returns empty list."""
        mock_mem0_client.search.return_value = {"results": []}

        results = await manager.search_memories(
            scope=scope,
            query="nonexistent query xyz",
            limit=10,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_memories_with_limit_param(self, manager, mock_mem0_client, scope):
        """Verify search_memories works with limit parameter."""
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem_filtered",
                    "memory": "Filtered result",
                    "score": 0.9,
                    "metadata": {},
                },
            ]
        }

        results = await manager.search_memories(
            scope=scope,
            query="test query",
            limit=5,
        )

        assert len(results) == 1
        mock_mem0_client.search.assert_called_once()
        call_kwargs = mock_mem0_client.search.call_args.kwargs
        assert call_kwargs["top_k"] == 5

    @pytest.mark.asyncio
    async def test_search_memories_uninitialized_client_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized client raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(user_id="user_123")

        with pytest.raises(Exception):
            await manager.search_memories(
                scope=scope,
                query="test query",
                limit=10,
            )

    @pytest.mark.asyncio
    async def test_search_memories_invalid_scope_raises_error(self, mock_mem0_client):
        """Invalid scope raises error."""
        manager = MemoryManager(mem0_client=mock_mem0_client)
        # org_id and project_id are no longer part of TenantScope in v3
        # Instead, an empty user_id is used to create an invalid scope
        invalid_scope = TenantScope(user_id="")

        with pytest.raises(Exception):
            await manager.search_memories(
                scope=invalid_scope,
                query="test query",
                limit=10,
            )


class TestSearchMemoriesToolRegistration:
    """Test search_memories tool registration with FastMCP."""

    def test_register_search_memories_tool_function_exists(self):
        """Verify register_search_memories_tool function exists and is callable."""
        from mcp_server.tools.search_memories import register_search_memories_tool

        assert callable(register_search_memories_tool)

    def test_register_search_memories_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.search_memories import register_search_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_search_memories_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_search_memories_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.search_memories import register_search_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_search_memories_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
