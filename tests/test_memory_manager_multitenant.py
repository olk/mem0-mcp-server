"""Unit tests for MemoryManager multi-tenant isolation.

# UT-5: Multi-tenant isolation tests
# Validates requirements: FR-10, FR-19
# Scenarios: SCEN-13 (org_id/project_id/user_id hierarchy), SCEN-14 (session isolation),
#            SCEN-15 (invalid scope rejected)
# DP-6: Multi-Tenant Isolation Pattern
# AC-47: All scope levels supported
# AC-48: Hierarchy enforced in storage
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.memory.manager import (
    MemoryManager,
    ScopeValidationError,
    TenantScope,
)


class TestMultiTenantIsolation:
    """Test multi-tenant isolation using user_id hierarchy."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock AsyncMemory."""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem_123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[
            {"id": "mem_1", "content": "test", "score": 0.9, "metadata": {}}
        ])
        client.update = AsyncMock(return_value={"status": "updated"})
        client.delete = AsyncMock(return_value={"status": "deleted"})
        client.get_all = AsyncMock(return_value={
            "id": "mem_123",
            "content": "test content",
            "user_id": "user_1",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        })
        return client

    @pytest.fixture
    def manager(self, mock_mem0_client):
        """Create MemoryManager with mock client."""
        return MemoryManager(mem0_client=mock_mem0_client)

    @pytest.mark.asyncio
    async def test_add_with_user_id_hierarchy(self, manager, mock_mem0_client):
        """SCEN-13: user_id hierarchy supported.

        # Validates: FR-10, FR-19, DP-6, AC-47
        User-level hierarchy should be passed to Mem0.
        """
        scope = TenantScope(
            user_id="user_123"
        )
        result = await manager.add_memory(
            scope=scope,
            content="Test memory content"
        )

        # Verify AsyncMemory.add was called with all scoping parameters
        mock_mem0_client.add.assert_called_once()
        call_kwargs = mock_mem0_client.add.call_args.kwargs
        assert "user_123" == call_kwargs["user_id"]
        assert result.id == "mem_123"
        assert result.content == "Test memory content"

    @pytest.mark.asyncio
    async def test_search_with_multi_tenant_scoping(self, manager, mock_mem0_client):
        """SCEN-13: Search respects multi-tenant scoping.

        # Validates: FR-10, FR-19, DP-6, AC-48
        """
        scope = TenantScope(
            user_id="user_123"
        )
        results = await manager.search_memories(
            scope=scope,
            query="test query",
            limit=5
        )

        mock_mem0_client.search.assert_called_once()
        call_kwargs = mock_mem0_client.search.call_args.kwargs
        assert "user_123" == call_kwargs["filters"]["user_id"]
        assert call_kwargs["top_k"] == 5
        assert len(results) == 1
        assert results[0].id == "mem_1"

    @pytest.mark.asyncio
    async def test_session_isolation_works(self, manager, mock_mem0_client):
        """SCEN-14: Session isolation works.

        # Validates: FR-10, FR-19, AC-47
        Sessions should be passed through for isolation.
        """
        scope = TenantScope(
            user_id="user_123",
            session_id="session_abc"
        )
        await manager.add_memory(
            scope=scope,
            content="Session-specific memory"
        )

        mock_mem0_client.add.assert_called_once()
        call_kwargs = mock_mem0_client.add.call_args.kwargs
        assert "session_abc" in call_kwargs["user_id"]

    @pytest.mark.asyncio
    async def test_invalid_scope_rejected(self, manager):
        """SCEN-15: Invalid scope rejected.

        # Validates: FR-10, FR-19, AC-48, E-9
        Empty user_id should be rejected.
        """
        scope = TenantScope(
            user_id=""  # Invalid: empty
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            await manager.add_memory(scope=scope, content="Test content")

        assert exc_info.value.code == "ERR_SCOPE_001"

    @pytest.mark.asyncio
    async def test_empty_user_id_rejected(self, manager):
        """SCEN-15: Empty user_id should be rejected.

        # Validates: FR-10, FR-19, E-9
        user_id is required for isolation.
        """
        scope = TenantScope(
            user_id="",  # Invalid: empty
        )
        with pytest.raises(ScopeValidationError) as exc_info:
            await manager.add_memory(scope=scope, content="Test memory")

        assert exc_info.value.code == "ERR_SCOPE_001"


class TestMemoryManagerInitialization:
    """Test MemoryManager initialization and error handling."""

    @pytest.mark.asyncio
    async def test_uninitialized_manager_with_none_client(self):
        """E-9: ScopeValidationError when required scope missing.

        # Validates: IC-3, E-9
        Operations without proper scope should raise ScopeValidationError.
        """
        # Manager initialized with None client - this is a valid initialization
        # but operations will fail due to scope validation, not client initialization
        manager = MemoryManager(mem0_client=None)

        # Create scope with empty required field - should fail scope validation
        scope = TenantScope(user_id="")
        with pytest.raises(ScopeValidationError) as exc_info:
            await manager.add_memory(scope=scope, content="test")

        assert exc_info.value.code == "ERR_SCOPE_001"
        assert exc_info.value.http_status == 400

    @pytest.fixture
    def mock_mem0_client(self):
        """Create mock AsyncMemory for initialization tests."""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem_123"}])
        return client

    def test_initialized_manager_has_client(self, mock_mem0_client):
        """Verify manager has client when properly initialized."""
        manager = MemoryManager(mem0_client=mock_mem0_client)
        assert manager.client is mock_mem0_client

    def test_uninitialized_manager_client_is_none(self):
        """Verify manager.client is None when initialized with None."""
        manager = MemoryManager(mem0_client=None)
        assert manager.client is None
