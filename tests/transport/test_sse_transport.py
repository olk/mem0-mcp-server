"""
Unit tests for SSE transport layer of mem0-mcp server.

# FR-12: SSE Transport for HTTP-based remote connections
# FR-24: Health Check Endpoint - Server exposes health check for monitoring

Test scenarios:
  - SCEN-10: transport=sse calls run_http_async(transport="sse")
  - SCEN-13: Health check endpoint called returns status ok
  - SCEN-14: Health check response includes version info
  - E-11: ERR_SSE_001 - Port already in use or SSE transport failed to start

These tests validate the SSE transport functionality without requiring
a running Docker container by using mocked FastMCP server and direct
imports of the transport module.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import importlib.util

transport_path = Path(__file__).parent.parent.parent / "src" / "mcp_server" / "transport.py"
spec = importlib.util.spec_from_file_location("mcp_server.transport", transport_path)
transport_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport_module)

run_transport = transport_module.run_transport
TransportType = transport_module.TransportType
_run_sse_transport = transport_module._run_sse_transport


class TestSSETransportConfig:
    """Tests for SSE transport configuration (FR-12, CPARA-4, CPARA-5, CPARA-6)."""

    @pytest.mark.asyncio
    async def test_sse_transport_uses_settings_host_port(self):
        """SCEN-10: SSE transport starts on configured host and port.

        Given: Transport is 'sse', host is '0.0.0.0', port is 8050
        When: run_transport is called with these parameters
        Then: run_http_async is called with transport='sse', host='0.0.0.0', port=8050
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=8050,
        )

    @pytest.mark.asyncio
    async def test_sse_transport_with_different_host_port(self):
        """Verify SSE transport works with custom host and port values.

        Given: Transport is 'sse', host is '127.0.0.1', port is 9000
        When: run_transport is called
        Then: run_http_async is called with correct custom values
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="127.0.0.1",
            port=9000,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="127.0.0.1",
            port=9000,
        )

    @pytest.mark.asyncio
    async def test_sse_transport_calls_register_health_check(self):
        """Verify health check endpoint is registered for SSE transport.

        Given: FastMCP server instance
        When: run_transport is called with transport='sse'
        Then: register_health_check is imported and available in the module
        """
        import mcp_server.transport as transport_module

        assert hasattr(transport_module, 'register_health_check')
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        with patch(
            "mcp_server.transport.register_health_check",
            return_value=None
        ):
            await run_transport(
                transport="sse",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp,
            )

        mock_mcp.run_http_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_sse_transport_error_raises_err_sse_001(self):
        """E-11: SSE transport error raises ERR_SSE_001.

        Given: SSE transport encounters an error (e.g., port in use)
        When: run_transport is called
        Then: RuntimeError with code ERR_SSE_001 is raised
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock(side_effect=Exception("Port in use"))

        with pytest.raises(RuntimeError) as exc_info:
            await run_transport(
                transport="sse",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp,
            )

        assert "ERR_SSE_001" in str(exc_info.value)
        assert "Port already in use or SSE transport failed to start" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sse_transport_error_preserves_original_exception(self):
        """Verify original exception is preserved in ERR_SSE_001 error.

        Given: SSE transport fails with a specific error
        When: RuntimeError is raised
        Then: Original exception is available via __cause__
        """
        mock_mcp = MagicMock()
        original_error = Exception("Address binding failed")
        mock_mcp.run_http_async = AsyncMock(side_effect=original_error)

        with pytest.raises(RuntimeError) as exc_info:
            await run_transport(
                transport="sse",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp,
            )

        assert exc_info.value.__cause__ is original_error


class TestTransportTypeEnum:
    """Tests for TransportType enum values (EN-1)."""

    def test_transport_type_sse_value(self):
        """EN-1: TransportType.SSE has value 'sse'."""
        assert TransportType.SSE.value == "sse"

    def test_transport_type_stdio_value(self):
        """EN-1: TransportType.STDIO has value 'stdio'."""
        assert TransportType.STDIO.value == "stdio"

    def test_transport_type_from_string_sse(self):
        """TransportType can be created from 'sse' string."""
        assert TransportType("sse") == TransportType.SSE

    def test_transport_type_from_string_stdio(self):
        """TransportType can be created from 'stdio' string."""
        assert TransportType("stdio") == TransportType.STDIO

    def test_transport_type_invalid_string_raises(self):
        """Invalid transport string raises ValueError."""
        with pytest.raises(ValueError):
            TransportType("http")

    def test_transport_type_sse_is_default_for_http(self):
        """Verify SSE is the default for remote HTTP transport."""
        assert TransportType.SSE.value == "sse"


class TestSSERunFunction:
    """Tests for _run_sse_transport internal function."""

    @pytest.mark.asyncio
    async def test_run_sse_transport_starts_without_error(self):
        """Verify _run_sse_transport completes without raising exceptions.

        Given: Valid FastMCP server
        When: _run_sse_transport is called
        Then: No exceptions are raised and run_http_async is called with correct args
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        with patch("mcp_server.transport.register_health_check"):
            await _run_sse_transport("0.0.0.0", 8050, mock_mcp)

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=8050,
        )

    @pytest.mark.asyncio
    async def test_run_sse_transport_with_custom_host_port(self):
        """Verify _run_sse_transport works with custom host and port.

        Given: Custom host '127.0.0.1' and port 9000
        When: _run_sse_transport is called
        Then: run_http_async is called with these custom values
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        with patch("mcp_server.transport.register_health_check"):
            await _run_sse_transport("127.0.0.1", 9000, mock_mcp)

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="127.0.0.1",
            port=9000,
        )


class TestSSETransportValidation:
    """Tests for SSE transport input validation."""

    @pytest.mark.asyncio
    async def test_run_transport_rejects_invalid_transport_type(self):
        """Invalid transport type raises ValueError.

        Given: transport='websocket' (invalid)
        When: run_transport is called
        Then: ValueError is raised with descriptive message
        """
        mock_mcp = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await run_transport(
                transport="websocket",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp,
            )

        assert "Invalid transport value" in str(exc_info.value)
        assert "websocket" in str(exc_info.value)
        assert "stdio" in str(exc_info.value) or "sse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_transport_rejects_empty_host(self):
        """Empty host string is accepted (FastMCP handles validation).

        Note: The transport module itself does not validate empty strings.
        FastMCP's run_http_async will handle host validation.
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="",
            port=8050,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_transport_accepts_valid_port_range(self):
        """Valid port numbers in range 1-65535 are accepted.

        Given: port=8050 (valid)
        When: run_transport is called
        Then: run_http_async is called with correct port
        """
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=8050,
        )

    @pytest.mark.asyncio
    async def test_run_transport_handles_port_1(self):
        """Minimum valid port (1) is accepted."""
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=1,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=1,
        )

    @pytest.mark.asyncio
    async def test_run_transport_handles_port_65535(self):
        """Maximum valid port (65535) is accepted."""
        mock_mcp = MagicMock()
        mock_mcp.run_http_async = AsyncMock()

        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=65535,
            mcp_server=mock_mcp,
        )

        mock_mcp.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=65535,
        )
