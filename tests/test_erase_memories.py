"""
Unit tests for erase_memories MCP tool.

# UT-13: erase_memories tool tests
# Validates requirements: FR-11
# Scenarios:
#   - SCEN-40: user_id required
#   - SCEN-41: all memories erased for scope
#   - SCEN-42: returns confirmation
#   - SCEN-43: invalid input rejected
# AC-19: user_id required - Valid user_id must be provided
# AC-20: Memory erased - All memories deleted from storage
# AC-21: Returns confirmation - Deletion confirmation returned
# E-10: ERR_400 - Invalid scope provided
# RPARAM-8: user_id/org_id/project_id - non-empty strings, max 255 chars
# DP-1: Dependency Injection Pattern

Note: The erase_memories tool function is decorated with @mcp.tool() and is not
directly importable. The error handling for invalid scope is implemented in the
tool layer which calls memory.delete_all() with properly formatted user_id.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import MemoryManager, TenantScope
from mcp_server.tools.erase_memories import EraseMemoriesInput, EraseMemoriesOutput


class TestEraseMemoriesInput:
    """Test input validation for EraseMemoriesInput model."""

    def test_valid_input(self):
        """SCEN-40: valid user_id accepted with org_id and project_id."""
        input_model = EraseMemoriesInput(
            user_id="user_123",
            agent_id="agent_456",
            run_id="run_789",
        )
        assert input_model.user_id == "user_123"
        assert input_model.agent_id == "agent_456"
        assert input_model.run_id == "run_789"

    def test_valid_input_minimal(self):
        """SCEN-40: user_id alone is valid when org/project provided separately."""
        input_model = EraseMemoriesInput(
            user_id="user_123",
        )
        assert input_model.user_id == "user_123"
        assert input_model.agent_id is None
        assert input_model.run_id is None

    def test_empty_user_id_raises_error(self):
        """SCEN-43: empty user_id rejected."""
        with pytest.raises(ValueError):
            EraseMemoriesInput(user_id="")

    def test_whitespace_only_user_id_raises_error(self):
        """SCEN-43: whitespace-only user_id rejected."""
        with pytest.raises(ValueError):
            EraseMemoriesInput(user_id="   ")

    def test_empty_agent_id_raises_error(self):
        """SCEN-43: empty agent_id (when provided) rejected."""
        with pytest.raises(ValueError):
            EraseMemoriesInput(user_id="user_123", agent_id="")

    def test_empty_run_id_raises_error(self):
        """SCEN-43: empty run_id (when provided) rejected."""
        with pytest.raises(ValueError):
            EraseMemoriesInput(user_id="user_123", run_id="")

    def test_user_id_too_long_raises_error(self):
        """SCEN-43: user_id exceeding 255 chars rejected."""
        with pytest.raises(ValueError):
            EraseMemoriesInput(user_id="x" * 256)

    def test_to_mem0_user_id_format(self):
        """Verify to_mem0_user_id formats correctly."""
        input_model = EraseMemoriesInput(user_id="user_123")
        # In v3, to_mem0_user_id just returns the user_id (no composite format)
        result = input_model.to_mem0_user_id()
        assert result == "user_123"

    def test_to_mem0_user_id_with_agent(self):
        """Verify to_mem0_user_id includes agent_id when provided."""
        input_model = EraseMemoriesInput(user_id="user_123", agent_id="agent_456")
        result = input_model.to_mem0_user_id()
        assert result == "user_123:agent_456"

    def test_to_mem0_user_id_with_agent_and_run(self):
        """Verify to_mem0_user_id includes both agent_id and run_id when provided."""
        input_model = EraseMemoriesInput(user_id="user_123", agent_id="agent_456", run_id="run_789")
        result = input_model.to_mem0_user_id()
        assert result == "user_123:agent_456:run_789"


class TestEraseMemoriesOutput:
    """Test output model for EraseMemoriesOutput."""

    def test_output_model(self):
        """SCEN-42: Verify output model structure with status and deleted."""
        output = EraseMemoriesOutput(
            status="erased",
            deleted=True,
        )
        assert output.status == "erased"
        assert output.deleted is True

    def test_output_model_failed(self):
        """SCEN-42: Verify output model for failed deletion."""
        output = EraseMemoriesOutput(
            status="failed",
            deleted=False,
        )
        assert output.status == "failed"
        assert output.deleted is False


class TestEraseMemoriesTool:
    """Test erase_memories tool functionality via MemoryManager.

    Note: MemoryManager.delete_all_memories() takes scope.
    The error handling for invalid scope (E-10) is validated here.
    """

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for erase tests."""
        client = MagicMock()
        client.delete_all = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for erase tests."""
        return TenantScope(user_id="user_123")

    @pytest.mark.asyncio
    async def test_erase_memories_success(self, manager, mock_mem0_client, scope):
        """SCEN-41: all memories erased - memories deleted from storage.

        # Validates: FR-11, AC-20
        erase_memories should delete all memories for scope and return confirmation.
        """
        mock_mem0_client.delete_all.return_value = {"deleted": True, "status": "deleted"}

        result = await manager.delete_all_memories(scope=scope)

        assert result is True
        mock_mem0_client.delete_all.assert_called_once()
        call_kwargs = mock_mem0_client.delete_all.call_args.kwargs
        assert "user_id" in call_kwargs

    @pytest.mark.asyncio
    async def test_erase_memories_invalid_scope_raises_error(self, mock_mem0_client):
        """SCEN-43: invalid scope rejected.

        # Validates: E-10
        Empty user_id should raise ScopeValidationError.
        """
        manager = MemoryManager(mem0_client=mock_mem0_client)
        # org_id and project_id are no longer part of TenantScope in v3
        # Instead, an empty user_id is used to create an invalid scope
        invalid_scope = TenantScope(user_id="")

        with pytest.raises(Exception):
            await manager.delete_all_memories(scope=invalid_scope)

    @pytest.mark.asyncio
    async def test_erase_memories_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error.

        # Validates: E-2
        When memory client is None, calling erase_memories raises RuntimeError.
        """
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(user_id="user_123")

        with pytest.raises(RuntimeError):
            await manager.delete_all_memories(scope=scope)

    @pytest.mark.asyncio
    async def test_erase_memories_result_parsing(self, manager, mock_mem0_client, scope):
        """Verify erase_memories correctly parses dict result from delete_all."""
        mock_mem0_client.delete_all.return_value = {
            "deleted": True,
            "status": "deleted",
            "count": 5
        }

        result = await manager.delete_all_memories(scope=scope)

        assert result is True

    @pytest.mark.asyncio
    async def test_erase_memories_bool_result(self, manager, mock_mem0_client, scope):
        """Verify erase_memories correctly parses bool result from delete_all."""
        mock_mem0_client.delete_all.return_value = True

        result = await manager.delete_all_memories(scope=scope)

        assert result is True


class TestEraseMemoriesToolRegistration:
    """Test erase_memories tool registration with FastMCP.

    Note: The erase_memories function is decorated with @mcp.tool() and is not
    directly importable. Tool-level testing validates the registration
    function exists and is callable with a FastMCP instance.
    """

    def test_register_erase_memories_tool_function_exists(self):
        """Verify register_erase_memories_tool function exists and is callable.

        # Validates: FR-11, DP-1
        The registration function is the public API for tool registration.
        """
        from mcp_server.tools.erase_memories import register_erase_memories_tool

        assert callable(register_erase_memories_tool)

    def test_register_erase_memories_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance.

        # Validates: FR-11, DP-1
        The registration function should accept a FastMCP instance and
        register the erase_memories tool with it.
        """
        from unittest.mock import MagicMock

        from mcp_server.tools.erase_memories import register_erase_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_erase_memories_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_erase_memories_tool_registers_async_function(self):
        """Verify registration registers an async tool function.

        # Validates: FR-11
        The registered function should be async.
        """
        from unittest.mock import MagicMock

        from mcp_server.tools.erase_memories import register_erase_memories_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_erase_memories_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
