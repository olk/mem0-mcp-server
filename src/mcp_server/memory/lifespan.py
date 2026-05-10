"""Async context manager for Mem0 AsyncMemory lifecycle.

# DP-2: Async Context Manager Pattern
# IC-3: Mem0 AsyncMemory instances MUST be created and closed by an asynccontextmanager
# passed via the server lifespan, ensuring a single shared instance across tools.
# ADR-7: Memory Lifecycle Management - Single AsyncMemory Instance via Lifespan
# FR-20: Multi-LLM Support - Compatible with various LLM providers
# CPARA-10: LLM configuration with provider and model structure

This module exposes the raw Mem0 AsyncMemory instance directly to tools,
without any custom multi-tenant wrapper layer.
"""

import logging
from contextlib import asynccontextmanager

from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig as Mem0EmbedderConfig
from mem0.llms.configs import LlmConfig as Mem0LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig as Mem0VectorStoreConfig

from mcp_server.config.settings import EmbedderConfig as AppEmbedderConfig
from mcp_server.config.settings import LLMConfig as AppLLMConfig
from mcp_server.config.settings import VectorStoreConfig as AppVectorStoreConfig
from mcp_server.memory.manager import Mem0InitializationError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def memory_lifespan(
    llm_config: AppLLMConfig | None = None,
    vector_store_config: AppVectorStoreConfig | None = None,
    embedder_config: AppEmbedderConfig | None = None,
):
    """Async context manager for Mem0 AsyncMemory lifecycle.

    # DP-2: Async Context Manager Pattern - Manage Mem0 AsyncMemory lifecycle
    # IC-3: Create and close AsyncMemory via this context manager
    # ADR-7: Single shared instance via lifespan
    # FR-20: Multi-LLM Support - LLM provider and model configurable

    This context manager:
    1. Creates AsyncMemory with vector store, LLM, and embedder configuration
    2. Yields the raw AsyncMemory instance for direct tool access
    3. Ensures cleanup on exit

    No custom multi-tenant wrapper is applied - tools receive the raw AsyncMemory
    instance and interact with it using the native Mem0 API.

    Configuration (CPARA-9, CPARA-10, FR-22):
        - Vector store: Redis with collection_name="mem0", embedding_model_dims=1536
        - LLM: Configurable provider (default: openai) and model (default: gpt-4o)
        - Embedder: Configurable provider (default: openai), model, and dimensions

    Args:
        llm_config: Optional LLM configuration for Multi-LLM support (provider, model, etc.)
                   If not provided, uses default LLMConfig with openai/gpt-4o
        vector_store_config: Optional vector store configuration dict with provider and config.
                             If not provided, uses default Redis config.
        embedder_config: Optional embedder configuration for embedding options.
                        If not provided, uses default EmbedderConfig with openai/text-embedding-3-small.

    Yields:
        dict with:
            - memory: AsyncMemory instance (raw Mem0 API)

    Raises:
        Mem0InitializationError: Only during creation, not during cleanup
    """
    memory: AsyncMemory | None = None

    try:
        llm_cfg = llm_config or AppLLMConfig()
        embedder_cfg = embedder_config or AppEmbedderConfig()
        vector_cfg = vector_store_config or AppVectorStoreConfig()

        mem0_config = MemoryConfig(
            vector_store=Mem0VectorStoreConfig(**vector_cfg.to_mem0_vector_store_config()),
            llm=Mem0LlmConfig(**llm_cfg.to_mem0_llm_config()),
            embedder=Mem0EmbedderConfig(**embedder_cfg.to_mem0_embedder_config()),
        )
        memory = AsyncMemory(config=mem0_config)
    except Exception as e:
        raise Mem0InitializationError(f"Failed to initialize Mem0 AsyncMemory: {e}") from e

    if memory is None:
        raise Mem0InitializationError("Failed to create AsyncMemory")

    try:
        yield {"memory": memory}
    finally:
        if memory is not None:
            try:
                memory.close()
            except Exception as e:
                logger.warning(
                    f"Memory cleanup warning: {e}",
                    extra={"logging_context": ["cleanup", "memory"]}
                )
