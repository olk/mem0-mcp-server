"""MCP tool modules for mem0-mcp-server.

This module registers all MCP tools with the FastMCP server instance.
Tools are registered at module import time to ensure they're available
when the server starts.
"""

from mcp_server import mcp
from mcp_server.prompts import register_all_prompts
from mcp_server.tools.add_memory import register_add_memory_tool
from mcp_server.tools.delete_memory import register_delete_memory_tool
from mcp_server.tools.erase_memories import register_erase_memories_tool
from mcp_server.tools.get_memory import register_get_memory_tool
from mcp_server.tools.list_memories import register_list_memories_tool
from mcp_server.tools.search_memories import register_search_memories_tool
from mcp_server.tools.update_memory import register_update_memory_tool

register_add_memory_tool(mcp)
register_delete_memory_tool(mcp)
register_erase_memories_tool(mcp)
register_get_memory_tool(mcp)
register_list_memories_tool(mcp)
register_search_memories_tool(mcp)
register_update_memory_tool(mcp)
register_all_prompts(mcp)

__all__ = [
    "register_add_memory_tool",
    "register_delete_memory_tool",
    "register_erase_memories_tool",
    "register_get_memory_tool",
    "register_list_memories_tool",
    "register_search_memories_tool",
    "register_update_memory_tool",
]
