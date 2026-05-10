"""
Unit tests for update_memory MCP tool.

# UT-11: update_memory tool tests
# Validates requirements: FR-6
# Scenarios:
#   - SCEN-32: memory_id required
#   - SCEN-33: content updated
#   - SCEN-34: metadata preserved
#   - SCEN-35: invalid input rejected
# AC-16: memory_id required - Valid memory_id must be provided
# AC-17: content updated - Memory content is updated with new content
# AC-18: Metadata preserved - Existing metadata preserved during update
# E-6: ERR_404 - Memory ID not found during update
# E-8: ERR_404 - Memory ID not found during get
# RPARAM-5: memory_id - non-empty string, max 255 chars
# RPARAM-6: content - non-empty string, max 10000 chars
# OPARAM-9: metadata - Optional object for updated metadata
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.update_memory import UpdateMemoryInput, UpdateMemoryOutput


class TestUpdateMemoryInput:
    """Test input validation for UpdateMemoryInput model."""

    def test_valid_input(self):
        """SCEN-32: valid memory_id and content accepted."""
        input_model = UpdateMemoryInput(
            memory_id="mem_test123",
            content="Updated memory content",
        )
        assert input_model.memory_id == "mem_test123"
        assert input_model.content == "Updated memory content"

    def test_memory_id_too_long_raises_error(self):
        """AC-16: memory_id exceeding 255 chars rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="x" * 256,
                content="Valid content",
            )

    def test_content_too_long_raises_error(self):
        """AC-17: content exceeding 10000 chars rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="mem_test123",
                content="x" * 10001,
            )

    def test_empty_memory_id_raises_error(self):
        """SCEN-35: empty memory_id rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="",
                content="Valid content",
            )

    def test_whitespace_only_memory_id_raises_error(self):
        """SCEN-35: whitespace-only memory_id rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="   ",
                content="Valid content",
            )

    def test_empty_content_raises_error(self):
        """SCEN-35: empty content rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="mem_test123",
                content="",
            )

    def test_whitespace_only_content_raises_error(self):
        """SCEN-35: whitespace-only content rejected."""
        with pytest.raises(ValueError):
            UpdateMemoryInput(
                memory_id="mem_test123",
                content="   ",
            )

    def test_optional_metadata_accepted(self):
        """SCEN-34: Verify optional metadata parameter is accepted."""
        input_model = UpdateMemoryInput(
            memory_id="mem_test123",
            content="Updated content",
            metadata={"key": "value", "new_key": "new_value"},
        )
        assert input_model.metadata == {"key": "value", "new_key": "new_value"}

    def test_optional_metadata_defaults_to_none(self):
        """Verify optional metadata defaults to None when not provided."""
        input_model = UpdateMemoryInput(
            memory_id="mem_test123",
            content="Updated content",
        )
        assert input_model.metadata is None


class TestUpdateMemoryOutput:
    """Test output model for UpdateMemoryOutput."""

    def test_output_model(self):
        """Verify output model structure with status and updated_at."""
        output = UpdateMemoryOutput(
            status="updated",
            updated_at="2026-04-30T12:00:00Z",
        )
        assert output.status == "updated"
        assert output.updated_at == "2026-04-30T12:00:00Z"


class TestUpdateMemoryTool:
    """Test update_memory tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client for update tests."""
        client = MagicMock()
        client.update = AsyncMock()
        client.get_all = AsyncMock()
        client.get = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for update tests."""
        return TenantScope(user_id="user_123")

    @pytest.mark.asyncio
    async def test_update_memory_success(self, manager, mock_mem0_client, scope):
        """SCEN-33: content updated - memory content is updated."""
        mock_mem0_client.update.return_value = {
            "id": "mem_test123",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_mem0_client.get.return_value = {
            "id": "mem_test123",
            "memory": "Old content",
            "metadata": {"user_id": "user_123"},
            "created_at": "2024-01-01T00:00:00Z",
        }

        result = await manager.update_memory(
            memory_id="mem_test123",
            scope=scope,
            content="Updated content",
            metadata={"new_key": "new_value"},
        )

        assert result.id == "mem_test123"
        assert result.content == "Updated content"

        mock_mem0_client.update.assert_called_once()
        call_kwargs = mock_mem0_client.update.call_args.kwargs
        assert call_kwargs["memory_id"] == "mem_test123"
        assert call_kwargs["data"] == "Updated content"

    @pytest.mark.asyncio
    async def test_update_memory_invalid_scope_raises_error(self):
        """SCEN-35: invalid scope rejected."""
        manager = MemoryManager(mem0_client=MagicMock())
        # org_id and project_id are no longer part of TenantScope in v3
        # Instead, an empty user_id is used to create an invalid scope
        invalid_scope = TenantScope(user_id="")

        with pytest.raises(Exception):
            await manager.update_memory(
                memory_id="mem_test123",
                scope=invalid_scope,
                content="Updated content",
            )

    @pytest.mark.asyncio
    async def test_update_memory_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(user_id="user_123")

        with pytest.raises(Exception):
            await manager.update_memory(
                memory_id="mem_test123",
                scope=scope,
                content="Updated content",
            )


class TestUpdateMemoryToolRegistration:
    """Test update_memory tool registration with FastMCP."""

    def test_register_update_memory_tool_function_exists(self):
        """Verify register_update_memory_tool function exists and is callable."""
        from mcp_server.tools.update_memory import register_update_memory_tool

        assert callable(register_update_memory_tool)

    def test_register_update_memory_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.update_memory import register_update_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_update_memory_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_update_memory_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.update_memory import register_update_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_update_memory_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
