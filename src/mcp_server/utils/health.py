"""
# FR-24: Health Check Endpoint - Server exposes health check for monitoring.
# AC-57: Health endpoint returns status
# AC-58: Health response includes version information
# FR-12: SSE Transport for HTTP-based remote connections
# DP-4: Strategy Pattern - Health check available when SSE transport is active
# CPARA-4: HOST (default: 0.0.0.0)
# CPARA-5: PORT (default: 8050)
# E-12: ERR_HEALTH_001 - Health check endpoint error

Health check endpoint module for MCP server monitoring.
Provides HTTP health check endpoint when SSE transport is active.
"""

import logging
from importlib.metadata import version as get_package_version
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

try:
    SERVER_VERSION = get_package_version("mem0-mcp-server")
except Exception:
    SERVER_VERSION = "1.0.0"


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring.

    # FR-24: Health Check Endpoint - Server exposes health check for monitoring
    # AC-57: Health endpoint returns status

    This endpoint returns JSON with status info.
    It is accessible at GET /health when SSE transport is active.

    Args:
        request: Starlette Request object (unused but required by FastMCP)

    Returns:
        JSONResponse with status: ok

    # E-12: ERR_HEALTH_001 - Health check endpoint error (if any exception occurs)
    """
    try:
        logger.debug(
            "Health check endpoint called",
            extra={"logging_context": ["health", "monitoring"]}
        )

        return JSONResponse(
            {
                "status": "ok",
                "version": SERVER_VERSION,
            }
        )
    except Exception as e:
        logger.error(
            f"Health check error: {e}",
            extra={"logging_context": ["health", "error"], "error": str(e)}
        )
        return JSONResponse(
            {
                "status": "error",
                "error": str(e),
            },
            status_code=500
        )


def register_health_check(mcp: "FastMCP") -> None:
    """Register the health check endpoint on the FastMCP server.

    # FR-24: Health Check Endpoint exposed via MCP server
    # AC-57: Health endpoint returns status
    # AC-58: Health response includes version info

    This function registers the /health endpoint using FastMCP's
    custom_route decorator. The route is available when SSE transport
    is active (when run_sse_async() is called).

    Args:
        mcp: FastMCP server instance to register the health check on
    """
    @mcp.custom_route("/health", methods=["GET"])
    async def health_endpoint(request: Request) -> JSONResponse:
        """Health check endpoint registered on MCP server.

        Returns:
            JSONResponse with status
        """
        return await health_check(request)

    logger.info(
        "Health check endpoint registered at /health",
        extra={"logging_context": ["health", "startup"]}
    )


__all__ = ["health_check", "register_health_check", "SERVER_VERSION"]
