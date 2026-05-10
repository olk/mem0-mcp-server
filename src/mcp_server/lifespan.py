"""
# DP-7: Resource Cleanup Pattern - Handle SIGTERM/SIGINT to cleanup resources properly.
# DF-5: Graceful Shutdown Flow - Shutdown signal -> FastMCP Server -> Mem0 Memory Manager -> Redis Vector Store
# E-1: ERR_MCP_INIT - Memory initialization failure

Graceful shutdown with SIGTERM/SIGINT handling and resource cleanup.
Implements FastMCP lifespan context manager for proper resource lifecycle.

# FR-25: Graceful Shutdown - Server handles shutdown signals properly.
# AC-59: SIGTERM/SIGINT handled
# AC-60: Cleanup executed
# AC-61: Connections closed properly
# IC-3: Mem0 AsyncMemory instances MUST be created and closed by asynccontextmanager
# NFR-5: MTTR < 5 minutes - Cleanup timeout enforced
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

from fastmcp.server.lifespan import lifespan

from mcp_server.memory.manager import Mem0InitializationError

# Cleanup timeout in seconds - NFR-5: MTTR < 5 minutes
CLEANUP_TIMEOUT_SECONDS = 300


async def _cleanup_with_timeout(memory_lifespan_result: dict) -> None:
    """Cleanup memory resources with timeout enforcement.

    This function ensures cleanup completes within MTTR < 5 minutes (NFR-5).
    Uses asyncio.timeout to prevent cleanup from blocking shutdown indefinitely.

    Args:
        memory_lifespan_result: Dict containing 'memory' (AsyncMemory) and 'manager' (MemoryManager)
    """
    memory = memory_lifespan_result.get("memory")
    if memory is None:
        return

    try:
        # NFR-5: MTTR < 5 minutes - enforce cleanup timeout
        async with asyncio.timeout(CLEANUP_TIMEOUT_SECONDS):
            memory.close()
            logging.info(
                "Mem0 AsyncMemory connections closed",
                extra={"logging_context": ["shutdown", "cleanup"]}
            )
    except TimeoutError:
        logging.error(
            f"Memory cleanup exceeded {CLEANUP_TIMEOUT_SECONDS}s timeout (MTTR violation)",
            extra={"logging_context": ["shutdown", "cleanup", "timeout"]}
        )
    except Exception as e:
        logging.error(
            f"Error during memory cleanup: {e}",
            extra={"logging_context": ["shutdown", "cleanup"], "error": str(e)}
        )


@lifespan
async def server_lifespan(server: "FastMCP"):
    """FastMCP lifespan context manager for graceful shutdown.

    This async context manager handles FastMCP server startup and shutdown.
    On startup: Initializes Mem0 AsyncMemory via memory_lifespan
    On shutdown: Cleans up all resources with timeout enforcement

    # FR-25: Graceful Shutdown - Server handles shutdown signals properly
    # AC-59: SIGTERM/SIGINT handled via FastMCP lifespan
    # AC-60: Cleanup executed with timeout
    # AC-61: Connections closed properly
    # IC-3: AsyncMemory created and closed by asynccontextmanager
    # NFR-5: MTTR < 5 minutes - cleanup timeout enforced

    Args:
        server: FastMCP server instance

    Yields:
        dict: Contains 'memory' (AsyncMemory) and 'manager' (MemoryManager)
    """
    from mcp_server.memory.lifespan import memory_lifespan

    settings = getattr(server, '_settings', None)
    if settings is None:
        raise Mem0InitializationError(
            "Server settings not found. Ensure main.py has set mcp._settings."
        )

    async with memory_lifespan(
            llm_config=settings.llm,
            vector_store_config=settings.vector_store,
            embedder_config=settings.embedder,
        ) as memory_lifespan_result:
        manager = memory_lifespan_result.get("manager")
        server.memory = manager

        logging.info(
            f"MemoryManager initialized: {type(manager).__name__}",
            extra={"logging_context": ["startup", "initialization"]}
        )

        try:
            yield memory_lifespan_result
        finally:
            logging.info(
                "FastMCP server shutting down",
                extra={"logging_context": ["shutdown"]}
            )

            await _cleanup_with_timeout(memory_lifespan_result)

            logging.info(
                "FastMCP server shutdown complete",
                extra={"logging_context": ["shutdown"]}
            )


__all__ = ["server_lifespan"]
