"""
# UT-5: Multi-tenant memory manager tests
# Validates: FR-10, FR-19
# Scenario: SCEN-13 (org hierarchy), SCEN-14 (session isolation), SCEN-15 (invalid scope rejected)
# AC-27: user_id/agent_id/session_id scoping supported
# AC-28: Data isolation enforced between tenants

Unit tests for multi-tenant memory manager.
Tests scope validation, session isolation, and invalid scope rejection.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.memory.manager import (
    MemoryEntry,
    MemoryManager,
    ScopeValidationError,
    ScopeValidator,
    TenantScope,
)


class TestTenantScope:
    """# AC-27: Simplified scope hierarchy for Mem0 v3"""

    def test_scope_with_full_hierarchy(self):
        """# SCEN-13: user_id/agent_id/session_id hierarchy supported"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-abc"
        )
        assert scope.user_id == "user-789"
        assert scope.agent_id == "agent-001"
        assert scope.session_id == "session-abc"

    def test_scope_with_user_only(self):
        """# SCEN-13: user-level scope without agent/session"""
        scope = TenantScope(
            user_id="user-789"
        )
        assert scope.agent_id is None
        assert scope.session_id is None

    def test_to_mem0_user_id_full(self):
        """# FR-10: Format scope hierarchy for Mem0 user_id"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-abc"
        )
        expected = "user-789:agent-001:session-abc"
        assert scope.to_mem0_user_id() == expected

    def test_to_mem0_user_id_user_only(self):
        """# FR-10: Format user-level scope"""
        scope = TenantScope(
            user_id="user-789"
        )
        expected = "user-789"
        assert scope.to_mem0_user_id() == expected

    def test_to_mem0_user_id_with_agent(self):
        """# FR-10: Format agent-level scope"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001"
        )
        expected = "user-789:agent-001"
        assert scope.to_mem0_user_id() == expected


class TestScopeValidationError:
    """# E-9: ERR_SCOPE_001 - Invalid scope hierarchy provided"""

    def test_error_properties(self):
        """# E-9: Error has correct properties"""
        error = ScopeValidationError(
            message="Custom message",
            code="ERR_SCOPE_001",
            http_status=400
        )
        assert error.code == "ERR_SCOPE_001"
        assert error.http_status == 400
        assert error.message == "Custom message"

    def test_error_default_values(self):
        """# E-9: Error has default values"""
        error = ScopeValidationError()
        assert error.code == "ERR_SCOPE_001"
        assert error.http_status == 400
        assert error.message == "Invalid scope hierarchy provided"


class TestScopeValidator:
    """# E-9: Scope validation on input"""

    def test_valid_full_scope(self):
        """# SCEN-13: user_id/agent_id/session_id hierarchy supported"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-abc"
        )
        assert ScopeValidator.validate_scope(scope) is True

    def test_valid_user_only_scope(self):
        """# SCEN-13: user-level scope validation"""
        scope = TenantScope(
            user_id="user-789"
        )
        assert ScopeValidator.validate_scope(scope) is True

    def test_invalid_empty_user_id(self):
        """# SCEN-15: invalid scope rejected - empty user_id"""
        scope = TenantScope(
            user_id=""
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)
        assert exc_info.value.code == "ERR_SCOPE_001"
        assert "user_id" in exc_info.value.message.lower()

    def test_invalid_whitespace_user_id(self):
        """# SCEN-15: invalid scope rejected - whitespace user_id"""
        scope = TenantScope(
            user_id="   "
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)
        assert exc_info.value.code == "ERR_SCOPE_001"

    def test_invalid_empty_agent_id(self):
        """# SCEN-15: invalid scope rejected - empty agent_id"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="   "
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)
        assert exc_info.value.code == "ERR_SCOPE_001"
        assert "agent_id" in exc_info.value.message.lower()

    def test_invalid_empty_session_id(self):
        """# SCEN-15: invalid scope rejected - empty session_id"""
        scope = TenantScope(
            user_id="user-789",
            session_id="   "
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)
        assert exc_info.value.code == "ERR_SCOPE_001"
        assert "session_id" in exc_info.value.message.lower()


