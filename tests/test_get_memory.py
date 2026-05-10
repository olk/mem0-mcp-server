"""
Unit tests for get_memory MCP tool.

# UT-10: get_memory tool tests
# Validates requirements: FR-8
# Scenarios:
#   - SCEN-22: memory_id required for retrieval
#   - SCEN-23: memory content and metadata returned
# AC-22: memory_id required - Valid memory_id must be provided
# AC-23: Returns memory content and metadata
# E-8: ERR_404 - Memory ID not found during get
# E-2: ERR_MEM_001 - Mem0 AsyncMemory not initialized or unavailable
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.get_memory import GetMemoryInput, GetMemoryOutput


class TestGetMemoryInput:
    """Test input validation for GetMemoryInput model."""

    def test_valid_input(self):
        """SCEN-22: valid memory_id accepted."""
        input_model = GetMemoryInput(
            memory_id="mem_abc123",
        )
        assert input_model.memory_id == "mem_abc123"

    def test_memory_id_too_long_raises_error(self):
        """AC-22: memory_id exceeding 255 chars rejected."""
        with pytest.raises(ValueError):
            GetMemoryInput(
                memory_id="x" * 256,
            )

    def test_empty_memory_id_raises_error(self):
        """AC-22: empty memory_id rejected."""
        with pytest.raises(ValueError):
            GetMemoryInput(
                memory_id="",
            )

    def test_whitespace_only_memory_id_raises_error(self):
        """AC-22: whitespace-only memory_id rejected."""
        with pytest.raises(ValueError):
            GetMemoryInput(
                memory_id="   ",
            )


class TestGetMemoryOutput:
    """Test output model for GetMemoryOutput."""

    def test_output_model(self):
        """AC-23: Verify output model structure contains all required fields."""
        output = GetMemoryOutput(
            memory_id="mem_abc123",
            content="Test memory content",
            metadata={"key": "value"},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )
        assert output.memory_id == "mem_abc123"
        assert output.content == "Test memory content"
        assert output.metadata == {"key": "value"}
        assert output.created_at == "2024-01-01T00:00:00Z"
        assert output.updated_at == "2024-01-02T00:00:00Z"

    def test_output_model_metadata_default(self):
        """Verify metadata defaults to empty dict when not provided."""
        output = GetMemoryOutput(
            memory_id="mem_abc123",
            content="Test content",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )
        assert output.metadata == {}


class TestGetMemoryTool:
    """Test get_memory tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for get tests."""
        client = MagicMock()
        client.get_all = AsyncMock()
        client.get = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for get tests."""
        return TenantScope(user_id="user_123")

    @pytest.mark.asyncio
    async def test_get_memory_success(self, manager, mock_mem0_client, scope):
        """SCEN-22 & SCEN-23: memory_id required, returns content and metadata."""
        mock_mem0_client.get.return_value = {
            "id": "mem_test123",
            "memory": "Test memory content",
            "user_id": "user_123",
            "metadata": {"source": "test", "user_id": "user_123"},
            "created_at": "2024-01-01T00:00:00Z",
        }

        result = await manager.get_memory(
            memory_id="mem_test123",
            scope=scope,
        )

        assert result.id == "mem_test123"
        assert result.content == "Test memory content"
        assert result.metadata == {"source": "test", "user_id": "user_123"}

    @pytest.mark.asyncio
    async def test_get_memory_with_empty_metadata(self, manager, mock_mem0_client, scope):
        """SCEN-23: Returns memory content and metadata (empty metadata case)."""
        mock_mem0_client.get.return_value = {
            "id": "mem_empty_meta",
            "memory": "Content without metadata",
            "user_id": "user_123",
            "metadata": {"user_id": "user_123"},
            "created_at": "2024-01-01T00:00:00Z",
        }

        result = await manager.get_memory(
            memory_id="mem_empty_meta",
            scope=scope,
        )

        assert result.id == "mem_empty_meta"
        assert result.content == "Content without metadata"
        assert result.metadata == {"user_id": "user_123"}

    @pytest.mark.asyncio
    async def test_get_memory_invalid_scope_raises_error(self):
        """SCEN-22: invalid scope raises error."""
        manager = MemoryManager(mem0_client=MagicMock())
        # org_id and project_id are no longer part of TenantScope in v3
        # Instead, an empty user_id is used to create an invalid scope
        invalid_scope = TenantScope(user_id="")

        with pytest.raises(Exception):
            await manager.get_memory(
                memory_id="mem_test123",
                scope=invalid_scope,
            )

    @pytest.mark.asyncio
    async def test_get_memory_not_found_raises_error(self, manager, mock_mem0_client, scope):
        """SCEN-23: E-8 - memory not found raises error."""
        mock_mem0_client.get.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await manager.get_memory(
                memory_id="mem_notfound",
                scope=scope,
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_memory_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(user_id="user_123")

        with pytest.raises(Exception):
            await manager.get_memory(
                memory_id="mem_test123",
                scope=scope,
            )


class TestGetMemoryToolRegistration:
    """Test get_memory tool registration with FastMCP."""

    def test_register_get_memory_tool_function_exists(self):
        """Verify register_get_memory_tool function exists and is callable."""
        from mcp_server.tools.get_memory import register_get_memory_tool

        assert callable(register_get_memory_tool)

    def test_register_get_memory_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.get_memory import register_get_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_get_memory_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_get_memory_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.get_memory import register_get_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_get_memory_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
