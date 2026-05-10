"""
# FR-10: Multi-tenant Support - The server MUST support multiple users, agents, and applications with isolated memory spaces.
# FR-20: Multi-LLM Support - Compatible with various LLM providers. LLM config accepts provider and model.
# FR-21: Vector Database Flexibility - Support multiple vector store backends.
# FR-22: Embedding Options - Multiple embedding models supported. Embedder config accepts provider and model.
# IC-3: Configuration management via environment variables
# AC-27: user_id/agent_id/session_id scoping supported (v3 simplified)
# AC-28: Data isolation enforced between tenants
# AC-49: LLM config accepts provider and model
# AC-50: Multiple providers supported
# AC-51: vector_store config with provider and config
# AC-52: Redis backend supported
# AC-53: embedder config accepts provider and model
# AC-54: Configurable dimensions
# E-9: ERR_SCOPE_001 - Invalid scope hierarchy provided
# CPARA-9: VECTOR_STORE configuration with provider and config structure
# CPARA-10: LLM configuration with provider and config structure
# DP-3: Repository Pattern - COMP-3 Mem0 Memory Manager acts as repository for memory operations
# DP-6: Multi-Tenant Isolation Pattern
# ADR-2: Redis as vector store per architecture decision

Multi-tenant memory scoping manager using Mem0 AsyncMemory.
Enforces scope hierarchy (user_id/agent_id/session_id) for memory isolation via composite user_id.
Supports multiple vector store backends via configurable VectorStoreConfig.
Supports multiple embedding models via configurable EmbedderConfig.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from ..config.settings import EmbedderConfig, LLMConfig, RerankerConfig, VectorStoreConfig

logger = logging.getLogger(__name__)


class TenantScope(BaseModel):
    """
    # Entity: ENT-3, ENT-4, ENT-5 - User, Agent, Session scope hierarchy

    Represents the scope hierarchy for memory isolation using Mem0 v3 API.
    In Mem0 v3, org_id and project_id are no longer passed to the client constructor.
    Multi-tenant isolation is achieved via composite user_id encoding.

    Attributes:
        user_id: User identifier (required for user-level isolation)
        agent_id: Agent identifier (optional, for agent-level isolation)
        session_id: Session identifier (optional, for session-level isolation)
    """
    user_id: str = Field(..., description="User ID for user-level isolation")
    agent_id: str | None = Field(None, description="Agent ID for agent-level isolation")
    session_id: str | None = Field(None, description="Session ID for session-level isolation")

    def to_mem0_user_id(self) -> str:
        """
        # FR-10: Format scope hierarchy for Mem0 user_id
        # AC-27: Scope hierarchy encoded in user_id for v3 compatibility

        Convert scope to Mem0-compatible user_id format.
        Format: {user_id}:{agent_id}:{session_id}
        Only includes non-None levels.
        """
        parts = [self.user_id]
        if self.agent_id:
            parts.append(self.agent_id)
        if self.session_id:
            parts.append(self.session_id)
        return ":".join(parts)

    def to_display_string(self) -> str:
        """Human-readable scope string for logging."""
        return f"user={self.user_id}, agent={self.agent_id}, session={self.session_id}"


class Mem0InitializationError(Exception):
    """Raised when Mem0 client initialization fails."""
    pass


class ScopeValidationError(Exception):
    """
    # E-9: ERR_SCOPE_001 - Invalid scope hierarchy provided
    
    Raised when scope hierarchy validation fails.
    HTTP Status: 400
    Severity: warn
    Logging context: [scope, validation]
    """
    def __init__(
        self,
        message: str = "Invalid scope hierarchy provided",
        code: str = "ERR_SCOPE_001",
        http_status: int = 400
    ):
        self.code = code
        self.http_status = http_status
        self.message = message
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"ScopeValidationError(code={self.code}, http_status={self.http_status}, message={self.message})"


class ScopeValidator:
    """
    # E-9: Scope validation on input
    # DP-6: Multi-Tenant Isolation Pattern - validate scope parameters
    
    Static methods for validating scope hierarchy.
    """

    @staticmethod
    def validate_scope(scope: TenantScope) -> bool:
        """
        # E-9: Validate scope hierarchy on input
        # FR-10: user_id hierarchy enforced (v3 simplified approach)

        Validates that required scope components are present and non-empty.
        Raises ScopeValidationError (ERR_SCOPE_001) if validation fails.

        Args:
            scope: TenantScope to validate

        Returns:
            True if valid

        Raises:
            ScopeValidationError: If user_id is empty
        """
        if not scope.user_id or not scope.user_id.strip():
            logger.warning(
                "Scope validation failed: user_id is empty",
                extra={"scope": scope.to_display_string(), "validation": "user_id"}
            )
            raise ScopeValidationError(
                message="Invalid scope hierarchy: user_id is required and cannot be empty",
                code="ERR_SCOPE_001",
                http_status=400
            )

        if scope.agent_id is not None and not scope.agent_id.strip():
            logger.warning(
                "Scope validation failed: agent_id is empty",
                extra={"scope": scope.to_display_string(), "validation": "agent_id"}
            )
            raise ScopeValidationError(
                message="Invalid scope hierarchy: agent_id cannot be empty if provided",
                code="ERR_SCOPE_001",
                http_status=400
            )

        if scope.session_id is not None and not scope.session_id.strip():
            logger.warning(
                "Scope validation failed: session_id is empty",
                extra={"scope": scope.to_display_string(), "validation": "session_id"}
            )
            raise ScopeValidationError(
                message="Invalid scope hierarchy: session_id cannot be empty if provided",
                code="ERR_SCOPE_001",
                http_status=400
            )

        logger.debug(
            "Scope validation passed",
            extra={"scope": scope.to_display_string(), "validation": "success"}
        )
        return True


class MemoryEntry(BaseModel):
    """
    # Entity: Memory entry returned from Mem0

    Represents a memory entry with its metadata.

    Attributes:
        id: Unique memory identifier
        content: Memory content text
        metadata: Additional metadata including scope info
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class MemoryManager:
    """
    # FR-10: Multi-tenant Support - The server MUST support multiple users, agents, and applications with isolated memory spaces.
    # FR-20: Multi-LLM Support - Compatible with various LLM providers. LLM config accepts provider and model.
    # FR-21: Vector Database Flexibility - Support multiple vector store backends.
    # FR-22: Embedding Options - Multiple embedding models supported. Embedder config accepts provider and model.
    # DP-3: Repository Pattern - COMP-3 Mem0 Memory Manager acts as repository for memory operations
    # DP-6: Multi-Tenant Isolation Pattern - MemoryManager enforces scoping in all operations
    # AC-28: Data isolation enforced between tenants - Users cannot access other users' memories
    # AC-49: LLM config accepts provider and model
    # AC-50: Multiple providers supported
    # AC-51: vector_store config with provider and config
    # AC-52: Redis backend supported
    # AC-53: embedder config accepts provider and model
    # AC-54: Configurable dimensions

    Multi-tenant memory manager using Mem0 AsyncMemory.

    This manager wraps Mem0 AsyncMemory to enforce multi-tenant isolation
    using the user_id/agent_id/session_id hierarchy encoded in Mem0 user_id.
    All memory operations are scoped to the tenant hierarchy.

    Attributes:
        client: Mem0 AsyncMemory client instance
        llm_config: LLM configuration with provider and model for Multi-LLM support
        vector_store_config: Vector store configuration with provider and config for multi-backend support
        embedder_config: Embedder configuration with provider, model, and dimensions for embedding options
    """

    def __init__(
        self,
        mem0_client: Any,
        llm_config: LLMConfig | None = None,
        vector_store_config: VectorStoreConfig | None = None,
        embedder_config: EmbedderConfig | None = None,
        reranker_config: RerankerConfig | None = None
    ):
        """
        # TECH-4: Mem0 v2 AsyncMemory
        # FR-20: Multi-LLM Support - configure with provider and model
        # FR-21: Vector Database Flexibility - Support multiple vector store backends
        # FR-22: Embedding Options - Multiple embedding models supported
        # FR-23: Reranker Support - boost relevance with reranking models
        # AC-49: LLM config accepts provider and model
        # AC-51: vector_store config with provider and config
        # AC-52: Redis backend supported
        # AC-53: embedder config accepts provider and model
        # AC-54: Configurable dimensions

        Initialize MemoryManager with Mem0 AsyncMemory client and optional LLM, vector store, embedder, and reranker configs.

        Args:
            mem0_client: Mem0 AsyncMemory client instance
            llm_config: Optional LLM configuration for Multi-LLM support (provider, model)
            vector_store_config: Optional vector store configuration for multi-backend support (provider, config)
            embedder_config: Optional embedder configuration for embedding options (provider, model, dimensions)
            reranker_config: Optional reranker configuration for enhanced search (provider, model, top_k)
        """
        self.client = mem0_client
        self.llm_config = llm_config or LLMConfig()
        self.vector_store_config = vector_store_config or VectorStoreConfig()
        self.embedder_config = embedder_config or EmbedderConfig()
        self.reranker_config = reranker_config
        reranker_info = f", Reranker provider={reranker_config.provider}" if reranker_config else ""
        logger.info(
            f"MemoryManager initialized with Mem0 AsyncMemory client, "
            f"LLM provider={self.llm_config.provider}, model={self.llm_config.model}, "
            f"VectorStore provider={self.vector_store_config.provider}, "
            f"Embedder provider={self.embedder_config.provider}, model={self.embedder_config.model}, "
            f"dimensions={self.embedder_config.dimension}{reranker_info}"
        )

    @property
    def llm_provider(self) -> str:
        """
        # FR-20: Expose LLM provider for Multi-LLM support
        # AC-49: Provider extracted from config
        
        Get the configured LLM provider.
        
        Returns:
            LLM provider name (e.g., 'openai', 'anthropic')
        """
        return self.llm_config.provider

    @property
    def llm_model(self) -> str:
        """
        # FR-20: Expose LLM model for Multi-LLM support
        # AC-49: Model extracted from config
        
        Get the configured LLM model.
        
        Returns:
            LLM model name (e.g., 'gpt-4o', 'claude-3')
        """
        return self.llm_config.model

    @property
    def vector_store_provider(self) -> str:
        """
        # FR-21: Vector Database Flexibility - Support multiple vector store backends
        # AC-51: Provider extracted from vector_store config
        # AC-52: Redis backend supported

        Get the configured vector store provider.

        Returns:
            Vector store provider name (e.g., 'redis', 'qdrant', 'chroma')
        """
        return self.vector_store_config.provider

    @property
    def embedder_provider(self) -> str:
        """
        # FR-22: Embedding Options - Multiple embedding models supported
        # AC-53: Provider extracted from embedder config

        Get the configured embedder provider.

        Returns:
            Embedder provider name (e.g., 'openai', 'huggingface', 'cohere')
        """
        return self.embedder_config.provider

    @property
    def embedder_model(self) -> str:
        """
        # FR-22: Embedding Options - Multiple embedding models supported
        # AC-53: Model extracted from embedder config

        Get the configured embedder model.

        Returns:
            Embedder model name (e.g., 'text-embedding-3-small', 'embed-english-v2.0')
        """
        return self.embedder_config.model

    @property
    def embedder_dimensions(self) -> int:
        """
        # FR-22: Embedding Options - Configurable dimensions
        # AC-54: Dimensions extracted from embedder config

        Get the configured embedding dimensions.

        Returns:
            Embedding dimension (e.g., 384, 768, 1536, 3072)
        """
        return self.embedder_config.dimension

    @property
    def reranker_provider(self) -> str | None:
        """
        # FR-23: Reranker Support
        # AC-55: Reranker provider extracted from config

        Get the configured reranker provider.

        Returns:
            Reranker provider name (e.g., 'cohere', 'sentence_transformer') or None if not configured
        """
        return self.reranker_config.provider if self.reranker_config else None

    async def add_memory(
        self,
        scope: TenantScope,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """
        # FR-10: Multi-tenant memory operations with full scope hierarchy
        # AC-27: Memory stored with scope hierarchy
        # IC-3: Configuration via environment variables
        
        Add a memory entry with tenant scope.
        
        Args:
            scope: TenantScope with user_id/agent_id/session_id
            content: Memory content text
            metadata: Optional additional metadata
            
        Returns:
            MemoryEntry with created memory info
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        # FR-10: Validate scope hierarchy on input per E-9
        ScopeValidator.validate_scope(scope)

        # Build Mem0 user_id from scope for v3 isolation
        mem0_user_id = scope.to_mem0_user_id()

        # Build metadata with scope info for isolation tracking
        memory_metadata = {
            "user_id": scope.user_id,
            **(metadata or {})
        }

        if scope.agent_id:
            memory_metadata["agent_id"] = scope.agent_id
        if scope.session_id:
            memory_metadata["session_id"] = scope.session_id

        logger.debug(
            f"Adding memory for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        # AC-28: Store agent_id, session_id with memories for isolation
        # Mem0 AsyncMemory.add() expects messages list format
        result = await self.client.add(
            messages=[{"role": "user", "content": content}],
            user_id=mem0_user_id,
            metadata=memory_metadata
        )

        results_list = result.get("results", []) if isinstance(result, dict) else result if result else []
        first_result = results_list[0] if results_list else {}

        return MemoryEntry(
            id=first_result.get("id", ""),
            content=content,
            metadata=memory_metadata,
            created_at=first_result.get("created_at")
        )

    async def search_memories(
        self,
        scope: TenantScope,
        query: str,
        limit: int = 10,
        metadata_filters: dict[str, Any] | None = None,
        rerank: bool | None = None
    ) -> list[MemoryEntry]:
        """
        # FR-10: Multi-tenant search with scope isolation
        # FR-23: Reranker Support - rerank parameter enables/disables reranking
        # AC-27: Memory stored with all scope levels
        # AC-28: Data isolation enforced - only scope's memories returned

        Search memories within tenant scope.

        Args:
            scope: TenantScope for search filtering
            query: Search query string
            limit: Maximum number of results (default 10)
            metadata_filters: Optional metadata filters for advanced search
            rerank: Optional boolean to enable/disable reranking.
                   If None, uses reranker_config.enabled if reranker is configured.
                   If reranker_config is None, reranking is not applied.

        Returns:
            List of MemoryEntry objects within scope

        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Searching memories for user: {mem0_user_id}, query: {query}",
            extra={"scope": scope.to_display_string()}
        )

        filters = {"user_id": mem0_user_id}
        if metadata_filters:
            filters.update(metadata_filters)

        search_kwargs: dict[str, Any] = {
            "query": query,
            "filters": filters,
            "top_k": limit,
        }

        if rerank is None and self.reranker_config:
            rerank = self.reranker_config.enabled

        if rerank is not None:
            search_kwargs["rerank"] = rerank

        results = await self.client.search(**search_kwargs)

        results_list = results.get("results", []) if isinstance(results, dict) else results

        return [
            MemoryEntry(
                id=r.get("id", ""),
                content=r.get("content") or r.get("memory", ""),
                metadata=r.get("metadata", {}),
                created_at=r.get("created_at")
            )
            for r in results_list
        ]

    async def get_memories(
        self,
        scope: TenantScope,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """
        # FR-10: Get memories within tenant scope
        # AC-27: Full scope hierarchy supported
        # AC-28: Data isolation enforced between tenants
        
        Get all memories within tenant scope.
        
        Args:
            scope: TenantScope for filtering
            limit: Maximum number of results (default 50)
            
        Returns:
            List of MemoryEntry objects within scope
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Getting memories for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        results = await self.client.get_all(
            filters={"user_id": mem0_user_id},
            page=1,
            page_size=limit,
        )
        results_list = results.get("results", []) if isinstance(results, dict) else results

        return [
            MemoryEntry(
                id=r.get("id", ""),
                content=r.get("content") or r.get("memory", ""),
                metadata=r.get("metadata", {}),
                created_at=r.get("created_at")
            )
            for r in results_list
        ]

    async def get_memory(
        self,
        memory_id: str,
        scope: TenantScope,
    ) -> MemoryEntry:
        """
        # FR-10: Get specific memory by ID within tenant scope
        # AC-22: memory_id required
        
        Get a specific memory entry by ID within tenant scope.
        
        Args:
            memory_id: ID of memory to retrieve
            scope: TenantScope for validation
            
        Returns:
            MemoryEntry for the specified memory
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Getting memory: {memory_id} for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        result = await self.client.get(memory_id=memory_id)
        if not result:
            raise ValueError(f"Memory {memory_id} not found")

        memory_user_id = result.get("user_id") or result.get("metadata", {}).get("user_id", "")
        memory_metadata = result.get("metadata", {})
        if memory_user_id != mem0_user_id:
            logger.warning(
                "Tenant isolation violation: attempted to access memory from different tenant",
                extra={"scope": scope.to_display_string()}
            )
            raise ValueError(f"Memory {memory_id} not found")

        return MemoryEntry(
            id=result.get("id", ""),
            content=result.get("content") or result.get("memory", ""),
            metadata=result.get("metadata", {}),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )

    async def delete_memory(
        self,
        memory_id: str,
        scope: TenantScope
    ) -> bool:
        """
        # FR-10: Delete memory with scope validation
        # E-9: Validate scope before delete operation
        
        Delete a memory entry within tenant scope.
        
        Args:
            memory_id: ID of memory to delete
            scope: TenantScope for validation
            
        Returns:
            True if deletion successful
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Deleting memory: {memory_id} for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        try:
            existing = await self.client.get(memory_id=memory_id)
            if existing:
                existing_user_id = existing.get("user_id") or existing.get("metadata", {}).get("user_id", "")
                if existing_user_id and existing_user_id != mem0_user_id:
                    raise ValueError(f"Memory {memory_id} not found")

            await self.client.delete(memory_id=memory_id)
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to delete memory: {memory_id}",
                extra={"scope": scope.to_display_string(), "error": str(e)}
            )
            raise RuntimeError(f"Failed to delete memory {memory_id}") from e

    async def delete_all_memories(self, scope: TenantScope) -> bool:
        """
        # FR-10: Delete all memories within tenant scope
        # AC-28: Ensure complete isolation on deletion
        
        Delete all memories within tenant scope.
        
        Args:
            scope: TenantScope for filtering
            
        Returns:
            True if deletion successful
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Deleting all memories for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        try:
            await self.client.delete_all(user_id=mem0_user_id)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete all memories",
                extra={"scope": scope.to_display_string(), "error": str(e)}
            )
            raise RuntimeError("Failed to delete all memories") from e

    async def update_memory(
        self,
        memory_id: str,
        scope: TenantScope,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """
        # FR-10: Update existing memory within tenant scope
        # AC-18: Metadata preserved during update
        
        Update an existing memory entry.
        
        Args:
            memory_id: ID of memory to update
            scope: TenantScope for validation
            content: New content for the memory
            metadata: Optional metadata to merge with existing
            
        Returns:
            MemoryEntry with updated memory info
            
        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Updating memory: {memory_id} for user: {mem0_user_id}",
            extra={"scope": scope.to_display_string()}
        )

        try:
            existing = await self.get_memory(memory_id=memory_id, scope=scope)
            merged_metadata = {**existing.metadata, **(metadata or {})}

            result = await self.client.update(
                memory_id=memory_id,
                data=content,
                metadata=merged_metadata
            )

            return MemoryEntry(
                id=memory_id,
                content=content,
                metadata=merged_metadata,
                created_at=existing.created_at,
                updated_at=result.get("updated_at") if isinstance(result, dict) else None,
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to update memory: {memory_id}",
                extra={"scope": scope.to_display_string(), "error": str(e)}
            )
            raise ValueError(f"Failed to update memory {memory_id}") from e

    async def list_memories(
        self,
        scope: TenantScope,
        limit: int = 50
    ) -> list[MemoryEntry]:
        """
        # FR-10: List memories within tenant scope with limit
        # AC-26: Returns memory list

        List all memories within tenant scope.

        Args:
            scope: TenantScope for filtering
            limit: Maximum number of results (default 50)

        Returns:
            List of MemoryEntry objects within scope

        Raises:
            ScopeValidationError: If scope validation fails (E-9)
        """
        ScopeValidator.validate_scope(scope)

        mem0_user_id = scope.to_mem0_user_id()

        logger.debug(
            f"Listing memories for user: {mem0_user_id}, limit={limit}",
            extra={"scope": scope.to_display_string()}
        )

        try:
            results = await self.client.get_all(
                filters={"user_id": mem0_user_id},
                page_size=limit,
            )
            results_list = results.get("results", []) if isinstance(results, dict) else results

            return [
                MemoryEntry(
                    id=r.get("id", ""),
                    content=r.get("content") or r.get("memory", ""),
                    metadata=r.get("metadata", {}),
                    created_at=r.get("created_at")
                )
                for r in results_list
            ]
        except Exception as e:
            logger.error(
                "Failed to list memories",
                extra={"scope": scope.to_display_string(), "error": str(e)}
            )
            raise
