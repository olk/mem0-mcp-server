"""
UT-4: Component tests for COMP-2 FastMCP Server transport selection
Validates: FR-18 (Transport Selection), IC-4 (Correct transport function selection)

Test scenarios:
  - SCEN-10: transport=sse calls run_http_async (AC-45)
  - SCEN-11: transport=stdio calls run_stdio_async (AC-46)
  - SCEN-12: invalid transport raises error (E-16)

FR-18: Transport Selection - Server selects transport based on configuration.
IC-4: The server MUST run using run_http_async(transport="sse") when transport='sse'
      and run_stdio_async() when transport='stdio'.
AC-45: transport=sse calls run_http_async(transport="sse")
AC-46: transport=stdio calls run_stdio_async()
E-16: ERR_TRANS_001 - Invalid transport configuration

This module implements DP-4: Strategy Pattern for transport selection.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Direct import of the transport.py module (not the transport package)
# This avoids the package/namespace conflict with src/mcp_server/transport/
transport_path = Path(__file__).parent.parent.parent / "src" / "mcp_server" / "transport.py"

# Load the transport module directly using exec
import importlib.util

spec = importlib.util.spec_from_file_location("mcp_server.transport", transport_path)
transport_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport_module)

run_transport = transport_module.run_transport
TransportType = transport_module.TransportType


@pytest.fixture
def mock_mcp_server():
    """Create mock FastMCP server with async transport methods.

    This fixture provides a mock FastMCP server for testing transport
    selection without requiring actual server initialization.
    """
    server = MagicMock()
    server.run_stdio_async = AsyncMock()
    server.run_http_async = AsyncMock()
    return server


class TestTransportSelection:
    """Tests for FR-18 Transport Selection and IC-4 constraint.

    These tests verify that the server correctly selects and calls
    the appropriate transport function based on the TRANSPORT configuration.
    """

    @pytest.mark.asyncio
    async def test_sse_transport_calls_run_http_async(self, mock_mcp_server):
        """SCEN-10 / AC-45: transport=sse calls run_http_async(transport="sse").

        Given precondition: transport=sse in config
        When action: Server starts
        Then outcome: run_http_async(transport="sse") called

        This test validates IC-4 constraint for SSE transport selection.
        """
        # FR-18: Transport Selection based on configuration
        # IC-4: MUST run run_http_async(transport="sse") when transport='sse'
        await run_transport(
            transport="sse",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp_server
        )

        # Verify run_http_async was called with correct transport, host and port
        mock_mcp_server.run_http_async.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=8050
        )

    @pytest.mark.asyncio
    async def test_stdio_transport_calls_run_stdio_async(self, mock_mcp_server):
        """SCEN-11 / AC-46: transport=stdio calls run_stdio_async().

        Given precondition: transport=stdio in config
        When action: Server starts
        Then outcome: run_stdio_async() called

        This test validates IC-4 constraint for stdio transport selection.
        """
        # FR-18: Transport Selection based on configuration
        # IC-4: MUST run run_stdio_async() when transport='stdio'
        await run_transport(
            transport="stdio",
            host="0.0.0.0",
            port=8050,
            mcp_server=mock_mcp_server
        )

        # Verify run_stdio_async was called
        mock_mcp_server.run_stdio_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_transport_raises_error(self, mock_mcp_server):
        """SCEN-12: invalid transport raises E-16 (ERR_TRANS_001).

        When action: Server starts with invalid transport config
        Then outcome: ValueError raised with ERR_TRANS_001 message

        This test validates error handling for invalid transport values.
        """
        # E-16: ERR_TRANS_001 - Invalid transport configuration
        with pytest.raises(ValueError) as exc_info:
            await run_transport(
                transport="invalid",
                host="0.0.0.0",
                port=8050,
                mcp_server=mock_mcp_server
            )

        # Verify error message contains expected text
        assert "Invalid transport value" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestTransportTypeEnum:
    """Tests for EN-1 TransportType enum values.

    Validates that the TransportType enum correctly represents
    the supported transport protocols.
    """

    def test_transport_type_enum_values(self):
        """EN-1: TransportType enum has correct STDIO and SSE values."""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.SSE.value == "sse"

    def test_transport_type_from_string_stdio(self):
        """TransportType can be created from 'stdio' string."""
        assert TransportType("stdio") == TransportType.STDIO

    def test_transport_type_from_string_sse(self):
        """TransportType can be created from 'sse' string."""
        assert TransportType("sse") == TransportType.SSE

    def test_transport_type_invalid_string_raises(self):
        """Invalid transport string raises ValueError."""
        with pytest.raises(ValueError):
            TransportType("invalid")
