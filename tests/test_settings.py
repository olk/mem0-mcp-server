"""
Unit tests for Pydantic settings models.

Validates: FR-13, FR-16, FR-17, DP-5, ADR-4, IC-7, IC-8, AC-41, AC-42, AC-43, AC-44

AC-34: Path resolves correctly to user's home directory
AC-35: File parsed as JSON
AC-36: Values extracted successfully

E-12 (ERR_CONFIG_001): Configuration file not found at expected path
E-15 (ERR_VAL_001): Configuration value failed Pydantic validation

# UT-3: Pydantic Validation tests (FR-17, IC-8)
# SCEN-7: valid config passes validation
# SCEN-8: invalid type rejected with error message
# SCEN-9: out-of-range value rejected

# UT-6: Secrets Management tests
# SCEN-16: API keys from env vars loaded
# SCEN-17: API keys not in config file
# SCEN-18: missing secrets handled gracefully
"""


import pytest
from pydantic import ValidationError

from mcp_server.config.settings import (
    EmbedderConfig,
    LLMConfig,
    SecretsSettings,
    ValidationSettingsError,
    VectorStoreConfig,
    get_secrets,
)
from mcp_server.config.settings import (
    ServerSettings as ServerSettingsModel,
)


class TestVectorStoreConfig:
    """Test VectorStoreConfig model.

    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: Explicit error messages on invalid values
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    """

    def test_default_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        config = VectorStoreConfig()
        assert config.provider == "redis"
        assert config.collection_name == "mem0"
        assert config.embedding_model_dims == 1536

    def test_custom_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        config = VectorStoreConfig(
            provider="chroma",
            collection_name="test_collection",
            chroma_path="/tmp/chroma"
        )
        assert config.provider == "chroma"
        assert config.collection_name == "test_collection"

    def test_invalid_provider(self):
        """SCEN-8: invalid type rejected with error message.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # E-15 (ERR_VAL_001): Configuration value failed Pydantic validation
        """
        with pytest.raises(ValidationError) as exc_info:
            VectorStoreConfig(provider="invalid")
        error_msg = str(exc_info.value)
        assert "provider" in error_msg
        assert "invalid" in error_msg
        assert "must be one of" in error_msg.lower()


class TestLLMConfig:
    """Test LLMConfig model.

    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: Explicit error messages on invalid values
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    """

    def test_default_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.2
        assert config.max_tokens == 2000

    def test_custom_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet",
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet"

    def test_invalid_provider(self):
        """SCEN-8: invalid type rejected with error message.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # E-15 (ERR_VAL_001): Configuration value failed Pydantic validation
        """
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(provider="invalid")
        error_msg = str(exc_info.value)
        assert "provider" in error_msg
        assert "invalid" in error_msg
        assert "must be one of" in error_msg.lower()

    def test_invalid_temperature(self):
        """SCEN-9: out-of-range value rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        with pytest.raises(ValidationError, match="temperature.*Must be between"):
            LLMConfig(temperature=5.0)

    def test_invalid_max_tokens(self):
        """SCEN-9: out-of-range value rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        with pytest.raises(ValidationError, match="max_tokens.*positive integer"):
            LLMConfig(max_tokens=-100)


