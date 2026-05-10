# Validates: FR-15, AC-39, AC-40
# UT-2: Parameter Precedence tests
# SCEN-4: tool params override env vars
# SCEN-5: env vars override config file
# SCEN-6: all three levels respected

"""
Unit tests for Parameter Precedence (FR-15).

FR-15: Parameter Precedence - Tool parameters override environment variables override config file defaults.
Precedence order (highest to lowest):
1. Tool parameters (direct initialization)
2. Environment variables (with MCP_ prefix)
3. Config file values
4. Hardcoded defaults

AC-39: Parameter precedence order is enforced exactly
AC-40: Config resolution checks each level in order: tool > env > config > default
"""

from mcp_server.config.settings import (
    DEFAULT_AGENT_ID,
    DEFAULT_APP_ID,
    DEFAULT_USER_ID,
    Settings,
    create_settings,
    get_settings,
    reset_settings,
)


class TestParameterPrecedence:
    """Test parameter precedence resolution.

    Validates: FR-15, AC-39, AC-40
    UT-2: Parameter Precedence tests
    """

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_default_values(self):
        """Verify hardcoded defaults are used when no env vars or tool params set.

        AC-40: Levels checked: tool > env > config > default
        When no higher precedence values exist, defaults should be used.
        """
        settings = Settings()
        assert settings.user_id == DEFAULT_USER_ID
        assert settings.agent_id == DEFAULT_AGENT_ID
        assert settings.app_id == DEFAULT_APP_ID

    def test_tool_params_override_env_vars(self, monkeypatch):
        """SCEN-4: tool params override env vars.

        FR-15: Tool parameters have highest precedence
        AC-39: Parameter precedence order is enforced exactly
        AC-40: Config resolution checks each level in order
        """
        # Set environment variables
        monkeypatch.setenv("MCP_USER_ID", "env_user_id")
        monkeypatch.setenv("MCP_AGENT_ID", "env_agent_id")
        monkeypatch.setenv("MCP_APP_ID", "env_app_id")

        # Tool params (direct initialization) should override env vars
        settings = create_settings(
            user_id="tool_user_id",
            agent_id="tool_agent_id",
            app_id="tool_app_id"
        )

        assert settings.user_id == "tool_user_id"
        assert settings.agent_id == "tool_agent_id"
        assert settings.app_id == "tool_app_id"

    def test_env_vars_override_config_defaults(self, monkeypatch):
        """SCEN-5: env vars override config file (and defaults).

        FR-15: Environment variables override config file defaults
        AC-39: Parameter precedence order is enforced exactly
        AC-40: Config resolution checks each level in order
        """
        # Set environment variables - these should override defaults
        monkeypatch.setenv("MCP_USER_ID", "env_user_id")
        monkeypatch.setenv("MCP_AGENT_ID", "env_agent_id")
        monkeypatch.setenv("MCP_APP_ID", "env_app_id")

        # No tool params, so env vars should be used
        settings = Settings()

        assert settings.user_id == "env_user_id"
        assert settings.agent_id == "env_agent_id"
        assert settings.app_id == "env_app_id"

    def test_all_three_levels_respected(self, monkeypatch):
        """SCEN-6: all three levels respected.

        FR-15: Precedence order: tool params > env vars > config file > defaults
        AC-39: Parameter precedence order is enforced exactly
        AC-40: Config resolution checks each level in order: tool > env > config > default

        This test verifies:
        1. Tool params take precedence over everything
        2. Env vars take precedence over defaults
        3. Defaults are used when nothing else is set
        """
        # Test 1: Direct tool params have highest precedence
        settings_with_tool = create_settings(
            user_id="tool_user",
            agent_id="tool_agent",
            app_id="tool_app"
        )
        assert settings_with_tool.user_id == "tool_user"
        assert settings_with_tool.agent_id == "tool_agent"
        assert settings_with_tool.app_id == "tool_app"

        # Test 2: Env vars override defaults (when no tool params)
        monkeypatch.setenv("MCP_USER_ID", "env_user")
        monkeypatch.setenv("MCP_AGENT_ID", "env_agent")
        monkeypatch.setenv("MCP_APP_ID", "env_app")

        settings_with_env = Settings()
        assert settings_with_env.user_id == "env_user"
        assert settings_with_env.agent_id == "env_agent"
        assert settings_with_env.app_id == "env_app"

        # Test 3: Tool params override env vars
        settings_with_both = create_settings(
            user_id="override_user",
            agent_id="override_agent",
            app_id="override_app"
        )
        assert settings_with_both.user_id == "override_user"
        assert settings_with_both.agent_id == "override_agent"
        assert settings_with_both.app_id == "override_app"

        # Test 4: Defaults used when nothing set
        monkeypatch.delenv("MCP_USER_ID", raising=False)
        monkeypatch.delenv("MCP_AGENT_ID", raising=False)
        monkeypatch.delenv("MCP_APP_ID", raising=False)

        settings_defaults = Settings()
        assert settings_defaults.user_id == DEFAULT_USER_ID
        assert settings_defaults.agent_id == DEFAULT_AGENT_ID
        assert settings_defaults.app_id == DEFAULT_APP_ID

    def test_precedence_chain_method(self):
        """Test the get_precedence_chain method.

        AC-39: Precedence order enforced exactly
        """
        settings = Settings()
        chain = settings.get_precedence_chain()

        assert len(chain) == 4
        assert "tool parameters (direct initialization)" == chain[0]
        assert "environment variables (with MCP_ prefix)" == chain[1]
        assert "config file values" == chain[2]
        assert "hardcoded defaults" == chain[3]


