"""
# FR-11: erase_memories Tool - Remove all memories for a user scope.
# CF-7: erase_memories core function - raw Mem0 AsyncMemory API passthrough
# E-10: ERR_400 - Invalid scope provided

MCP tool implementation for erasing all memories within a user scope.
Directly exposes Mem0 AsyncMemory.delete_all() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class EraseMemoriesInput(BaseModel):
    """Input model for erase_memories MCP tool.

    Raw Mem0 API parameters:
    - user_id: User identifier for the scope to erase (required)
    - agent_id: Agent identifier for more granular scope (optional)
    - run_id: Run identifier for more granular scope (optional)

    At least user_id is required per Mem0 API.
    """

    user_id: str = Field(
        ...,
        description="User identifier for memory scope to erase",
        max_length=255,
    )
    agent_id: str | None = Field(
        default=None,
        description="Agent identifier for more granular scope",
        max_length=255,
    )
    run_id: str | None = Field(
        default=None,
        description="Run identifier for more granular scope",
        max_length=255,
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id is non-empty string."""
        if not v or not v.strip():
            raise ValueError("user_id must be a non-empty string")
        return v

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str | None) -> str | None:
        """Validate agent_id is non-empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("agent_id cannot be empty if provided")
        return v

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str | None) -> str | None:
        """Validate run_id is non-empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("run_id cannot be empty if provided")
        return v

    def to_mem0_user_id(self) -> str:
        """Format Mem0-compatible user_id from scope components.

        Returns:
            Formatted user_id: {user_id}:{agent_id}:{run_id}
            Only includes non-None levels.
        """
        parts = [self.user_id]
        if self.agent_id:
            parts.append(self.agent_id)
        if self.run_id:
            parts.append(self.run_id)
        return ":".join(parts)


class EraseMemoriesOutput(BaseModel):
    """Output model for erase_memories MCP tool response."""

    status: str = Field(..., description="Status of the memory erasure operation")
    deleted: bool = Field(..., description="Whether all memories were successfully erased")


def register_erase_memories_tool(mcp: "FastMCP") -> None:
    """Register erase_memories MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.delete_all() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def erase_memories(
        user_id: str,
        agent_id: str | None = None,
        run_id: str | None = None,
        ctx: Context | None = None,
    ) -> EraseMemoriesOutput:
        """Erase all memories within a user scope.

        # FR-11: Erase all memories for a user scope
        # CF-7: erase_memories core function - raw Mem0 API passthrough

        This MCP tool directly exposes Mem0 AsyncMemory.delete_all() functionality.
        All memories for the specified user scope are permanently removed.

        Args:
            user_id: User identifier for memory scope to erase (required)
            agent_id: Optional agent identifier for more granular scope
            run_id: Optional run identifier for more granular scope
            ctx: FastMCP context for accessing lifespan state

        Returns:
            EraseMemoriesOutput with status and deleted confirmation

        Raises:
            ValueError: E-10 (ERR_400) if user_id is empty
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
        """
        if not user_id or not user_id.strip():
            raise ValueError("ERR_400: user_id is required and cannot be empty")

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

        input_model = EraseMemoriesInput(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
        )

        mem0_user_id = input_model.to_mem0_user_id()

        try:
            result = await memory.delete_all(user_id=mem0_user_id)

            logger.info(
                f"All memories erased for user scope: {mem0_user_id}",
                extra={
                    "logging_context": ["memory", "erase"],
                    "user_id": mem0_user_id,
                }
            )

            deleted = False
            if isinstance(result, dict):
                deleted = result.get("deleted", False) or result.get("status") == "deleted"
            elif isinstance(result, bool):
                deleted = result

            return EraseMemoriesOutput(
                status="erased" if deleted else "failed",
                deleted=deleted,
            )

        except Exception as e:
            logger.error(
                f"erase_memories failed: {e}",
                extra={"logging_context": ["memory", "erase"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: erase_memories failed - {e}") from e

    logger.debug("erase_memories tool registered successfully")
