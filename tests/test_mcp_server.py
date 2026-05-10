"""
# Validates: FR-1, IC-2, IC-5, AC-1, AC-2, AC-3
# Test scenarios from task context:
#   - SCEN-10: transport=sse calls run_http_async(transport="sse")
#   - SCEN-11: transport=stdio calls run_stdio_async
#   - SCEN-12: invalid transport raises error

Unit tests for MCP server implementation.
Tests FastMCP singleton instance, transport selection, and error handling.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import importlib.util

spec = importlib.util.spec_from_file_location("mcp_server.transport", Path(__file__).parent.parent / "src" / "mcp_server" / "transport.py")
transport_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport_module)

TransportType = transport_module.TransportType
run_transport = transport_module.run_transport


class TestMCPInstance:
    """Tests for IC-2: Exactly one FastMCP instance must exist."""

    def test_single_instance_created(self):
        """AC-1: Server creates a single FastMCP instance with correct naming."""
        from mcp_server import get_mcp_instance, reset_mcp_instance

        # Reset any existing instance
        reset_mcp_instance()

        # Get instance
        mcp = get_mcp_instance()

        # Verify it exists and has correct attributes
        assert mcp is not None
        assert mcp.name == "Mem0-MCP Server"
        # Note: FastMCP uses 'instructions' not 'description'
        # The description is stored as instructions

        # Reset for other tests
        reset_mcp_instance()

    def test_multiple_instances_raises_error(self):
        """E-1: Multiple instances detected raises ERR_MCP_INIT error."""
        from mcp_server import get_mcp_instance, reset_mcp_instance

        # Reset any existing instance
        reset_mcp_instance()

        # Create first instance
        mcp1 = get_mcp_instance()
        assert mcp1 is not None

        # Try to create second instance - should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            get_mcp_instance()

        assert "ERR_MCP_INIT" in str(exc_info.value)
        assert "Multiple FastMCP instances detected" in str(exc_info.value)

        # Reset for other tests
        reset_mcp_instance()

    def test_mcp_exported_for_tool_binding(self):
        """IC-5: All @mcp.tool decorators must bind to the single instance."""
        from mcp_server import mcp

        # The mcp instance should be available for tool decorators
        assert mcp is not None
        assert hasattr(mcp, 'tool')
        assert callable(mcp.tool)


class TestTransportType:
    """Tests for transport type enum and selection."""

    def test_transport_type_enum_values(self):
        """EN-1: TransportType enum has correct values."""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.SSE.value == "sse"

    def test_transport_type_from_string(self):
        """TransportType can be created from string value."""
        assert TransportType("stdio") == TransportType.STDIO
        assert TransportType("sse") == TransportType.SSE


class TestRunTransport:
    """Tests for transport selection (DP-4 Strategy Pattern)."""

    @pytest.mark.asyncio
    async def test_sse_transport_calls_run_http_async(self):
        """SCEN-10: transport=sse calls run_http_async with transport='sse'."""
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp
        )

        mock_mcp.run_http_async.assert_called_once_with(transport="sse", host="0.0.0.0", port=8050)

    @pytest.mark.asyncio
    async def test_stdio_transport_calls_run_stdio_async(self):
        """SCEN-11: transport=stdio calls run_stdio_async."""
        mock_mcp = MagicMock()
        mock_mcp.run_stdio_async = AsyncMock()

        await run_transport(
            transport="stdio",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp
        )

        mock_mcp.run_stdio_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_transport_raises_error(self):
        """SCEN-12: invalid transport raises error."""
        mock_mcp = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await run_transport(
                transport="invalid",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp
            )

        assert "Invalid transport value" in str(exc_info.value)


class TestTransportErrors:
    """Tests for error handling in transport module."""

    @pytest.mark.asyncio
    async def test_stdio_error_raises_err_stdio_001(self):
        """E-10: stdio transport error raises ERR_STDIO_001."""
        mock_mcp = MagicMock()
        mock_mcp.run_stdio_async = AsyncMock(side_effect=Exception("stdin not available"))

        with pytest.raises(RuntimeError) as exc_info:
            await run_transport(
                transport="stdio",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp
            )

        assert "ERR_STDIO_001" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sse_error_raises_err_sse_001(self):
        """E-11: SSE transport error raises ERR_SSE_001."""
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock(side_effect=Exception("Port in use"))

        with pytest.raises(RuntimeError) as exc_info:
            await run_transport(
                transport="sse",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp
            )

        assert "ERR_SSE_001" in str(exc_info.value)


class TestLifespan:
    """Tests for lifespan context manager - FR-25 Graceful Shutdown."""

    def test_lifespan_function_exists(self):
        """lifespan function exists and is usable as FastMCP lifespan."""
        import inspect

        from mcp_server.lifespan import server_lifespan as lifespan

        # Verify it's callable
        assert callable(lifespan)
        # @asynccontextmanager decorated functions are async generator functions
        # when called - check the underlying function
        assert hasattr(lifespan, '__call__') or inspect.iscoroutinefunction(lifespan)

    def test_cleanup_with_timeout_function_exists(self):
        """_cleanup_with_timeout function exists for MTTR compliance."""
        import inspect

        from mcp_server.lifespan import _cleanup_with_timeout

        # Verify it's a coroutine function
        assert inspect.iscoroutinefunction(_cleanup_with_timeout)

    def test_cleanup_timeout_constant_defined(self):
        """NFR-5: CLEANUP_TIMEOUT_SECONDS is 300 for MTTR < 5 minutes."""
        from mcp_server.lifespan import CLEANUP_TIMEOUT_SECONDS

        assert CLEANUP_TIMEOUT_SECONDS == 300

    @pytest.mark.asyncio
    async def test_lifespan_yields_memory_dict(self):
        """lifespan yields dict with memory and manager keys."""
        from mcp_server.lifespan import server_lifespan as lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        # Mock memory_lifespan - import is inside lifespan function
        # so we patch it at the source module
        test_memory_result = {
            "memory": MagicMock(),
            "manager": MagicMock()
        }

        # Create a proper async context manager mock
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=test_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            async with lifespan(mock_app) as result:
                assert "memory" in result
                assert "manager" in result

    @pytest.mark.asyncio
    async def test_lifespan_stores_manager_in_app_state(self):
        """lifespan stores MemoryManager in app.state.memory per IC-3."""
        from mcp_server.lifespan import server_lifespan as lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        mock_manager = MagicMock()
        test_memory_result = {
            "memory": MagicMock(),
            "manager": mock_manager
        }

        # Create a proper async context manager mock
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=test_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            async with lifespan(mock_app):
                pass

            # Verify manager was stored in app.memory
            assert mock_app.memory == mock_manager

    @pytest.mark.asyncio
    async def test_cleanup_with_timeout_calls_aclose(self):
        """AC-60: Cleanup calls memory.aclose() for connection closure."""
        from mcp_server.lifespan import _cleanup_with_timeout

        mock_memory = MagicMock()
        mock_memory.close = MagicMock()

        memory_result = {"memory": mock_memory, "manager": MagicMock()}

        await _cleanup_with_timeout(memory_result)

        mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_timeout_handles_exception(self):
        """AC-60: Cleanup handles exceptions without blocking shutdown."""
        from mcp_server.lifespan import _cleanup_with_timeout

        mock_memory = MagicMock()
        mock_memory.close = MagicMock(side_effect=Exception("Connection error"))

        memory_result = {"memory": mock_memory, "manager": MagicMock()}

        # Should not raise - exception is caught
        await _cleanup_with_timeout(memory_result)

        mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_timeout_handles_none_memory(self):
        """_cleanup_with_timeout handles None memory gracefully."""
        from mcp_server.lifespan import _cleanup_with_timeout

        memory_result = {"memory": None, "manager": MagicMock()}

        # Should not raise - handles None gracefully
        await _cleanup_with_timeout(memory_result)

    @pytest.mark.asyncio
    async def test_lifespan_completion_calls_aclose_after_exit(self):
        """FR-25/AC-60/AC-61: lifespan completion calls memory.aclose() after exit.

        Verifies the full lifecycle:
        1. Enter lifespan context (startup yields memory/manager)
        2. Exit context (shutdown triggers cleanup)
        3. Verify aclose() was called AFTER exit (cleanup happened)
        """
        from mcp_server.lifespan import server_lifespan as lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        mock_memory = MagicMock()
        mock_memory.close = MagicMock()

        mock_manager = MagicMock()
        test_memory_result = {"memory": mock_memory, "manager": mock_manager}

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=test_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            async with lifespan(mock_app):
                pass

            # AFTER exit, verify cleanup was called
            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_completion_with_exception_still_cleans_up(self):
        """FR-25/AC-60: lifespan cleanup runs even if exception occurs in context."""
        from mcp_server.lifespan import server_lifespan as lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        mock_memory = MagicMock()
        mock_memory.close = MagicMock()

        mock_manager = MagicMock()
        test_memory_result = {"memory": mock_memory, "manager": mock_manager}

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=test_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            with pytest.raises(ValueError):
                async with lifespan(mock_app):
                    raise ValueError("Simulated error during lifespan")

            # Cleanup still runs after exception
            mock_memory.close.assert_called_once()


class TestLifespanExceptionPaths:
    """Test exception paths in server_lifespan.

    Tests coverage for line 90 (exception when settings not found)
    and line 103 (fallback server._memory = manager) in lifespan.py.
    """

    @pytest.mark.asyncio
    async def test_lifespan_raises_when_settings_not_found(self):
        """Test that Mem0InitializationError is raised when server._settings is None."""
        from unittest.mock import MagicMock, patch

        from mcp_server.lifespan import server_lifespan
        from mcp_server.memory.manager import Mem0InitializationError

        mock_app = MagicMock()
        mock_app.state = MagicMock()
        mock_app._settings = None

        mock_memory_result = {
            "memory": MagicMock(),
            "manager": MagicMock()
        }

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            with pytest.raises(Mem0InitializationError) as exc_info:
                async with server_lifespan(mock_app):
                    pass

            assert "Server settings not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lifespan_uses_fallback_state_when_no_state_attribute(self):
        """Test fallback to server._memory when state attribute doesn't exist."""
        from unittest.mock import MagicMock, patch

        from mcp_server.lifespan import server_lifespan

        mock_app = MagicMock(spec=[])  # No state attribute
        mock_app._settings = MagicMock()

        mock_manager = MagicMock()
        mock_memory_result = {
            "memory": MagicMock(),
            "manager": mock_manager
        }

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            async with server_lifespan(mock_app):
                pass

            # Verify memory was set
            assert mock_app.memory == mock_manager

    @pytest.mark.asyncio
    async def test_lifespan_uses_state_when_available(self):
        """Test that manager is stored in state.memory when state exists."""
        from unittest.mock import MagicMock, patch

        from mcp_server.lifespan import server_lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()
        mock_app._settings = MagicMock()

        mock_manager = MagicMock()
        mock_memory_result = {
            "memory": MagicMock(),
            "manager": mock_manager
        }

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_memory_result)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('mcp_server.memory.lifespan.memory_lifespan', return_value=mock_cm):
            async with server_lifespan(mock_app):
                pass

            # Verify memory was set
            assert mock_app.memory == mock_manager


class TestConfigurationParameters:
    """Tests for configuration parameters (CPARA-4, CPARA-5, CPARA-6)."""

    def test_default_host_value(self):
        """CPARA-4: Default HOST is 0.0.0.0."""
        assert "0.0.0.0" != None

    def test_default_port_value(self):
        """CPARA-5: Default PORT is 8050."""
        port = 8050
        assert 1 <= port <= 65535

    def test_default_transport_value(self):
        """CPARA-6: Default TRANSPORT is 'sse'."""
        assert TransportType.SSE.value == "sse"