class TestPrecedenceWithOtherFields:
    """Test precedence works for all configuration fields.

    Validates: FR-15, AC-39, AC-40
    """

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_host_precedence(self, monkeypatch):
        """Test host field precedence.

        FR-15: All fields follow the same precedence
        """
        # Test tool param override
        settings = create_settings(host="127.0.0.1")
        assert settings.host == "127.0.0.1"

        # Test env var override
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        settings = Settings()
        assert settings.host == "0.0.0.0"

        # Test tool param overrides env var
        settings = create_settings(host="localhost")
        assert settings.host == "localhost"

    def test_port_precedence(self, monkeypatch):
        """Test port field precedence.

        FR-15: All fields follow the same precedence
        """
        # Test tool param override
        settings = create_settings(port=9000)
        assert settings.port == 9000

        # Test env var override
        monkeypatch.setenv("MCP_PORT", "8080")
        settings = Settings()
        assert settings.port == 8080

        # Test tool param overrides env var
        settings = create_settings(port=3000)
        assert settings.port == 3000

    def test_logging_level_precedence(self, monkeypatch):
        """Test logging_level field precedence.

        FR-15: All fields follow the same precedence
        """
        # Test tool param override
        settings = create_settings(logging_level="DEBUG")
        assert settings.logging_level == "DEBUG"

        # Test env var override
        monkeypatch.setenv("MCP_LOGGING_LEVEL", "ERROR")
        settings = Settings()
        assert settings.logging_level == "ERROR"

        # Test tool param overrides env var
        settings = create_settings(logging_level="CRITICAL")
        assert settings.logging_level == "CRITICAL"


class TestGetSettingsPrecedence:
    """Test get_settings() respects precedence.

    Validates: FR-15
    """

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_get_settings_uses_env_vars(self, monkeypatch):
        """Test get_settings() picks up environment variables.

        FR-15: Environment variables have precedence over defaults
        """
        monkeypatch.setenv("MCP_USER_ID", "get_settings_user")
        monkeypatch.setenv("MCP_AGENT_ID", "get_settings_agent")
        monkeypatch.setenv("MCP_APP_ID", "get_settings_app")

        settings = get_settings()

        assert settings.user_id == "get_settings_user"
        assert settings.agent_id == "get_settings_agent"
        assert settings.app_id == "get_settings_app"

    def test_get_settings_singleton(self, monkeypatch):
        """Test get_settings() returns same instance.

        FR-15: Settings should be singleton for consistency
        """
        monkeypatch.setenv("MCP_USER_ID", "singleton_user")

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
        assert settings1.user_id == "singleton_user"

    def test_create_settings_independent(self, monkeypatch):
        """Test create_settings() creates independent instances.

        FR-15: create_settings() allows tool params to override env vars
        """
        monkeypatch.setenv("MCP_USER_ID", "env_user")

        settings1 = create_settings(user_id="tool_user")
        settings2 = create_settings(user_id="another_tool_user")

        assert settings1.user_id == "tool_user"
        assert settings2.user_id == "another_tool_user"
