"""
Unit tests for MCP prompt templates.

# UT-8: prompt templates tests
# Validates requirements: FR-1, FR-14
# Scenarios:
#   - SCEN-23: recall_memories prompt renders correctly
#   - SCEN-24: get_user_context prompt renders correctly
#   - SCEN-25: extract_memories prompt renders correctly
#   - SCEN-26: summarize_for_storage prompt renders correctly
#   - SCEN-28: get_preferences prompt renders correctly
#   - SCEN-29: session_recap prompt renders correctly
# AC-15: Prompts return valid JSON payload
# AC-16: Prompts include correct scope filters
"""

import json


def _get_message_text(message) -> str:
    """Extract text content from a Message object.

    Message.content can be TextContent or EmbeddedResource at type level,
    but when passing a string to Message(), it's stored as TextContent.text.
    """
    if hasattr(message.content, "text"):
        return message.content.text
    return str(message.content)


class TestRecallMemoriesPrompt:
    """Test recall_memories prompt template."""

    def test_recall_memories_renders_valid_json(self):
        """SCEN-23: recall_memories returns valid JSON with query and filters."""
        from mcp_server.prompts import recall_memories

        result = recall_memories(
            query="user preferences",
            user_id="user_123",
            agent_id="agent_789",
            session_id="session_abc",
            limit=10,
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "recall_memories"
        assert payload["query"] == "user preferences"
        assert payload["filters"]["user_id"] == "user_123"
        assert payload["filters"]["agent_id"] == "agent_789"
        assert payload["filters"]["session_id"] == "session_abc"
        assert "org_id" not in payload["filters"]
        assert "project_id" not in payload["filters"]
        assert payload["limit"] == 10

    def test_recall_memories_without_optional_agent_id(self):
        """recall_memories works without optional agent_id."""
        from mcp_server.prompts import recall_memories

        result = recall_memories(
            query="test query",
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["filters"]["agent_id"] is None
        assert payload["filters"]["session_id"] == "session_abc"

    def test_recall_memories_default_limit(self):
        """recall_memories uses default limit of 10."""
        from mcp_server.prompts import recall_memories

        result = recall_memories(
            query="test query",
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["limit"] == 10


class TestGetUserContextPrompt:
    """Test get_user_context prompt template."""

    def test_get_user_context_renders_valid_json(self):
        """SCEN-24: get_user_context returns valid JSON with filters."""
        from mcp_server.prompts import get_user_context

        result = get_user_context(
            user_id="user_123",
            agent_id="agent_789",
            session_id="session_abc",
            limit=50,
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "get_user_context"
        assert payload["filters"]["user_id"] == "user_123"
        assert payload["filters"]["agent_id"] == "agent_789"
        assert payload["filters"]["session_id"] == "session_abc"
        assert "org_id" not in payload["filters"]
        assert "project_id" not in payload["filters"]
        assert payload["limit"] == 50

    def test_get_user_context_default_limit(self):
        """get_user_context uses default limit of 50."""
        from mcp_server.prompts import get_user_context

        result = get_user_context(
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["limit"] == 50


class TestExtractMemoriesPrompt:
    """Test extract_memories prompt template."""

    def test_extract_memories_renders_valid_json(self):
        """SCEN-25: extract_memories returns valid JSON with instructions and add_memory params."""
        from mcp_server.prompts import extract_memories

        result = extract_memories(
            message_content="I prefer dark mode theme",
            user_id="user_123",
            agent_id="agent_789",
            session_id="session_abc",
            message_role="user",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "extract_memories"
        assert "task" in payload["instructions"]
        assert payload["instructions"]["message_content"] == "I prefer dark mode theme"
        assert payload["instructions"]["message_role"] == "user"
        assert payload["add_memory_params"]["user_id"] == "user_123"
        assert payload["add_memory_params"]["messages"] == [
            {"role": "user", "content": "I prefer dark mode theme"}
        ]
        assert payload["add_memory_params"]["metadata"]["prompt_type"] == "extracted_facts"

    def test_extract_memories_default_message_role(self):
        """extract_memories defaults message_role to 'user'."""
        from mcp_server.prompts import extract_memories

        result = extract_memories(
            message_content="Test message",
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["instructions"]["message_role"] == "user"
        assert payload["add_memory_params"]["metadata"]["original_role"] == "user"

    def test_extract_memories_assistant_role(self):
        """extract_memories works with assistant message role."""
        from mcp_server.prompts import extract_memories

        result = extract_memories(
            message_content="Based on your preferences, I'll suggest...",
            user_id="user_123",
            session_id="session_abc",
            message_role="assistant",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["instructions"]["message_role"] == "assistant"


class TestSummarizeForStoragePrompt:
    """Test summarize_for_storage prompt template."""

    def test_summarize_for_storage_renders_valid_json(self):
        """SCEN-26: summarize_for_storage returns valid JSON with instructions and add_memory params."""
        from mcp_server.prompts import summarize_for_storage

        messages_json = json.dumps([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ])

        result = summarize_for_storage(
            messages_json=messages_json,
            user_id="user_123",
            agent_id="agent_789",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "summarize_for_storage"
        assert "task" in payload["instructions"]
        assert payload["instructions"]["message_count"] == 2
        assert payload["add_memory_params"]["messages"] == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert payload["add_memory_params"]["metadata"]["prompt_type"] == "conversation_summary"

    def test_summarize_for_storage_handles_invalid_json(self):
        """summarize_for_storage handles invalid JSON gracefully."""
        from mcp_server.prompts import summarize_for_storage

        result = summarize_for_storage(
            messages_json="not valid json",
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["add_memory_params"]["messages"] == [
            {"role": "user", "content": "not valid json"}
        ]

    def test_summarize_for_storage_handles_non_list_json(self):
        """summarize_for_storage wraps non-list JSON in list."""
        from mcp_server.prompts import summarize_for_storage

        result = summarize_for_storage(
            messages_json=json.dumps({"role": "user", "content": "Single message"}),
            user_id="user_123",
            session_id="session_abc",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["add_memory_params"]["messages"] == [
            {"role": "user", "content": "Single message"}
        ]


class TestGetPreferencesPrompt:
    """Test get_preferences prompt template."""

    def test_get_preferences_renders_valid_json(self):
        """SCEN-28: get_preferences returns valid JSON with filters."""
        from mcp_server.prompts import get_preferences

        result = get_preferences(
            user_id="user_123",
            topic="theme",
            limit=20,
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "get_preferences"
        assert payload["filters"]["user_id"] == "user_123"
        assert "org_id" not in payload["filters"]
        assert "project_id" not in payload["filters"]
        assert payload["filters"]["metadata"]["topic"] == {"icontains": "theme"}
        assert payload["limit"] == 20

    def test_get_preferences_without_topic_filter(self):
        """get_preferences works without topic filter."""
        from mcp_server.prompts import get_preferences

        result = get_preferences(
            user_id="user_123",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert "metadata" not in payload["filters"]

    def test_get_preferences_default_limit(self):
        """get_preferences uses default limit of 20."""
        from mcp_server.prompts import get_preferences

        result = get_preferences(
            user_id="user_123",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["limit"] == 20


class TestSessionRecapPrompt:
    """Test session_recap prompt template."""

    def test_session_recap_renders_valid_json(self):
        """SCEN-29: session_recap returns valid JSON with filters and instructions."""
        from mcp_server.prompts import session_recap

        result = session_recap(
            session_id="session_abc",
            user_id="user_123",
            agent_id="agent_789",
        )

        content = _get_message_text(result.messages[0])
        payload = json.loads(content)

        assert payload["prompt"] == "session_recap"
        assert "task" in payload["instructions"]
        assert payload["filters"]["user_id"] == "user_123"
        assert payload["filters"]["session_id"] == "session_abc"
        assert payload["filters"]["agent_id"] == "agent_789"
        assert "org_id" not in payload["filters"]
        assert "project_id" not in payload["filters"]
        assert "Use list_memories" in payload["note"]


class TestPromptRegistration:
    """Test prompt registration with FastMCP."""

    def test_register_all_prompts_function_exists(self):
        """Verify register_all_prompts function exists and is callable."""
        from mcp_server.prompts import register_all_prompts

        assert callable(register_all_prompts)

    def test_register_all_prompts_accepts_mcp_instance(self):
        """Verify registration function accepts FastMCP instance."""
        from unittest.mock import MagicMock

        from mcp_server.prompts import register_all_prompts

        mock_mcp = MagicMock()

        register_all_prompts(mock_mcp)
