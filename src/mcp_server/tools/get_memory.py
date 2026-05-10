"""
# FR-8: get_memory Tool - Retrieve specific memory by ID.
# CF-5: get_memory core function - raw Mem0 AsyncMemory API passthrough
# E-8: ERR_404 - Memory ID not found

MCP tool implementation for retrieving specific memory by ID.
Directly exposes Mem0 AsyncMemory.get() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class GetMemoryInput(BaseModel):
    """Input model for get_memory MCP tool.

    Raw Mem0 API parameters:
    - memory_id: ID of memory to retrieve (required)
    """

    memory_id: str = Field(
        ...,
        description="ID of memory to retrieve",
        min_length=1,
        max_length=255,
    )

    @field_validator("memory_id")
    @classmethod
    def validate_memory_id(cls, v: str) -> str:
        """Validate memory_id is non-empty string."""
        if not v or not v.strip():
            raise ValueError("memory_id must be a non-empty string")
        return v


class GetMemoryOutput(BaseModel):
    """Output model for get_memory MCP tool response.

    # AC-23: Returns memory content and metadata
    """

    memory_id: str = Field(..., description="Unique identifier for the memory")
    content: str = Field(..., description="Memory content stored in the system")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    created_at: str | None = Field(None, description="ISO timestamp of creation")
    updated_at: str | None = Field(None, description="ISO timestamp of last update")


def register_get_memory_tool(mcp: "FastMCP") -> None:
    """Register get_memory MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.get() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def get_memory(
        memory_id: str,
        ctx: Context | None = None,
    ) -> GetMemoryOutput:
        """Retrieve specific memory by ID.

        # FR-8: Retrieve specific memory by ID
        # CF-5: get_memory core function - raw Mem0 API passthrough
        # AC-23: Memory content and metadata returned to caller

        This MCP tool directly exposes Mem0 AsyncMemory.get() functionality.
        Returns full memory details including content, metadata, and timestamps.

        Args:
            memory_id: ID of memory to retrieve (non-empty string, max 255 chars)
            ctx: FastMCP context for accessing lifespan state

        Returns:
            GetMemoryOutput with memory details (content, metadata, timestamps)

        Raises:
            ValueError: E-8 (ERR_404) if memory_id is invalid
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
            RuntimeError: E-8 (ERR_404) if memory not found
        """
        memory = None
        if ctx is not None and hasattr(ctx, 'request_context') and ctx.request_context is not None:
            lifespan_context = getattr(ctx.request_context, 'lifespan_context', None)
            if lifespan_context is not None:
                memory = lifespan_context.get("memory")

        if memory is None:
            logger.error(
                "AsyncMemory not available via context",
                extra={"logging_context": ["memory", "lifecycle"]}
            )
            raise RuntimeError(
                "ERR_MEM_001: Mem0 AsyncMemory not initialized or unavailable"
            )

        try:
            result = await memory.get(memory_id=memory_id)

            logger.info(
                f"Memory retrieved successfully: {memory_id}",
                extra={
                    "logging_context": ["memory", "get"],
                    "memory_id": memory_id,
                }
            )

            if isinstance(result, dict):
                return GetMemoryOutput(
                    memory_id=result.get("id", memory_id),
                    content=result.get("memory", ""),
                    metadata=result.get("metadata") or {},
                    created_at=result.get("created_at") or None,
                    updated_at=result.get("updated_at") or None,
                )

            return GetMemoryOutput(
                memory_id=memory_id,
                content=str(result) if result else "",
                metadata={},
                created_at=None,
                updated_at=None,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "does not exist" in error_msg:
                logger.warning(
                    f"Memory not found during get: {memory_id}",
                    extra={"logging_context": ["memory", "get"]}
                )
                raise RuntimeError("ERR_404: Memory ID not found during get") from e
            logger.error(
                f"get_memory failed: {e}",
                extra={"logging_context": ["memory", "get"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: get_memory failed - {e}") from e

    logger.debug("get_memory tool registered successfully")