class TestMemoryEntry:
    """# AC-27: Memory entry with scope hierarchy"""

    def test_memory_entry_creation(self):
        """# FR-10: Memory stored with scope info"""
        entry = MemoryEntry(
            id="mem-123",
            content="Test memory content",
            metadata={"user_id": "user-789"},
            created_at="2024-01-01T00:00:00Z"
        )
        assert entry.id == "mem-123"
        assert entry.content == "Test memory content"
        assert entry.metadata["user_id"] == "user-789"


class TestMemoryManager:
    """# FR-10: Multi-tenant memory operations"""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"},
            {"id": "mem-2", "content": "Memory 2", "metadata": {}, "created_at": "2024-01-01T00:00:01Z"}
        ])
        client.get_all = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.get = AsyncMock(return_value={
            "id": "mem-123",
            "user_id": "user-789",
            "metadata": {"user_id": "user-789"}
        })
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def memory_manager(self, mock_mem0_client):
        """MemoryManager with mocked client"""
        return MemoryManager(mock_mem0_client)

    @pytest.mark.asyncio
    async def test_add_memory_success(self, memory_manager, mock_mem0_client):
        """# AC-27: Memory stored with scope hierarchy"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-abc"
        )

        result = await memory_manager.add_memory(
            scope=scope,
            content="Test memory content"
        )

        assert result.id == "mem-123"
        assert result.content == "Test memory content"
        assert result.metadata["agent_id"] == "agent-001"
        assert result.metadata["session_id"] == "session-abc"

        mock_mem0_client.add.assert_called_once()
        call_args = mock_mem0_client.add.call_args
        assert "user-789:agent-001:session-abc" in call_args.kwargs["user_id"]

    @pytest.mark.asyncio
    async def test_add_memory_invalid_scope(self, memory_manager):
        """# SCEN-15: E-9: invalid scope rejected"""
        scope = TenantScope(
            user_id="",
        )

        with pytest.raises(ScopeValidationError) as exc_info:
            await memory_manager.add_memory(scope=scope, content="Test content")
        assert exc_info.value.code == "ERR_SCOPE_001"

    @pytest.mark.asyncio
    async def test_search_memories_success(self, memory_manager, mock_mem0_client):
        """# AC-28: Data isolation enforced - search within scope"""
        scope = TenantScope(
            user_id="user-789"
        )

        results = await memory_manager.search_memories(
            scope=scope,
            query="test query",
            limit=10
        )

        assert len(results) == 2
        assert results[0].content == "Memory 1"
        assert results[1].content == "Memory 2"

        mock_mem0_client.search.assert_called_once()
        call_args = mock_mem0_client.search.call_args
        assert "user-789" in call_args.kwargs["filters"]["user_id"]

    @pytest.mark.asyncio
    async def test_search_memories_different_users_isolated(self, memory_manager, mock_mem0_client):
        """# AC-28: Users cannot access other users' memories"""
        scope_user_a = TenantScope(
            user_id="user-A"
        )

        scope_user_b = TenantScope(
            user_id="user-B"
        )

        # Search for user A
        await memory_manager.search_memories(scope=scope_user_a, query="test")
        call_a = mock_mem0_client.search.call_args
        assert "user-A" in call_a.kwargs["filters"]["user_id"]

        # Search for user B
        await memory_manager.search_memories(scope=scope_user_b, query="test")
        call_b = mock_mem0_client.search.call_args
        assert "user-B" in call_b.kwargs["filters"]["user_id"]

    @pytest.mark.asyncio
    async def test_get_memories_success(self, memory_manager, mock_mem0_client):
        """# FR-10: Get memories within tenant scope"""
        scope = TenantScope(
            user_id="user-789"
        )

        results = await memory_manager.get_memories(scope=scope, limit=50)

        assert len(results) == 1
        assert results[0].id == "mem-1"

        mock_mem0_client.get_all.assert_called_once()
        call_args = mock_mem0_client.get_all.call_args
        assert call_args.kwargs["filters"]["user_id"] == "user-789"

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, memory_manager, mock_mem0_client):
        """# FR-10: Delete memory with scope validation"""
        scope = TenantScope(
            user_id="user-789"
        )

        result = await memory_manager.delete_memory(
            memory_id="mem-123",
            scope=scope
        )

        assert result is True
        mock_mem0_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_all_memories_success(self, memory_manager, mock_mem0_client):
        """# SCEN-14: session isolation - delete all in scope"""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001"
        )

        result = await memory_manager.delete_all_memories(scope=scope)

        assert result is True
        mock_mem0_client.delete_all.assert_called_once()
        call_args = mock_mem0_client.delete_all.call_args
        assert call_args[1]["user_id"] == "user-789:agent-001"

    @pytest.mark.asyncio
    async def test_session_isolation(self, memory_manager, mock_mem0_client):
        """# SCEN-14: session isolation works - different sessions have separate memories"""
        scope_session_1 = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-1"
        )

        scope_session_2 = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-2"
        )

        # Add memory to session 1
        await memory_manager.add_memory(
            scope=scope_session_1,
            content="Session 1 memory"
        )
        call_1 = mock_mem0_client.add.call_args
        assert "session-1" in call_1.kwargs["user_id"]

        # Add memory to session 2
        await memory_manager.add_memory(
            scope=scope_session_2,
            content="Session 2 memory"
        )
        call_2 = mock_mem0_client.add.call_args
        assert "session-2" in call_2.kwargs["user_id"]


