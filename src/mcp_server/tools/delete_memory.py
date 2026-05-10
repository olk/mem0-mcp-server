"""
# FR-7: delete_memory Tool - Remove memory from storage.
# CF-4: delete_memory core function - raw Mem0 AsyncMemory API passthrough
# E-7: ERR_404 - Memory ID not found during delete

MCP tool implementation for removing memory from storage.
Directly exposes Mem0 AsyncMemory.delete() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class DeleteMemoryInput(BaseModel):
    """Input model for delete_memory MCP tool.

    Raw Mem0 API parameters:
    - memory_id: ID of memory to delete (required)
    """

    memory_id: str = Field(
        ...,
        description="ID of memory to delete",
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


class DeleteMemoryOutput(BaseModel):
    """Output model for delete_memory MCP tool response."""

    status: str = Field(..., description="Status of the memory deletion operation")
    deleted: bool = Field(..., description="Whether the memory was successfully deleted")


def register_delete_memory_tool(mcp: "FastMCP") -> None:
    """Register delete_memory MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.delete() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def delete_memory(
        memory_id: str,
        ctx: Context | None = None,
    ) -> DeleteMemoryOutput:
        """Remove memory from storage.

        # FR-7: Remove memory from storage
        # CF-4: delete_memory core function - raw Mem0 API passthrough
        # AC-20: Memory deleted from storage
        # AC-21: Deletion confirmation returned

        This MCP tool directly exposes Mem0 AsyncMemory.delete() functionality.
        The specified memory is permanently removed from storage.

        Args:
            memory_id: ID of memory to delete (non-empty string, max 255 chars)
            ctx: FastMCP context for accessing lifespan state

        Returns:
            DeleteMemoryOutput with status and deleted confirmation

        Raises:
            ValueError: If memory_id is invalid
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
            RuntimeError: E-7 (ERR_404) if memory not found during delete
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
            result = await memory.delete(memory_id=memory_id)

            logger.info(
                f"Memory deleted successfully: {memory_id}",
                extra={
                    "logging_context": ["memory", "delete"],
                    "memory_id": memory_id,
                }
            )

            deleted = False
            if isinstance(result, dict):
                deleted = result.get("deleted", False) or result.get("status") == "deleted"
            elif isinstance(result, bool):
                deleted = result

            return DeleteMemoryOutput(
                status="deleted" if deleted else "failed",
                deleted=deleted,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                logger.warning(
                    f"Memory not found during delete: {memory_id}",
                    extra={"logging_context": ["memory", "delete"]}
                )
                raise RuntimeError("ERR_404: Memory ID not found during delete") from e
            logger.error(
                f"delete_memory failed: {e}",
                extra={"logging_context": ["memory", "delete"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: delete_memory failed - {e}") from e

    logger.debug("delete_memory tool registered successfully")
