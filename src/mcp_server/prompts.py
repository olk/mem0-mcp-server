"""
MCP prompt templates for mem0-mcp-server.

This module provides reusable prompt templates that guide memory operations.
Prompts return structured JSON payloads that clients can use to execute
memory operations via the MCP tools.

Prompts follow the naming convention: intent/scenario, not tool names.
"""

import json
import logging
from typing import Any

from fastmcp.prompts import Message, PromptResult

from mcp_server import mcp

logger = logging.getLogger(__name__)


@mcp.prompt(
    name="recall_memories",
    description="Semantic search to recall relevant memories based on a query",
)
def recall_memories(
    query: str,
    user_id: str,
    agent_id: str | None = None,
    session_id: str | None = None,
    limit: int = 10,
) -> PromptResult:
    """Render a prompt for semantic memory search.

    Returns JSON payload with search parameters for search_memories tool.
    """
    payload = {
        "prompt": "recall_memories",
        "query": query,
        "filters": {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
        },
        "limit": limit,
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


@mcp.prompt(
    name="get_user_context",
    description="Retrieve all memories for a user to build context",
)
def get_user_context(
    user_id: str,
    agent_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> PromptResult:
    """Render a prompt to retrieve all memories for a user.

    Returns JSON payload with filters for list_memories tool.
    """
    payload = {
        "prompt": "get_user_context",
        "filters": {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
        },
        "limit": limit,
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


@mcp.prompt(
    name="extract_memories",
    description="Extract facts and preferences from messages for storage",
)
def extract_memories(
    message_content: str,
    user_id: str,
    agent_id: str | None = None,
    session_id: str | None = None,
    message_role: str = "user",
) -> PromptResult:
    """Render a prompt for extracting memories from a message.

    Returns JSON payload with messages for add_memory tool.
    Instructs the LLM what to extract and how to format it.
    """
    payload = {
        "prompt": "extract_memories",
        "instructions": {
            "task": "Analyze the message and extract factual information, preferences, "
                    "or context worth remembering. Format as concise, self-contained facts.",
            "message_content": message_content,
            "message_role": message_role,
        },
        "add_memory_params": {
            "messages": [{"role": message_role, "content": message_content}],
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "metadata": {
                "prompt_type": "extracted_facts",
                "original_role": message_role,
            },
            "infer": True,
        },
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


@mcp.prompt(
    name="summarize_for_storage",
    description="Generate a summary from conversation messages for memory storage",
)
def summarize_for_storage(
    messages_json: str,
    user_id: str,
    agent_id: str | None = None,
    session_id: str | None = None,
) -> PromptResult:
    """Render a prompt to summarize conversation messages for storage.

    Returns JSON payload with summarized messages for add_memory tool.
    Expects messages_json to be a JSON string array of {role, content} dicts.
    """
    try:
        messages = json.loads(messages_json)
        if not isinstance(messages, list):
            messages = [messages]
    except json.JSONDecodeError:
        messages = [{"role": "user", "content": messages_json}]

    payload = {
        "prompt": "summarize_for_storage",
        "instructions": {
            "task": "Summarize the conversation concisely, preserving key facts, "
                    "decisions, and any user preferences mentioned.",
            "message_count": len(messages),
        },
        "add_memory_params": {
            "messages": messages,
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "metadata": {
                "prompt_type": "conversation_summary",
            },
            "infer": True,
        },
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


@mcp.prompt(
    name="get_preferences",
    description="Retrieve user preferences specifically",
)
def get_preferences(
    user_id: str,
    topic: str | None = None,
    limit: int = 20,
) -> PromptResult:
    """Render a prompt to retrieve user preferences.

    Returns JSON payload with filters for list_memories tool.
    Optionally filters by topic using metadata icontains.
    """
    filters: dict[str, Any] = {
        "user_id": user_id,
    }

    if topic:
        filters["metadata"] = {"topic": {"icontains": topic}}

    payload = {
        "prompt": "get_preferences",
        "filters": filters,
        "limit": limit,
        "note": "Filter results for preference-related memories",
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


@mcp.prompt(
    name="session_recap",
    description="Generate a session summary for future recall",
)
def session_recap(
    session_id: str,
    user_id: str,
    agent_id: str | None = None,
) -> PromptResult:
    """Render a prompt to generate a session summary.

    Returns JSON payload with filters for list_memories tool to retrieve
    memories from a specific session, plus instructions for summarizing.
    """
    payload = {
        "prompt": "session_recap",
        "instructions": {
            "task": "Summarize the session into key topics, outcomes, and any "
                    "follow-up actions. Format as structured summary.",
        },
        "filters": {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
        },
        "note": "Use list_memories with these filters to get session memories, "
                "then generate summary for add_memory with metadata.prompt_type='session_recap'",
    }
    return PromptResult(messages=[Message(content=json.dumps(payload, indent=2))])


def register_all_prompts(server) -> None:
    """Register all prompts with the FastMCP server.

    Args:
        server: FastMCP server instance
    """
    logger.info("All prompt templates registered successfully")
