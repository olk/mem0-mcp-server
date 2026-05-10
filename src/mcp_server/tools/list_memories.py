"""
# FR-9: list_memories Tool - List memories with filtering and limit.
# CF-6: list_memories core function - raw Mem0 AsyncMemory API passthrough
# E-2: ERR_MEM_001 - Mem0 AsyncMemory not initialized or unavailable

MCP tool implementation for listing memories with filtering and limit.
Directly exposes Mem0 AsyncMemory.get_all() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ListMemoriesInput(BaseModel):
    """Input model for list_memories MCP tool.

    Raw Mem0 API parameters:
    - filters: Filter object with entity IDs (user_id, agent_id, app_id, run_id) and/or metadata filters
    - limit: Maximum number of results to return (default 50, max 100)

    Filter operators supported:
    - in: Matches any of the values specified
    - gte: Greater than or equal to
    - lte: Less than or equal to
    - gt: Greater than
    - lt: Less than
    - ne: Not equal to
    - icontains: Case-insensitive containment check
    - *: Wildcard character that matches everything

    Logical operators:
    - AND: All conditions must match
    - OR: Any condition must match
    - NOT: Negate the condition
    """

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filter object with entity IDs and/or metadata filters. At least one entity ID (user_id, agent_id, app_id, run_id) is required.",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of results to return (default: 50, max: 100)",
        ge=1,
        le=100,
    )

    @model_validator(mode="after")
    def validate_entity_ids_in_filters(self) -> "ListMemoriesInput":
        """Validate that at least one entity ID is provided in filters.

        Mem0 API requires at least one of user_id, agent_id, app_id, or run_id in filters.
        """
        entity_ids = ["user_id", "agent_id", "app_id", "run_id"]
        if not any(key in self.filters for key in entity_ids):
                raise ValueError(
                    "At least one entity ID (user_id, agent_id, app_id, or run_id) is required in filters. "
                    "Mem0 API requires at least one of these identifiers."
                )
        return self


class MemoryResponse(BaseModel):
    """Output model for a single memory in list_memories response."""

    memory_id: str = Field(..., description="Unique identifier for the memory")
    content: str = Field(..., description="Memory content stored in the system")
    user_id: str | None = Field(default=None, description="User identifier")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    app_id: str | None = Field(default=None, description="App identifier")
    run_id: str | None = Field(default=None, description="Run identifier")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    created_at: str | None = Field(None, description="ISO timestamp of creation")
    updated_at: str | None = Field(None, description="ISO timestamp of last update")


class ListMemoriesOutput(BaseModel):
    """Output model for list_memories MCP tool response."""

    memories: list[MemoryResponse] = Field(
        default_factory=list,
        description="List of memories matching filter criteria",
    )
    limit: int = Field(..., description="Maximum number of results requested")
    total_count: int | None = Field(None, description="Total count of memories matching filters")


def register_list_memories_tool(mcp: "FastMCP") -> None:
    """Register list_memories MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.get_all() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def list_memories(
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        ctx: Context | None = None,
    ) -> ListMemoriesOutput:
        """List memories with filtering and limit.

        # FR-9: List memories with filtering and limit
        # CF-6: list_memories core function - raw Mem0 API passthrough
        # AC-24: userId filter supported
        # AC-26: Returns memory list

        This MCP tool directly exposes Mem0 AsyncMemory.get_all() functionality.
        Entity IDs (user_id, agent_id, app_id, run_id) must be passed inside the filters object.
        Supports complex logical operations (AND, OR, NOT) and comparison operators.

        Args:
            filters: Filter object with entity IDs and/or metadata filters (e.g., {"AND": [{"user_id": "alice"}, {"created_at": {"gte": "2024-01-01"}}]})
            limit: Maximum number of results to return (default: 50, max: 100)
            ctx: FastMCP context for accessing lifespan state

        Returns:
            ListMemoriesOutput with list of memories matching criteria

        Raises:
            ValueError: If no entity ID provided in filters
            RuntimeError: E-2 (ERR_MEM_001) if memory not initialized
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

        input_filters = filters if filters is not None else {}

        input_model = ListMemoriesInput(filters=input_filters, limit=limit)

        try:
            result = await memory.get_all(
                filters=input_model.filters,
                page_size=input_model.limit,
            )

            memories_list = []
            total_count = None
            if isinstance(result, dict):
                results_items = result.get("results", [])
                if isinstance(results_items, list):
                    memories_list = results_items
                else:
                    memories_list = [results_items] if results_items else []
                total_count = result.get("count")
            elif isinstance(result, list):
                memories_list = result

            memories = []
            for r in memories_list:
                if isinstance(r, dict):
                    memories.append(MemoryResponse(
                        memory_id=r.get("id", ""),
                        content=r.get("memory", ""),
                        user_id=r.get("user_id"),
                        agent_id=r.get("agent_id"),
                        app_id=r.get("app_id"),
                        run_id=r.get("run_id"),
                        metadata=r.get("metadata") or {},
                        created_at=r.get("created_at"),
                        updated_at=r.get("updated_at"),
                    ))

            logger.info(
                f"Listed {len(memories)} memories successfully",
                extra={
                    "logging_context": ["memory", "list"],
                    "count": len(memories),
                    "limit": limit,
                }
            )

            return ListMemoriesOutput(
                memories=memories,
                limit=limit,
                total_count=total_count,
            )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"list_memories failed: {e}",
                extra={"logging_context": ["memory", "list"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: list_memories failed - {e}") from e

    logger.debug("list_memories tool registered successfully")
