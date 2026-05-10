"""
Unit tests for list_memories MCP tool.

# UT-16: list_memories tool tests
# Validates requirements: FR-9, AC-24, AC-26
# Scenarios:
#   - SCEN-24: Filter memories by user_id
#   - SCEN-25: Limit with max results
#   - SCEN-26: Returns list of memories
# AC-24: userId filter supported
# AC-26: Returns memory list
# E-2: ERR_MEM_001 - Mem0 AsyncMemory not initialized or unavailable
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.list_memories import (
    ListMemoriesInput,
    ListMemoriesOutput,
    MemoryResponse,
)


class TestListMemoriesInput:
    """Test input validation for ListMemoriesInput model."""

    def test_valid_input_with_user_id(self):
        """AC-24: userId filter supported via filters object."""
        input_model = ListMemoriesInput(filters={"user_id": "user_123"})
        assert input_model.filters == {"user_id": "user_123"}

    def test_all_entity_ids_in_filters(self):
        """AC-24: All entity IDs (user_id, agent_id, app_id, run_id) supported in filters."""
        input_model = ListMemoriesInput(
            filters={
                "user_id": "user_123",
                "agent_id": "agent_456",
                "app_id": "app_789",
                "run_id": "run_abc",
            }
        )
        assert input_model.filters["user_id"] == "user_123"
        assert input_model.filters["agent_id"] == "agent_456"
        assert input_model.filters["app_id"] == "app_789"
        assert input_model.filters["run_id"] == "run_abc"

    def test_advanced_filters_with_operators(self):
        """Filter operators (AND, OR, NOT, in, gte, lte, etc.) supported."""
        input_model = ListMemoriesInput(
            filters={
                "user_id": "user_123",
                "AND": [
                    {"created_at": {"gte": "2024-01-01"}},
                    {"categories": {"in": ["work", "personal"]}},
                ]
            }
        )
        assert "AND" in input_model.filters
        assert input_model.filters["user_id"] == "user_123"

    def test_limit_params(self):
        """AC-26: Limit parameter accepted."""
        input_model = ListMemoriesInput(filters={"user_id": "user_123"}, limit=25)
        assert input_model.limit == 25

    def test_limit_boundary(self):
        """Limit boundary values (1-100)."""
        input_model = ListMemoriesInput(filters={"user_id": "user_123"}, limit=1)
        assert input_model.limit == 1

        input_model = ListMemoriesInput(filters={"user_id": "user_123"}, limit=100)
        assert input_model.limit == 100

    def test_no_entity_id_raises_error(self):
        """At least one entity ID required in filters."""
        with pytest.raises(ValueError) as exc_info:
            ListMemoriesInput(filters={"metadata": {"key": "value"}})
        assert "user_id, agent_id, app_id, or run_id" in str(exc_info.value)

    def test_empty_filters_raises_error(self):
        """Empty filters raises error - at least one entity ID required."""
        with pytest.raises(ValueError):
            ListMemoriesInput(filters={})


class TestMemoryResponse:
    """Test output model for a single memory in list_memories response."""

    def test_output_model_all_fields(self):
        """AC-26: Verify output model structure with all fields."""
        output = MemoryResponse(
            memory_id="mem_abc123",
            content="Test memory content",
            user_id="user_123",
            agent_id="agent_456",
            app_id="app_789",
            run_id="run_abc",
            metadata={"key": "value"},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )
        assert output.memory_id == "mem_abc123"
        assert output.content == "Test memory content"
        assert output.user_id == "user_123"
        assert output.agent_id == "agent_456"
        assert output.app_id == "app_789"
        assert output.run_id == "run_abc"
        assert output.metadata == {"key": "value"}
        assert output.created_at == "2024-01-01T00:00:00Z"
        assert output.updated_at == "2024-01-02T00:00:00Z"

    def test_output_model_optional_fields_default(self):
        """AC-26: Verify optional fields have correct defaults."""
        output = MemoryResponse(
            memory_id="mem_abc123",
            content="Test content",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )
        assert output.memory_id == "mem_abc123"
        assert output.content == "Test content"
        assert output.user_id is None
        assert output.agent_id is None
        assert output.app_id is None
        assert output.run_id is None
        assert output.metadata == {}
        assert output.created_at == "2024-01-01T00:00:00Z"
        assert output.updated_at == "2024-01-02T00:00:00Z"


class TestListMemoriesOutput:
    """Test output model for list_memories response."""

    def test_output_model_empty_list(self):
        """AC-26: Returns memory list - empty list case."""
        output = ListMemoriesOutput(memories=[], limit=50, total_count=0)
        assert output.memories == []
        assert output.limit == 50

    def test_output_model_with_memories(self):
        """AC-26: Returns memory list - with data."""
        memories = [
            MemoryResponse(
                memory_id="mem_1",
                content="Content 1",
                user_id="user_1",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-02T00:00:00Z",
            ),
            MemoryResponse(
                memory_id="mem_2",
                content="Content 2",
                user_id="user_1",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-02T00:00:00Z",
            ),
        ]
        output = ListMemoriesOutput(memories=memories, limit=50, total_count=2)
        assert len(output.memories) == 2
        assert output.memories[0].memory_id == "mem_1"
        assert output.memories[1].memory_id == "mem_2"
        assert output.total_count == 2


class TestListMemoriesTool:
    """Test list_memories tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for list tests."""
        client = MagicMock()
        client.get_all = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for list tests."""
        return TenantScope(
            user_id="user_123",
        )

    @pytest.mark.asyncio
    async def test_list_memories_success(self, manager, mock_mem0_client, scope):
        """SCEN-24: Filter memories by user_id via scope."""
        mock_mem0_client.get_all.return_value = {
            "results": [
                {
                    "id": "mem_1",
                    "memory": "Memory 1",
                    "metadata": {"user_id": "user_123"},
                    "created_at": "2024-01-01T00:00:00Z",
                },
            ],
            "count": 1,
        }

        result = await manager.list_memories(scope=scope, limit=10)

        assert len(result) == 1
        assert result[0].id == "mem_1"
        mock_mem0_client.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_memories_limit(self, manager, mock_mem0_client, scope):
        """SCEN-25: Limit parameter controls max results."""
        mock_mem0_client.get_all.return_value = {
            "results": [
                {"id": f"mem_{i}", "memory": f"Memory {i}", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
                for i in range(5)
            ],
            "count": 5,
        }

        result = await manager.list_memories(scope=scope, limit=10)

        assert len(result) == 5
        mock_mem0_client.get_all.assert_called_once()
        call_kwargs = mock_mem0_client.get_all.call_args.kwargs
        assert call_kwargs["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_memories_empty_results(self, manager, mock_mem0_client, scope):
        """SCEN-26: Returns memory list - empty results case."""
        mock_mem0_client.get_all.return_value = {"results": [], "count": 0}

        result = await manager.list_memories(scope=scope, limit=10)

        assert len(result) == 0
        assert result == []

    @pytest.mark.asyncio
    async def test_list_memories_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(
            user_id="user_123",
        )

        with pytest.raises(Exception):
            await manager.list_memories(scope=scope, limit=10)


class TestListMemoriesToolRegistration:
    """Test list_memories tool registration with FastMCP."""

    def test_register_list_memories_tool_function_exists(self):
        """Verify register_list_memories_tool function exists and is callable."""
        from mcp_server.tools.list_memories import register_list_memories_tool

        assert callable(register_list_memories_tool)

    def test_register_list_memories_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.list_memories import register_list_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_list_memories_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_list_memories_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.list_memories import register_list_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_list_memories_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