class TestTenantScopeDisplayString:
    """Test TenantScope.to_display_string() method (line 104)."""

    def test_to_display_string_full_scope(self):
        """Test display string with full scope hierarchy."""
        scope = TenantScope(
            user_id="user-789",
            agent_id="agent-001",
            session_id="session-abc"
        )
        display = scope.to_display_string()

        assert "user=user-789" in display
        assert "agent=agent-001" in display
        assert "session=session-abc" in display

    def test_to_display_string_user_only(self):
        """Test display string with user-level scope only."""
        scope = TenantScope(
            user_id="user-789"
        )
        display = scope.to_display_string()

        assert "user=user-789" in display
        assert "agent=None" in display
        assert "session=None" in display


class TestScopeValidatorAgentId:
    """Test ScopeValidator with agent_id validation (lines 167-171)."""

    def test_invalid_whitespace_agent_id(self):
        """Test that whitespace-only agent_id is rejected."""
        scope = TenantScope(
            user_id="user-789",
            agent_id="   "
        )

        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)

        assert exc_info.value.code == "ERR_SCOPE_001"
        assert "agent_id" in exc_info.value.message.lower()

    def test_empty_agent_id_accepted_when_none(self):
        """Test that None agent_id is accepted."""
        scope = TenantScope(
            user_id="user-789",
            agent_id=None
        )

        result = ScopeValidator.validate_scope(scope)
        assert result is True


class TestScopeValidatorSessionId:
    """Test ScopeValidator with session_id validation (lines 178-182)."""

    def test_invalid_whitespace_session_id(self):
        """Test that whitespace-only session_id is rejected."""
        scope = TenantScope(
            user_id="user-789",
            session_id="   "
        )

        with pytest.raises(ScopeValidationError) as exc_info:
            ScopeValidator.validate_scope(scope)

        assert exc_info.value.code == "ERR_SCOPE_001"
        assert "session_id" in exc_info.value.message.lower()

    def test_empty_session_id_accepted_when_none(self):
        """Test that None session_id is accepted."""
        scope = TenantScope(
            user_id="user-789",
            session_id=None
        )

        result = ScopeValidator.validate_scope(scope)
        assert result is True


