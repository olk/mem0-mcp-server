"""
# FR-1: MCP Protocol Integration - The server MUST implement MCP specification for AI agent tool exposure.
# IC-2: Exactly one FastMCP instance MUST exist, named 'Mem0-MCP Server' with description 'Server exposes Mem0 API via MCP'
# IC-5: All @mcp.tool decorators MUST bind to the single FastMCP instance registered at startup.
# E-1: ERR_MCP_INIT - Multiple FastMCP instances detected or initialization failed

FastMCP server initialization with single instance named Mem0-MCP Server.
All @mcp.tool decorators in the tools module MUST bind to this single mcp instance.
"""

import logging
import threading

from fastmcp import FastMCP

from mcp_server.lifespan import server_lifespan

# Module-level singleton tracking to enforce IC-2 (exactly one FastMCP instance)
_mcp_instance: FastMCP | None = None
_mcp_instance_count: int = 0
_mcp_lock: threading.Lock = threading.Lock()


def get_mcp_instance() -> FastMCP:
    """Get or create the single FastMCP instance.

    This function implements the singleton pattern to ensure exactly one
    FastMCP instance exists (IC-2). On subsequent calls after the first
    instance is created, it raises E-1 error.

    Returns:
        FastMCP: The single FastMCP instance

    Raises:
        RuntimeError: E-1 if multiple instances are detected
    """
    global _mcp_instance, _mcp_instance_count

    with _mcp_lock:
        if _mcp_instance is not None:
            logging.error(
                "Multiple FastMCP instances detected",
                extra={"logging_context": ["startup", "initialization"]}
            )
            raise RuntimeError(
                "ERR_MCP_INIT: Multiple FastMCP instances detected or initialization failed"
            )

        _mcp_instance = FastMCP(
            name="Mem0-MCP Server",
            instructions="Server exposes Mem0 API via MCP",
            lifespan=server_lifespan
        )
        _mcp_instance_count += 1

    logging.info(
        "FastMCP instance created",
        extra={
            "logging_context": ["startup", "initialization"],
            "instance_name": "Mem0-MCP Server",
            "instance_description": "Server exposes Mem0 API via MCP"
        }
    )

    return _mcp_instance


def reset_mcp_instance() -> None:
    """Reset the MCP instance (for testing purposes only).

    This function is intended for testing scenarios where the singleton
    needs to be reset between test cases.
    """
    global _mcp_instance, _mcp_instance_count

    with _mcp_lock:
        _mcp_instance = None
        _mcp_instance_count = 0


# Create the single FastMCP instance (IC-2, IC-5)
# All @mcp.tool decorators in tools/ module bind to this instance
mcp: FastMCP = get_mcp_instance()

__all__ = ["mcp", "get_mcp_instance", "reset_mcp_instance"]
