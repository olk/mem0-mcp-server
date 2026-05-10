"""
# FR-5: search_memories Tool - Search memories using semantic similarity.
# CF-2: search_memories core function - raw Mem0 AsyncMemory API passthrough
# E-3: ERR_VEC_001 - Vector store connection failed during search

MCP tool implementation for searching long-term memory using semantic similarity.
Directly exposes Mem0 AsyncMemory.search() functionality via MCP protocol.
"""

import logging
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class SearchMemoriesInput(BaseModel):
    """Input model for search_memories MCP tool.

    Raw Mem0 API parameters:
    - query: search query text (required)
    - filters: Filter object with entity IDs (user_id, agent_id, app_id, run_id) and/or metadata filters
    - limit: max results (optional, default 10)
    - page: page number for pagination (optional)
    - page_size: number of results per page (optional)
    - rerank: enable/disable reranking (optional, default None uses config default)

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

    Pagination:
    - page: Page number (default: 1)
    - page_size: Results per page (default: 100, max: 100)
    """

    query: str = Field(
        ...,
        description="Search query text for semantic similarity search",
        min_length=1,
        max_length=1000,
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filter object with entity IDs and/or metadata filters for advanced search",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    page: int | None = Field(
        default=None,
        description="Page number for pagination (default: 1)",
        ge=1,
    )
    page_size: int | None = Field(
        default=None,
        description="Number of results per page (default: 100)",
        ge=1,
        le=100,
    )
    rerank: bool | None = Field(
        default=None,
        description="Enable or disable reranking. If None, uses reranker config default if configured.",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is non-empty string."""
        if not v or not v.strip():
            raise ValueError("query must be a non-empty string")
        return v

    @model_validator(mode="after")
    def validate_entity_ids_in_filters(self) -> "SearchMemoriesInput":
        """Validate that at least one entity ID is provided in filters.

        Mem0 API requires at least one of user_id, agent_id, app_id, or run_id in filters.
        """
        entity_ids = ["user_id", "agent_id", "app_id", "run_id"]
        if self.filters:
            has_entity_id = any(key in self.filters for key in entity_ids)
            if not has_entity_id:
                raise ValueError(
                    "At least one entity ID (user_id, agent_id, app_id, or run_id) is required in filters. "
                    "Mem0 API requires at least one of these identifiers."
                )
        return self


class MemorySearchResult(BaseModel):
    """Individual memory result with relevance score.

    # AC-14: Returns matching memories with scores
    # FR-23: Reranker support - includes rerank_score when reranking is applied
    """

    memory_id: str = Field(..., description="Unique identifier for the memory")
    content: str = Field(..., description="Memory content text")
    score: float = Field(..., description="Relevance score (0.0 to 1.0)", ge=0.0, le=1.0)
    rerank_score: float | None = Field(
        default=None,
        description="Reranker score after reranking (0.0 to 1.0), present when reranking is applied",
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Memory metadata")


class SearchMemoriesOutput(BaseModel):
    """Output model for search_memories MCP tool response."""

    results: list[MemorySearchResult] = Field(
        ..., description="List of matching memories ranked by relevance score"
    )


def register_search_memories_tool(mcp: "FastMCP") -> None:
    """Register search_memories MCP tool with the FastMCP server.

    Directly exposes Mem0 AsyncMemory.search() via MCP protocol.
    No custom multi-tenant wrapper - raw API passthrough.

    Args:
        mcp: FastMCP server instance to register the tool with
    """
    @mcp.tool()
    async def search_memories(
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        page: int | None = None,
        page_size: int | None = None,
        rerank: bool | None = None,
        ctx: Context | None = None,
    ) -> SearchMemoriesOutput:
        """Search memories using semantic similarity.

        # FR-5: Search memories using semantic similarity
        # CF-2: search_memories core function - raw Mem0 API passthrough
        # FR-23: Reranker Support - rerank parameter enables/disables reranking

        This MCP tool directly exposes Mem0 AsyncMemory.search() functionality.
        Entity IDs (user_id, agent_id, app_id, run_id) must be passed inside the filters object.
        Supports complex logical operations (AND, OR, NOT) and comparison operators.
        Returns memories ranked by semantic similarity to the query.

        Args:
            query: Search query text (non-empty string, max 1000 chars)
            filters: Filter object with entity IDs and/or metadata filters (e.g., {"AND": [{"user_id": "alice"}, {"created_at": {"gte": "2024-01-01"}}]})
            limit: Maximum number of results to return (default: 10, max: 100)
            page: Page number for pagination (optional, default: 1)
            page_size: Number of results per page (optional, default: 100, max: 100)
            rerank: Enable or disable reranking (optional, uses config default if not specified)
            ctx: FastMCP context for accessing lifespan state

        Returns:
            SearchMemoriesOutput with list of matching memories with relevance scores

        Raises:
            ValueError: E-5 (ERR_400) if query is invalid/empty or no entity ID in filters
            RuntimeError: E-3 (ERR_VEC_001) if vector store connection fails
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

        if not query or not query.strip():
            return SearchMemoriesOutput(results=[])

        input_filters = filters if filters is not None else {}
        input_model = SearchMemoriesInput(query=query, filters=input_filters, limit=limit, page=page, page_size=page_size, rerank=rerank)

        search_kwargs: dict[str, Any] = {
            "query": input_model.query,
            "filters": input_model.filters,
            "top_k": input_model.limit,
        }
        if input_model.page is not None:
            search_kwargs["page"] = input_model.page
        if input_model.page_size is not None:
            search_kwargs["page_size"] = input_model.page_size
        if input_model.rerank is not None:
            search_kwargs["rerank"] = input_model.rerank

        try:
            result = await memory.search(**search_kwargs)

            results_list = result.get("results", []) if isinstance(result, dict) else result if result else []

            search_results = []
            for r in results_list:
                score = r.get("score", 0.0) if isinstance(r, dict) else 0.0
                rerank_score = r.get("rerank_score") if isinstance(r, dict) else None
                memory_id = r.get("id", "") if isinstance(r, dict) else ""
                content = r.get("memory", "") if isinstance(r, dict) else str(r)
                metadata = r.get("metadata") if isinstance(r, dict) else None

                search_results.append(
                    MemorySearchResult(
                        memory_id=memory_id,
                        content=content,
                        score=score,
                        rerank_score=rerank_score,
                        metadata=metadata,
                    )
                )

            logger.info(
                f"Search completed: {len(search_results)} results for query",
                extra={
                    "logging_context": ["search"],
                    "query_length": len(query),
                    "result_count": len(search_results),
                }
            )

            return SearchMemoriesOutput(results=search_results)

        except ValueError:
            raise
        except ConnectionError as e:
            logger.error(
                f"Vector store connection failed during search: {e}",
                extra={"logging_context": ["vector", "search"]}
            )
            raise RuntimeError("ERR_VEC_001: Vector store connection failed during search") from e
        except Exception as e:
            logger.error(
                f"search_memories failed: {e}",
                extra={"logging_context": ["memory", "search"], "error": str(e)}
            )
            raise RuntimeError(f"ERR_500: search_memories failed - {e}") from e

    logger.debug("search_memories tool registered successfully")
