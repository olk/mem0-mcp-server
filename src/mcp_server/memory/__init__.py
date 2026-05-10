"""Mem0 memory management package.

# FR-2: Mem0 v2 API Exposure - The server MUST expose complete mem0 v2 Python SDK
# functionality via MCP tools.
# FR-20: Multi-LLM Support - Compatible with various LLM providers
# IC-3: Mem0 AsyncMemory instances MUST be created and closed by an asynccontextmanager
# passed via the server lifespan, ensuring a single shared instance across tools.
# CPARA-10: LLM configuration with provider and config structure
# DP-2: Async Context Manager Pattern
# DP-3: Repository Pattern
# DP-6: Multi-Tenant Isolation Pattern
"""

from mcp_server.config.settings import LLMConfig
from mcp_server.memory.lifespan import memory_lifespan
from mcp_server.memory.manager import (
    Mem0InitializationError,
    MemoryManager,
    ScopeValidationError,
    TenantScope,
)

__all__ = [
    "MemoryManager",
    "LLMConfig",
    "Mem0InitializationError",
    "ScopeValidationError",
    "TenantScope",
    "memory_lifespan",
]
