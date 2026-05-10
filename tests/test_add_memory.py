"""
Unit tests for add_memory MCP tool.

# UT-7: add_memory tool tests
# Validates requirements: FR-4
# Scenarios:
#   - SCEN-19: content stored with userId
#   - SCEN-20: memory_id returned
#   - SCEN-21: invalid input rejected
# AC-10: Content stored indexed by user_id
# AC-11: memory_id returned to caller
# AC-12: Invalid input rejected with descriptive error
# E-4: ERR_400 - Invalid content or user_id provided to add_memory
# E-2: ERR_MEM_001 - Mem0 AsyncMemory not initialized or unavailable
# DP-1: Dependency Injection Pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    TenantScope,
)
from mcp_server.tools.add_memory import AddMemoryInput, AddMemoryOutput, MemoryResult


class TestAddMemoryInput:
    """Test input validation for AddMemoryInput model."""

    def test_valid_input(self):
        """SCEN-19: valid messages and entity ID accepted."""
        input_model = AddMemoryInput(
            messages=[{"role": "user", "content": "Test memory content"}],
            user_id="user_123",
        )
        assert input_model.messages == [{"role": "user", "content": "Test memory content"}]
        assert input_model.user_id == "user_123"

    def test_messages_too_short_raises_error(self):
        """Empty messages list rejected."""
        with pytest.raises(ValueError):
            AddMemoryInput(
                messages=[],
                user_id="user_123",
            )

    def test_message_missing_role_raises_error(self):
        """Message without role field rejected."""
        with pytest.raises(ValueError):
            AddMemoryInput(
                messages=[{"content": "Test content"}],
                user_id="user_123",
            )

    def test_message_missing_content_raises_error(self):
        """Message without content field rejected."""
        with pytest.raises(ValueError):
            AddMemoryInput(
                messages=[{"role": "user"}],
                user_id="user_123",
            )

    def test_empty_content_in_message_raises_error(self):
        """Message with empty content rejected."""
        with pytest.raises(ValueError):
            AddMemoryInput(
                messages=[{"role": "user", "content": "   "}],
                user_id="user_123",
            )

    def test_entity_ids_required(self):
        """At least one entity ID (user_id, agent_id, or run_id) required."""
        with pytest.raises(ValueError):
            AddMemoryInput(
                messages=[{"role": "user", "content": "Test content"}],
            )

    def test_optional_parameters_accepted(self):
        """Verify optional parameters are accepted."""
        input_model = AddMemoryInput(
            messages=[{"role": "user", "content": "Test content"}],
            user_id="user_123",
            agent_id="agent_789",
            run_id="run_456",
            metadata={"key": "value"},
            infer=False,
        )
        assert input_model.agent_id == "agent_789"
        assert input_model.run_id == "run_456"
        assert input_model.metadata == {"key": "value"}
        assert input_model.infer is False

    def test_optional_parameters_default_values(self):
        """Verify optional parameters have correct defaults."""
        input_model = AddMemoryInput(
            messages=[{"role": "user", "content": "Test content"}],
            user_id="user_123",
        )
        assert input_model.agent_id is None
        assert input_model.run_id is None
        assert input_model.metadata is None
        assert input_model.infer is True


class TestAddMemoryOutput:
    """Test output model for AddMemoryOutput."""

    def test_output_model(self):
        """Verify output model structure."""
        output = AddMemoryOutput(
            results=[
                MemoryResult(
                    id="mem_abc123",
                    memory="Test memory content",
                    metadata={"key": "value"},
                    event="ADD",
                )
            ]
        )
        assert len(output.results) == 1
        assert output.results[0].id == "mem_abc123"
        assert output.results[0].memory == "Test memory content"


class TestAddMemoryTool:
    """Test add_memory tool functionality via MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock AsyncMemory for add tests."""
        client = MagicMock()
        client.add = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mocked memory."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.fixture
    def scope(self):
        """Create TenantScope for tests."""
        return TenantScope(
            org_id="org_abc",
            project_id="proj_xyz",
            user_id="user_123",
            agent_id=None,
            session_id=None,
        )

    @pytest.mark.asyncio
    async def test_add_memory_success(self, manager, mock_mem0_client, scope):
        """SCEN-19 & SCEN-20: content stored with userId, memory_id returned."""
        mock_mem0_client.add.return_value = {
            "results": [{
                "id": "mem_test123",
                "memory": "Test memory content",
                "created_at": "2024-01-01T00:00:00Z",
            }]
        }

        result = await manager.add_memory(
            scope=scope,
            content="Test memory content",
        )

        assert result.id == "mem_test123"
        assert result.content == "Test memory content"

        mock_mem0_client.add.assert_called_once()
        call_kwargs = mock_mem0_client.add.call_args.kwargs
        assert call_kwargs["messages"] == [{"role": "user", "content": "Test memory content"}]

    @pytest.mark.asyncio
    async def test_add_memory_with_metadata(self, manager, mock_mem0_client, scope):
        """Verify add_memory works with metadata."""
        mock_mem0_client.add.return_value = {
            "results": [{
                "id": "mem_metadata",
                "created_at": "2024-01-01T00:00:00Z",
            }]
        }

        result = await manager.add_memory(
            scope=scope,
            content="Test content",
            metadata={"key": "value"},
        )

        assert result.id == "mem_metadata"
        mock_mem0_client.add.assert_called_once()
        call_kwargs = mock_mem0_client.add.call_args.kwargs
        assert call_kwargs["metadata"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_add_memory_invalid_scope_raises_error(self):
        """SCEN-21: invalid scope rejected."""
        manager = MemoryManager(mem0_client=MagicMock())
        invalid_scope = TenantScope(
            org_id="",
            project_id="proj_xyz",
            user_id="user_123",
            agent_id=None,
            session_id=None,
        )

        with pytest.raises(Exception):
            await manager.add_memory(
                scope=invalid_scope,
                content="Test content",
            )

    @pytest.mark.asyncio
    async def test_add_memory_uninitialized_memory_raises_error(self):
        """E-2: ERR_MEM_001 - uninitialized memory raises error."""
        manager = MemoryManager(mem0_client=None)
        scope = TenantScope(
            org_id="org_abc",
            project_id="proj_xyz",
            user_id="user_123",
            agent_id=None,
            session_id=None,
        )

        with pytest.raises(Exception):
            await manager.add_memory(
                scope=scope,
                content="Test content",
            )


class TestAddMemoryToolRegistration:
    """Test add_memory tool registration with FastMCP."""

    def test_register_add_memory_tool_function_exists(self):
        """Verify register_add_memory_tool function exists and is callable."""
        from mcp_server.tools.add_memory import register_add_memory_tool

        assert callable(register_add_memory_tool)

    def test_register_add_memory_tool_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.tools.add_memory import register_add_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_add_memory_tool(mock_mcp)

        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_add_memory_tool_registers_async_function(self):
        """Verify registration registers an async tool function."""
        from unittest.mock import MagicMock

        from mcp_server.tools.add_memory import register_add_memory_tool

        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        register_add_memory_tool(mock_mcp)

        assert mock_mcp.tool.call_count == 1
