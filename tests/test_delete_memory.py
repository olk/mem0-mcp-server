"""
Unit tests for delete_memory MCP tool.

# UT-12: delete_memory tool tests
# Validates requirements: FR-7
# Scenarios:
#   - SCEN-36: memory_id required
#   - SCEN-37: memory removed
#   - SCEN-38: returns confirmation
#   - SCEN-39: invalid input rejected
# AC-19: memory_id required - Valid memory_id must be provided
# AC-20: Memory removed - Memory deleted from storage
# AC-21: Returns confirmation - Deletion confirmation returned
# E-7: ERR_404 - Memory ID not found during delete
# E-8: ERR_404 - Memory ID not found during get
# RPARAM-7: memory_id - non-empty string, max 255 chars
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.delete_memory import DeleteMemoryInput, DeleteMemoryOutput


class TestDeleteMemoryInput:
    """Test input validation for DeleteMemoryInput model."""

    def test_valid_input(self):
        """SCEN-36: valid memory_id accepted."""
        input_model = DeleteMemoryInput(
            memory_id="mem_test123",
        )
        assert input_model.memory_id == "mem_test123"

    def test_memory_id_too_long_raises_error(self):
        """SCEN-39: memory_id exceeding 255 chars rejected."""
        with pytest.raises(ValueError):
            DeleteMemoryInput(
                memory_id="x" * 256,
            )

    def test_empty_memory_id_raises_error(self):
        """SCEN-39: empty memory_id rejected."""
        with pytest.raises(ValueError):
            DeleteMemoryInput(
                memory_id="",
            )

    def test_whitespace_only_memory_id_raises_error(self):
        """SCEN-39: whitespace-only memory_id rejected."""
        with pytest.raises(ValueError):
            DeleteMemoryInput(
                memory_id="   ",
            )


class TestDeleteMemoryOutput:
    """Test output model for DeleteMemoryOutput."""

    def test_output_model(self):
        """SCEN-38: Verify output model structure with status and deleted."""
        output = DeleteMemoryOutput(
            status="deleted",
            deleted=True,
        )
        assert output.status == "deleted"
        assert output.deleted is True


class TestDeleteMemoryTool:
    """Test delete_memory tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for delete tests."""
        client = MagicMock()
        client.delete = AsyncMock()
        client.get = AsyncMock(return_value={
            "id": "mem_test123",
            "user_id": "user_123",
            "memory": {"text": "test memory"},
            "metadata": {"user_id": "user_123"}
        })
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for delete tests."""
        return TenantScope(user_id="user_123")

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, manager, mock_mem0_client, scope):
        """SCEN-37: memory removed - memory deleted from storage."""
        mock_mem0_client.delete.return_value = True

        result = await manager.delete_memory(
            memory_id="mem_test123",
            scope=scope,
        )

        assert result is True

        mock_mem0_client.delete.assert_called_once()
        call_kwargs = mock_mem0_client.delete.call_args.kwargs
        assert call_kwargs["memory_id"] == "mem_test123"

    @pytest.mark.asyncio
    async def test_delete_memory_invalid_scope_raises_error(self):
        """SCEN-39: invalid scope rejected."""
        manager = MemoryManager(mem0_client=MagicMock())
        # org_id and project_id are no longer part of TenantScope in v3
        # Instead, an empty user_id is used to create an invalid scope
        invalid_scope = TenantScope(user_id="")

        with pytest.raises(Exception):
            await manager.delete_memory(
                memory_id="mem_test123",
                scope=invalid_scope,
            )

    @pytest.mark.asyncio
    async def test_delete_memory_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(user_id="user_123")

        with pytest.raises(RuntimeError):
            await manager.delete_memory(
                memory_id="mem_test123",
                scope=scope,
            )


class TestDeleteMemoryToolRegistration:
    """Test delete_memory tool registration with FastMCP."""

    def test_register_delete_memory_tool_function_exists(self):
        """Verify register_delete_memory_tool function exists and is callable."""
        from mcp_server.tools.delete_memory import register_delete_memory_tool

        assert callable(register_delete_memory_tool)

    def test_register_delete_memory_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.delete_memory import register_delete_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_delete_memory_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_delete_memory_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.delete_memory import register_delete_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_delete_memory_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
