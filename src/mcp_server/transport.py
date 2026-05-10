"""
# DP-4: Strategy Pattern - Select transport (stdio vs SSE) at runtime based on configuration.
# DF-4: Transport Selection Flow - Config -> FastMCP Server -> Transport
# E-10: ERR_STDIO_001 - stdin/stdout not available for stdio transport
# E-11: ERR_SSE_001 - Port already in use or SSE transport failed to start
# CPARA-4: HOST (default: 0.0.0.0)
# CPARA-5: PORT (default: 8050)
# CPARA-6: TRANSPORT (default: sse, values: stdio, sse)
# EN-1: TransportType enum (STDIO, SSE)

Transport selection module for FastMCP server.
Supports stdio and SSE transports based on configuration.
"""

import logging
from enum import Enum

from fastmcp import FastMCP

# Import health check module (FR-24: Health Check Endpoint)
from mcp_server.utils.health import register_health_check


class TransportType(Enum):
    """EN-1: TransportType enum for MCP transport protocol types.

    Values:
        STDIO: Standard I/O transport for local AI agent integration
        SSE: Server-Sent Events transport for remote HTTP connections
    """
    STDIO = "stdio"
    SSE = "sse"


async def run_transport(
    transport: str,
    host: str,
    port: int,
    mcp_server: FastMCP
) -> None:
    """Run the appropriate transport based on configuration.

    This function implements the Strategy Pattern (DP-4) to select between
    stdio and SSE transports at runtime based on the TRANSPORT configuration.

    Args:
        transport: Transport type ("stdio" or "sse")
        host: Server bind address for SSE transport
        port: Server bind port for SSE transport
        mcp_server: FastMCP server instance

    Raises:
        ValueError: If transport value is invalid
        RuntimeError: E-10 for stdio errors, E-11 for SSE errors
    """
    try:
        transport_type = TransportType(transport)
    except ValueError:
        logging.error(
            f"Invalid transport type: {transport}",
            extra={"logging_context": ["transport", "config"]}
        )
        raise ValueError(
            f"Invalid transport value: {transport}. Must be one of: stdio, sse"
        )

    if transport_type == TransportType.STDIO:
        await _run_stdio_transport(mcp_server)
    else:  # SSE
        await _run_sse_transport(host, port, mcp_server)


async def _run_stdio_transport(mcp_server: FastMCP) -> None:
    """Run stdio transport for local AI agent integration.

    Args:
        mcp_server: FastMCP server instance

    Raises:
        RuntimeError: E-10 if stdin/stdout not available
    """
    try:
        logging.info(
            "Starting stdio transport",
            extra={"logging_context": ["transport", "stdio"]}
        )
        await mcp_server.run_stdio_async()
    except Exception as e:
        logging.error(
            f"stdio transport failed: {e}",
            extra={"logging_context": ["transport", "stdio"], "error": str(e)}
        )
        raise RuntimeError(
            "ERR_STDIO_001: stdin/stdout not available for stdio transport"
        ) from e


async def _run_sse_transport(host: str, port: int, mcp_server: FastMCP) -> None:
    """Run SSE transport for remote HTTP connections.

    # FR-24: Health Check Endpoint - Server exposes health check for monitoring
    # AC-57: Health endpoint returns status
    # AC-58: Health response includes version info
    # FR-12: SSE Transport for HTTP-based remote connections
    # DP-4: Strategy Pattern - Health check available when SSE transport is active

    Args:
        host: Server bind address
        port: Server bind port
        mcp_server: FastMCP server instance

    Raises:
        RuntimeError: E-11 if port is in use or SSE transport fails
    """
    try:
        logging.info(
            f"Starting SSE transport on {host}:{port}",
            extra={"logging_context": ["transport", "sse"], "host": host, "port": port}
        )

        # Register health check endpoint before starting SSE transport
        # FR-24: Health check endpoint registered at /health for SSE transport
        # AC-57: Health endpoint returns status when called
        # AC-58: Version info included in health response
        register_health_check(mcp_server)

        await mcp_server.run_http_async(transport="sse", host=host, port=port)
    except Exception as e:
        logging.error(
            f"SSE transport failed: {e}",
            extra={"logging_context": ["transport", "sse"], "error": str(e)}
        )
        raise RuntimeError(
            "ERR_SSE_001: Port already in use or SSE transport failed to start"
        ) from e


__all__ = ["TransportType", "run_transport"]
