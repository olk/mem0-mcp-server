"""
Shared test fixtures for mem0-mcp integration tests.

This module provides fixtures for test isolation using unique identifiers
and common utilities for testing MCP server over SSE with Redis backend.

Note: Some imports are lazy-loaded to avoid import errors when running
unit tests that don't need the full application dependencies.
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _get_tenant_scope():
    """Lazy import of TenantScope to avoid import errors in unit tests."""
    from mcp_server.memory.manager import TenantScope
    return TenantScope


@pytest.fixture
def unique_user_id() -> str:
    """Unique user ID per test."""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_agent_id() -> str:
    """Unique agent ID per test."""
    return f"test_agent_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_session_id() -> str:
    """Unique session ID per test."""
    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_memory_content() -> str:
    """Unique memory content per test to avoid collisions."""
    return f"test_memory_{uuid.uuid4().hex}"


@pytest.fixture
def tenant_scope_factory():
    """Factory to create isolated tenant scopes per test.

    Usage:
        scope = tenant_scope_factory(
            user_id=unique_user_id
        )
    """
    TenantScope = _get_tenant_scope()

    def _create(
        user_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
    ):
        return TenantScope(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
        )
    return _create


@pytest.fixture
def isolated_scope(unique_user_id):
    """Create a fully isolated tenant scope for a single test.

    This fixture ensures complete isolation between tests by using
    unique user ID generated per test function.
    """
    TenantScope = _get_tenant_scope()
    return TenantScope(
        user_id=unique_user_id,
    )


@pytest.fixture
def isolated_scope_with_agent(unique_user_id, unique_agent_id):
    """Create an isolated tenant scope with agent ID."""
    TenantScope = _get_tenant_scope()
    return TenantScope(
        user_id=unique_user_id,
        agent_id=unique_agent_id,
    )


@pytest.fixture
def isolated_scope_with_session(unique_user_id, unique_agent_id, unique_session_id):
    """Create an isolated tenant scope with agent and session IDs."""
    TenantScope = _get_tenant_scope()
    return TenantScope(
        user_id=unique_user_id,
        agent_id=unique_agent_id,
        session_id=unique_session_id,
    )


def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "integration: mark test as integration test requiring Docker")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker container")
    config.addinivalue_line("markers", "sse: mark test as SSE transport test")
    config.addinivalue_line("markers", "redis: mark test as Redis-related test")
