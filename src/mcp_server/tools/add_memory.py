"""
# FR-4: add_memory Tool - Store information in long-term memory with semantic indexing.
# CF-1: add_memory core function - raw Mem0 AsyncMemory API passthrough
# E-2: ERR_MEM_001 - Mem0 AsyncMemory not initialized or unavailable

MCP tool implementation for storing information in long-term memory.
Directly exposes Mem0 AsyncMemory.add() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class AddMemoryInput(BaseModel):
    """Input model for add_memory MCP tool.

    Raw Mem0 API parameters:
    - messages: list of role/content dicts (required)
    - user_id: user identifier (optional*)
    - agent_id: agent identifier (optional)
    - run_id: run identifier (optional)
    - metadata: custom key-value metadata (optional)
    - infer: skip LLM inference if False (optional, default True)

    * At least one entity ID (user_id, agent_id, run_id) is required per Mem0 API
    """

    messages: list[dict[str, str]] = Field(
        ...,
        description="Conversation turns for Mem0 to extract memories from. Each dict must have 'role' and 'content'",
        min_length=1,
    )
    user_id: str | None = Field(
        default=None,
        description="User identifier for memory scoping",
        max_length=255,
    )
    agent_id: str | None = Field(
        default=None,
        description="Agent identifier for memory scoping",
        max_length=255,
    )
    run_id: str | None = Field(
        default=None,
        description="Run identifier for memory scoping",
        max_length=255,
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Custom key-value metadata (e.g., {'topic': 'preferences'})",
    )
    infer: bool = Field(
        default=True,
        description="Set to False to skip LLM inference and store text as-is",
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list) -> list:
        """Validate messages is non-empty list of valid role/content dicts."""
        if not v or len(v) == 0:
            raise ValueError("messages must be a non-empty list")
        for msg in v:
            if not isinstance(msg, dict):
                raise ValueError("Each message must be a dict with 'role' and 'content'")
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content' fields")
            content = msg.get("content")
            if not content or not content.strip():
                raise ValueError("message content cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_entity_ids(self) -> "AddMemoryInput":
        """Validate that at least one entity ID is provided.

        Mem0 API requires at least one of user_id, agent_id, or run_id.
        """
        if not self.user_id and not self.agent_id and not self.run_id:
            raise ValueError(
                "At least one entity ID (user_id, agent_id, or run_id) is required. "
                "Mem0 API requires at least one of these identifiers."
            )
        return self


class MemoryResult(BaseModel):
    """Result item from add_memory response."""

    id: str = Field(..., description="Unique identifier for the created memory")
    memory: str = Field(..., description="Memory content")
    metadata: dict[str, Any] | None = Field(default=None, description="Memory metadata")
    event: str = Field(..., description="Event type (e.g., 'ADD')")


class AddMemoryOutput(BaseModel):
    """Output model for add_memory MCP tool response."""

    results: list[MemoryResult] = Field(
        ..., description="List of created memory entries"
    )


def register_add_memory_tool(mcp: "FastMCP") -> None:
    """Register add_memory MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.add() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def add_memory(
        messages: list[dict[str, str]],
        user_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
        ctx: Context | None = None,
    ) -> AddMemoryOutput:
        """Store information in long-term memory with semantic indexing.

        # FR-4: Store information in long-term memory with semantic indexing
        # CF-1: add_memory core function - raw Mem0 API passthrough

        This MCP tool directly exposes Mem0 AsyncMemory.add() functionality.
        Content is stored with semantic indexing for later retrieval.

        Args:
            messages: List of message dicts with 'role' and 'content' (e.g., [{"role": "user", "content": "..."}])
            user_id: Optional user identifier for memory scoping
            agent_id: Optional agent identifier for memory scoping
            run_id: Optional run identifier for memory scoping
            metadata: Optional custom key-value metadata
            infer: If False, skip LLM inference and store text as-is (default True)
            ctx: FastMCP context for accessing lifespan state

        Returns:
            AddMemoryOutput with list of created memory entries

        Raises:
            ValueError: E-4 (ERR_400) if messages is invalid or no entity ID provided
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
        """
        input_model = AddMemoryInput(
            messages=messages,
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            metadata=metadata,
            infer=infer,
        )

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
            result = await memory.add(
                messages=input_model.messages,
                user_id=input_model.user_id,
                agent_id=input_model.agent_id,
                run_id=input_model.run_id,
                metadata=input_model.metadata,
                infer=input_model.infer,
            )

            logger.info(
                f"Memory stored successfully: {len(result.get('results', []))} entries",
                extra={
                    "logging_context": ["memory"],
                    "message_count": len(messages),
                }
            )

            results_list = result.get("results", []) if isinstance(result, dict) else []
            memory_results = [
                MemoryResult(
                    id=r.get("id", ""),
                    memory=r.get("memory", ""),
                    metadata=r.get("metadata"),
                    event=r.get("event", "ADD"),
                )
                for r in results_list
            ]

            return AddMemoryOutput(results=memory_results)

        except Exception as e:
            logger.error(
                f"add_memory failed: {e}",
                extra={"logging_context": ["memory", "add"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: add_memory failed - {e}") from e

    logger.debug("add_memory tool registered successfully")