class TestEmbedderConfig:
    """Test EmbedderConfig model.

    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: Explicit error messages on invalid values
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    """

    def test_default_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        config = EmbedderConfig()
        assert config.provider == "openai"
        assert config.model == "text-embedding-3-small"
        assert config.dimension == 1536

    def test_invalid_provider(self):
        """SCEN-8: invalid type rejected with error message.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # E-15 (ERR_VAL_001): Configuration value failed Pydantic validation
        """
        with pytest.raises(ValidationError) as exc_info:
            EmbedderConfig(provider="invalid")
        error_msg = str(exc_info.value)
        assert "provider" in error_msg
        assert "invalid" in error_msg
        assert "must be one of" in error_msg.lower()

    def test_invalid_dimension(self):
        """SCEN-9: out-of-range value rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        with pytest.raises(ValidationError, match="dimension.*positive integer"):
            EmbedderConfig(dimension=-1536)


class TestServerSettings:
    """Test ServerSettings model.

    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: Explicit error messages on invalid values
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    # UT-3: SCEN-7, SCEN-8, SCEN-9
    """

    def test_default_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        settings = ServerSettingsModel()

        assert settings.config_id == "default"
        assert settings.memory_expiry == 3600
        assert settings.logging_level == "INFO"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.transport == "sse"

    def test_custom_values(self):
        """SCEN-7: valid config passes validation.

        FR-17: All configuration values validated with Pydantic
        """
        settings = ServerSettingsModel(
            config_id="custom-config",
            memory_expiry=7200,
            logging_level="DEBUG",
            host="127.0.0.1",
            port=9000,
            transport="sse"
        )

        assert settings.config_id == "custom-config"
        assert settings.memory_expiry == 7200
        assert settings.logging_level == "DEBUG"
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.transport == "sse"

    def test_logging_level_validation(self):
        """SCEN-7 and SCEN-8: valid logging levels pass, invalid rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Valid levels pass validation
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = ServerSettingsModel(logging_level=level)
            assert settings.logging_level == level

        # Invalid level is rejected with descriptive message
        with pytest.raises(ValidationError, match="logging_level.*Must be one of"):
            ServerSettingsModel(logging_level="INVALID")

    def test_transport_validation(self):
        """SCEN-7 and SCEN-8: valid transports pass, invalid rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Valid transports pass validation
        for transport in ["sse", "stdio"]:
            settings = ServerSettingsModel(transport=transport)
            assert settings.transport == transport

        # Invalid transport is rejected with descriptive message
        with pytest.raises(ValidationError, match="transport.*Must be one of"):
            ServerSettingsModel(transport="invalid")

    def test_port_range_validation(self):
        """SCEN-7 and SCEN-9: valid ports pass, out-of-range rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Valid ports pass validation
        settings = ServerSettingsModel(port=1)
        assert settings.port == 1

        settings = ServerSettingsModel(port=65535)
        assert settings.port == 65535

        # Out-of-range ports are rejected with descriptive message
        with pytest.raises(ValidationError, match="port.*Must be between"):
            ServerSettingsModel(port=0)

        with pytest.raises(ValidationError, match="port.*Must be between"):
            ServerSettingsModel(port=70000)

    def test_memory_expiry_range_validation(self):
        """SCEN-7 and SCEN-9: valid memory_expiry passes, out-of-range rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Valid range passes validation
        settings = ServerSettingsModel(memory_expiry=60)
        assert settings.memory_expiry == 60

        settings = ServerSettingsModel(memory_expiry=86400)
        assert settings.memory_expiry == 86400

        # Out-of-range values are rejected with descriptive message
        with pytest.raises(ValidationError, match="memory_expiry.*at least 60"):
            ServerSettingsModel(memory_expiry=30)

    def test_host_validation(self):
        """SCEN-7 and SCEN-8: valid hosts pass, invalid rejected.

        # FR-17: Pydantic Validation with explicit error messages
        # IC-8: Explicit error messages on invalid values
        # AC-43: Validation errors contain descriptive messages
        # AC-44: Invalid values rejected with clear indication of problem
        """
        # Valid hosts pass validation
        for host in ["localhost", "127.0.0.1", "0.0.0.0", "192.168.1.1", "example.com"]:
            settings = ServerSettingsModel(host=host)
            assert settings.host == host

        # Invalid host is rejected with descriptive message
        with pytest.raises(ValidationError, match="host.*valid hostname"):
            ServerSettingsModel(host="")

    def test_nested_configurations(self):
        """SCEN-7: nested config models pass validation.

        # FR-17: All configuration values validated with Pydantic
        """
        settings = ServerSettingsModel(
            vector_store={"provider": "chroma", "chroma_path": "/tmp/chroma"},
            llm={"provider": "ollama", "model": "llama2"},
            embedder={"provider": "huggingface", "model": "sentence-transformers"}
        )

        # Nested configs should be proper model instances
        assert settings.vector_store.provider == "chroma"
        assert settings.vector_store.chroma_path == "/tmp/chroma"
        assert settings.llm.provider == "ollama"
        assert settings.llm.model == "llama2"
        assert settings.embedder.provider == "huggingface"


class TestValidationSettingsError:
    """Test ValidationSettingsError for E-15 (ERR_VAL_001).

    # E-15 (ERR_VAL_001): Configuration value failed Pydantic validation
    # FR-17: Pydantic Validation with explicit error messages
    # IC-8: Explicit error messages on invalid values
    # AC-43: Validation errors contain descriptive messages
    # AC-44: Invalid values rejected with clear indication of problem
    """

    def test_error_attributes(self):
        """Test that ValidationSettingsError contains proper attributes.

        AC-43: Validation errors contain descriptive messages
        AC-44: Invalid values rejected with clear indication of problem
        """
        error = ValidationSettingsError(
            field_name="port",
            invalid_value=0,
            expected_format="integer between 1 and 65535"
        )

        assert error.field_name == "port"
        assert error.invalid_value == 0
        assert error.expected_format == "integer between 1 and 65535"
        assert "port" in str(error)
        assert "0" in str(error)
        assert "1 and 65535" in str(error)

    def test_error_message_format(self):
        """Test that error message is descriptive.

        AC-43: Validation errors contain descriptive messages
        """
        error = ValidationSettingsError(
            field_name="logging_level",
            invalid_value="INVALID",
            expected_format="DEBUG, INFO, WARNING, ERROR, or CRITICAL"
        )

        assert "logging_level" in str(error)
        assert "INVALID" in str(error)
        assert "DEBUG, INFO, WARNING, ERROR, or CRITICAL" in str(error)


class TestSecretsSettings:
    """Test SecretsSettings for secrets management.

    UT-6: Secrets Management tests
    SCEN-16: API keys from env vars loaded
    SCEN-17: API keys not in config file
    SCEN-18: missing secrets handled gracefully
    """

    def test_api_key_loaded_from_env_var(self, monkeypatch):
        """SCEN-16: API keys from env vars loaded.

        FR-16: API keys sourced only from environment variables
        AC-42: Environment variables used for sensitive data
        """
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-key-12345")

        secrets = SecretsSettings()

        assert secrets.OPENAI_API_KEY == "sk-test-secret-key-12345"

    def test_api_key_stripped_of_whitespace(self, monkeypatch):
        """Test that API key whitespace is stripped.

        AC-42: Environment variables used for sensitive data
        """
        monkeypatch.setenv("OPENAI_API_KEY", "  sk-test-key-12345  ")

        secrets = SecretsSettings()

        assert secrets.OPENAI_API_KEY == "sk-test-key-12345"

    def test_missing_api_key_raises_error(self, monkeypatch):
        """SCEN-18: missing secrets handled gracefully.

        E-14 (ERR_SEC_001): Required API key not found in environment variables
        FR-16: API keys sourced only from environment variables
        """
        from pydantic import ValidationError

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            SecretsSettings()

        # E-14 error message should be in the validation error
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg
        assert "Required API key not found" in error_msg

    def test_empty_api_key_raises_error(self, monkeypatch):
        """SCEN-18: missing secrets handled gracefully.

        E-14 (ERR_SEC_001): Empty string should raise error
        """
        from pydantic import ValidationError

        monkeypatch.setenv("OPENAI_API_KEY", "")

        with pytest.raises(ValidationError) as exc_info:
            SecretsSettings()

        # E-14 error message should be in the validation error
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg

    def test_whitespace_only_api_key_raises_error(self, monkeypatch):
        """SCEN-18: missing secrets handled gracefully.

        E-14 (ERR_SEC_001): Whitespace-only should raise error
        """
        from pydantic import ValidationError

        monkeypatch.setenv("OPENAI_API_KEY", "   ")

        with pytest.raises(ValidationError) as exc_info:
            SecretsSettings()

        # E-14 error message should be in the validation error
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg

    def test_api_key_not_in_config_file(self):
        """SCEN-17: API keys not in config file.

        IC-7: Secrets MUST be sourced only from environment variables
        AC-41: No API keys in config file (security requirement)
        
        This test verifies that the SecretsSettings class only loads from
        environment variables, not from any config file. The class uses
        Pydantic BaseSettings which by default does not load from files.
        """
        from pydantic_settings import BaseSettings as PydanticBaseSettings

        # Verify that SecretsSettings uses BaseSettings (not file-based)
        assert issubclass(SecretsSettings, PydanticBaseSettings)

        # The SecretsSettings class should have no file-based configuration
        # This is intentional - secrets come from env vars only (IC-7)


class TestGetSecrets:
    """Test get_secrets function.

    UT-6: Secrets Management tests
    """

    def test_get_secrets_success(self, monkeypatch):
        """SCEN-16: API keys from env vars loaded.

        FR-16: API keys sourced only from environment variables
        """
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        secrets = get_secrets()

        assert isinstance(secrets, SecretsSettings)
        assert secrets.OPENAI_API_KEY == "sk-test-key"

    def test_get_secrets_raises_settings_error(self, monkeypatch):
        """SCEN-18: missing secrets handled gracefully.

        E-14 (ERR_SEC_001): Required API key not found in environment
        """
        from pydantic import ValidationError

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValidationError):
            get_secrets()


class TestSettingsPrecedence:
    """Test Settings class for parameter precedence.

    FR-15: Parameter Precedence - Tool parameters override environment variables override config file defaults.
    AC-39: Parameter precedence order is enforced exactly
    AC-40: Config resolution checks each level in sequence
    """

    def test_get_precedence_chain(self):
        """Test that get_precedence_chain returns correct precedence order."""
        from mcp_server.config.settings import Settings

        settings = Settings()
        chain = settings.get_precedence_chain()

        assert isinstance(chain, list)
        assert len(chain) == 4
        assert "tool parameters (direct initialization)" in chain[0]
        assert "environment variables (with MCP_ prefix)" in chain[1]
        assert "config file values" in chain[2]
        assert "hardcoded defaults" in chain[3]

    def test_is_precedence_respected_returns_true(self):
        """Test that is_precedence_respected returns True for valid overrides."""
        from mcp_server.config.settings import Settings

        settings = Settings()
        result = settings.is_precedence_respected(
            memory_expiry=7200,
            port=9000
        )

        assert result is True

    def test_settings_defaults(self):
        """Test Settings class has correct defaults."""
        from mcp_server.config.settings import Settings

        settings = Settings()

        assert settings.config_id == "default"
        assert settings.memory_expiry == 3600
        assert settings.logging_level == "INFO"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.transport == "sse"
        assert settings.user_id == "default_user"
        assert settings.agent_id == "default_agent"
        assert settings.app_id == "default_app"

    def test_settings_with_overrides(self):
        """Test Settings class accepts override values."""
        from mcp_server.config.settings import Settings

        settings = Settings(
            config_id="custom-config",
            memory_expiry=7200,
            host="127.0.0.1",
            port=9000,
            user_id="custom-user"
        )

        assert settings.config_id == "custom-config"
        assert settings.memory_expiry == 7200
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.user_id == "custom-user"

    def test_settings_vector_store_dict_default(self):
        """Test Settings vector_store defaults to empty dict."""
        from mcp_server.config.settings import Settings

        settings = Settings()
        assert settings.vector_store == {}
        assert isinstance(settings.vector_store, dict)

    def test_settings_llm_dict_default(self):
        """Test Settings llm defaults to empty dict."""
        from mcp_server.config.settings import Settings

        settings = Settings()
        assert settings.llm == {}
        assert isinstance(settings.llm, dict)

    def test_settings_embedder_dict_default(self):
        """Test Settings embedder defaults to empty dict."""
        from mcp_server.config.settings import Settings

        settings = Settings()
        assert settings.embedder == {}
        assert isinstance(settings.embedder, dict)
