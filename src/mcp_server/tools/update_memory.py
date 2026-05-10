"""
# FR-6: update_memory Tool - Update existing memory content.
# CF-3: update_memory core function - raw Mem0 AsyncMemory API passthrough
# E-6: ERR_404 - Memory ID not found during update

MCP tool implementation for updating existing memory content.
Directly exposes Mem0 AsyncMemory.update() functionality via MCP protocol.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class UpdateMemoryInput(BaseModel):
    """Input model for update_memory MCP tool.

    Raw Mem0 API parameters:
    - memory_id: ID of memory to update (required)
    - content: New content for the memory (required)
    - metadata: Updated metadata to merge (optional)
    """

    memory_id: str = Field(
        ...,
        description="ID of memory to update",
        min_length=1,
        max_length=255,
    )
    content: str = Field(
        ...,
        description="New content for the memory",
        min_length=1,
        max_length=10000,
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional updated metadata to merge with existing metadata",
    )

    @field_validator("memory_id")
    @classmethod
    def validate_memory_id(cls, v: str) -> str:
        """Validate memory_id is non-empty string."""
        if not v or not v.strip():
            raise ValueError("memory_id must be a non-empty string")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty string."""
        if not v or not v.strip():
            raise ValueError("content must be a non-empty string")
        return v


class UpdateMemoryOutput(BaseModel):
    """Output model for update_memory MCP tool response."""

    status: str = Field(..., description="Status of the memory update operation")
    updated_at: str = Field(..., description="ISO timestamp of when the memory was updated")


def register_update_memory_tool(mcp: "FastMCP") -> None:
    """Register update_memory MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.update() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def update_memory(
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        ctx: Context | None = None,
    ) -> UpdateMemoryOutput:
        """Update existing memory content.

        # FR-6: Update existing memory content
        # CF-3: update_memory core function - raw Mem0 API passthrough
        # AC-17: Memory content is updated with new content
        # AC-18: Existing memory metadata preserved during update

        This MCP tool directly exposes Mem0 AsyncMemory.update() functionality.
        Metadata from the existing memory is preserved and merged with any
        new metadata provided.

        Args:
            memory_id: ID of memory to update (non-empty string, max 255 chars)
            content: New content for the memory (non-empty string, max 10000 chars)
            metadata: Optional metadata to update/merge with existing metadata
            ctx: FastMCP context for accessing lifespan state

        Returns:
            UpdateMemoryOutput with status and updated_at timestamp

        Raises:
            ValueError: If memory_id or content is invalid
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
            RuntimeError: E-6 (ERR_404) if memory not found during update
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
            result = await memory.update(
                memory_id=memory_id,
                data=content,
                metadata=metadata,
            )

            logger.info(
                f"Memory updated successfully: {memory_id}",
                extra={
                    "logging_context": ["memory", "update"],
                    "memory_id": memory_id,
                }
            )

            updated_at = None
            if isinstance(result, dict):
                updated_at = result.get("updated_at")

            if not updated_at:
                updated_at = datetime.now(UTC).isoformat()
                logger.warning(
                    f"Mem0 did not return updated_at for memory {memory_id}, using current timestamp",
                    extra={"logging_context": ["memory", "update"]}
                )

            return UpdateMemoryOutput(
                status="updated",
                updated_at=updated_at,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                logger.warning(
                    f"Memory not found during update: {memory_id}",
                    extra={"logging_context": ["memory", "update"]}
                )
                raise RuntimeError("ERR_404: Memory ID not found during update") from e
            logger.error(
                f"update_memory failed: {e}",
                extra={"logging_context": ["memory", "update"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: update_memory failed - {e}") from e

    logger.debug("update_memory tool registered successfully")