class TestMemoryManagerExceptionPaths:
    """Test exception handling paths in MemoryManager."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client."""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """MemoryManager with mocked client."""
        return MemoryManager(mock_mem0_client)

    @pytest.mark.asyncio
    async def test_delete_memory_raises_on_different_tenant(self, manager, mock_mem0_client):
        """Test delete_memory raises when memory belongs to different tenant (line 618)."""
        scope = TenantScope(
            user_id="user-789"
        )

        mock_mem0_client.get = AsyncMock(return_value={
            "id": "mem-123",
            "user_id": "different:user:id",
            "metadata": {"user_id": "different:user:id"}
        })

        with pytest.raises(ValueError) as exc_info:
            await manager.delete_memory(memory_id="mem-123", scope=scope)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delete_memory_raises_on_aclose_error(self, manager, mock_mem0_client):
        """Test delete_memory handles exception from aclose (line 623)."""
        scope = TenantScope(
            user_id="user-789"
        )

        mock_mem0_client.get.return_value = None
        mock_mem0_client.delete.side_effect = RuntimeError("Connection closed")

        with pytest.raises(RuntimeError) as exc_info:
            await manager.delete_memory(memory_id="mem-123", scope=scope)

        assert "Failed to delete memory" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_all_memories_handles_exception(self, manager, mock_mem0_client):
        """Test delete_all_memories handles exception (lines 659-664)."""
        scope = TenantScope(
            user_id="user-789"
        )

        mock_mem0_client.delete_all.side_effect = Exception("Redis connection lost")

        with pytest.raises(RuntimeError) as exc_info:
            await manager.delete_all_memories(scope=scope)

        assert "Failed to delete all memories" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_memory_reraises_not_found(self, manager, mock_mem0_client):
        """Test update_memory re-raises ValueError from get_memory (line 718)."""
        scope = TenantScope(
            user_id="user-789"
        )

        mock_mem0_client.get.return_value = {
            "id": "mem-123",
            "user_id": "user-789",
            "metadata": {"user_id": "user-789"},
            "content": "old content"
        }
        mock_mem0_client.update.side_effect = ValueError("Memory not found")

        with pytest.raises(ValueError) as exc_info:
            await manager.update_memory(
                memory_id="mem-123",
                scope=scope,
                content="new content"
            )

        assert "Failed to update memory" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_memory_tenant_isolation_violation(self, manager, mock_mem0_client):
        """Test get_memory raises when accessing memory from different tenant (lines 569-573)."""
        scope = TenantScope(
            user_id="user-789"
        )

        mock_mem0_client.get = AsyncMock(return_value={
            "id": "mem-123",
            "user_id": "different:tenant:id",
            "metadata": {"user_id": "different:tenant:id"}
        })

        with pytest.raises(ValueError) as exc_info:
            await manager.get_memory(memory_id="mem-123", scope=scope)

        assert "not found" in str(exc_info.value).lower()


class TestSearchMemoriesWithMetadataFilters:
    """Test search_memories with metadata_filters (line 467)."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock Mem0 AsyncMemory client."""
        client = MagicMock()
        client.search = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Result 1", "metadata": {"category": "important"}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """MemoryManager with mocked client."""
        return MemoryManager(mock_mem0_client)

    @pytest.mark.asyncio
    async def test_search_with_metadata_filters(self, manager, mock_mem0_client):
        """Test that search_memories passes metadata_filters to mem0 client."""
        scope = TenantScope(
            user_id="user-789"
        )

        filters = {"category": "important", "priority": "high"}

        results = await manager.search_memories(
            scope=scope,
            query="test query",
            limit=10,
            metadata_filters=filters
        )

        mock_mem0_client.search.assert_called_once()
        call_kwargs = mock_mem0_client.search.call_args.kwargs

        assert "filters" in call_kwargs
        assert call_kwargs["filters"]["user_id"] == "user-789"
        assert call_kwargs["filters"]["category"] == "important"
        assert call_kwargs["filters"]["priority"] == "high"

        assert len(results) == 1
        assert results[0].id == "mem-1"
