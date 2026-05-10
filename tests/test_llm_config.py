"""
# UT-6: Multi-LLM Support tests
# Validates: FR-20, AC-49, AC-50
# Scenario: Multi-LLM provider and model configuration
# AC-49: LLM config accepts provider and model
# AC-50: Multiple providers supported

Unit tests for Multi-LLM Support functionality.
Tests LLMConfig validation, provider/model extraction, and Multi-Provider support.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.memory.manager import (
    LLMConfig,
    MemoryManager,
    TenantScope,
)


class TestLLMConfig:
    """# FR-20: Multi-LLM Support - Compatible with various LLM providers"""

    def test_default_llm_config(self):
        """# AC-49: LLM config accepts provider and model (default values)"""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.2
        assert config.max_tokens == 2000

    def test_custom_llm_config(self):
        """# AC-49: LLM config accepts custom provider and model"""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus",
            temperature=0.5,
            max_tokens=1500
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 1500

    def test_provider_case_insensitive(self):
        """# AC-50: Multiple providers supported (case insensitive)"""
        config = LLMConfig(provider="ANTHROPIC", model="claude-3")
        assert config.provider == "anthropic"

    def test_valid_providers(self):
        """# AC-50: Multiple providers supported - all valid providers"""
        valid_providers = ["openai", "anthropic", "azure_openai", "ollama", "gemini", "huggingface", "groq", "deepseek"]
        for provider in valid_providers:
            config = LLMConfig(provider=provider, model="test-model")
            assert config.provider == provider

    def test_invalid_provider_rejected(self):
        """# AC-50: Multiple providers - invalid provider rejected"""
        with pytest.raises(ValueError) as exc_info:
            LLMConfig(provider="invalid_provider", model="test-model")
        assert "invalid_provider" in str(exc_info.value)
        assert "openai" in str(exc_info.value)  # Shows valid options

    def test_temperature_validation(self):
        """# AC-43: Validation errors contain descriptive messages"""
        # Valid temperature
        config = LLMConfig(temperature=1.5)
        assert config.temperature == 1.5

        # Invalid temperature too high
        with pytest.raises(ValueError) as exc_info:
            LLMConfig(temperature=3.0)
        assert "3.0" in str(exc_info.value)
        assert "0" in str(exc_info.value)  # Shows range

        # Invalid temperature negative
        with pytest.raises(ValueError):
            LLMConfig(temperature=-0.1)

    def test_max_tokens_validation(self):
        """# AC-43: Validation errors - invalid max_tokens rejected"""
        # Valid max_tokens
        config = LLMConfig(max_tokens=100)
        assert config.max_tokens == 100

        # Invalid max_tokens zero
        with pytest.raises(ValueError):
            LLMConfig(max_tokens=0)

        # Invalid max_tokens negative
        with pytest.raises(ValueError):
            LLMConfig(max_tokens=-1)


class TestLLMConfigToMem0:
    """# FR-20: Convert LLM config to Mem0 format"""

    def test_to_mem0_llm_config(self):
        """# AC-49: Provider and model extracted for Mem0 initialization"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=1500
        )
        mem0_config = config.to_mem0_llm_config()

        assert mem0_config["provider"] == "openai"
        assert mem0_config["config"]["model"] == "gpt-4o"
        assert mem0_config["config"]["temperature"] == 0.3
        assert mem0_config["config"]["max_tokens"] == 1500

    def test_to_mem0_llm_config_default(self):
        """# AC-49: Default LLM config converts correctly"""
        config = LLMConfig()
        mem0_config = config.to_mem0_llm_config()

        assert mem0_config["provider"] == "openai"
        assert mem0_config["config"]["model"] == "gpt-4o"
        assert mem0_config["config"]["temperature"] == 0.2
        assert mem0_config["config"]["max_tokens"] == 2000


class TestMemoryManagerMultiLLM:
    """# FR-20: MemoryManager with Multi-LLM Support"""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.get_all = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Memory 1", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
        ])
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    def test_memory_manager_with_llm_config(self, mock_mem0_client):
        """# AC-49: MemoryManager accepts LLM config with provider and model"""
        llm_config = LLMConfig(provider="anthropic", model="claude-3")
        manager = MemoryManager(mem0_client=mock_mem0_client, llm_config=llm_config)

        assert manager.llm_provider == "anthropic"
        assert manager.llm_model == "claude-3"

    def test_memory_manager_without_llm_config(self, mock_mem0_client):
        """# AC-49: MemoryManager uses default LLM config when not provided"""
        manager = MemoryManager(mem0_client=mock_mem0_client)

        assert manager.llm_provider == "openai"
        assert manager.llm_model == "gpt-4o"

    def test_memory_manager_llm_properties(self, mock_mem0_client):
        """# AC-49: LLM provider and model accessible via properties"""
        config = LLMConfig(provider="gemini", model="gemini-pro")
        manager = MemoryManager(mem0_client=mock_mem0_client, llm_config=config)

        # AC-49: Provider extracted from config
        assert manager.llm_provider == "gemini"

        # AC-49: Model extracted from config
        assert manager.llm_model == "gemini-pro"

    @pytest.mark.asyncio
    async def test_add_memory_with_llm_config(self, mock_mem0_client):
        """# FR-20: Memory operations work with custom LLM config"""
        llm_config = LLMConfig(provider="anthropic", model="claude-3")
        manager = MemoryManager(mem0_client=mock_mem0_client, llm_config=llm_config)

        scope = TenantScope(
            org_id="org-123",
            project_id="proj-456",
            user_id="user-789"
        )

        result = await manager.add_memory(
            scope=scope,
            content="Test memory content"
        )

        assert result.id == "mem-123"
        assert result.content == "Test memory content"

        # Verify LLM config is still accessible
        assert manager.llm_provider == "anthropic"
        assert manager.llm_model == "claude-3"


class TestMultiProviderSupport:
    """# AC-50: Multiple providers supported"""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 AsyncMemory client"""
        client = MagicMock()
        client.add = AsyncMock(return_value=[{"id": "mem-123", "created_at": "2024-01-01T00:00:00Z"}])
        client.search = AsyncMock(return_value=[])
        client.get_all = AsyncMock(return_value=[])
        client.delete = AsyncMock(return_value=True)
        client.delete_all = AsyncMock(return_value=True)
        return client

    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-4o"),
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-opus"),
        ("anthropic", "claude-3-sonnet"),
        ("gemini", "gemini-pro"),
        ("azure_openai", "gpt-4"),
        ("ollama", "llama2"),
        ("huggingface", "meta-llama/Llama-2-70b"),
    ])
    def test_various_providers_accepted(self, mock_mem0_client, provider, model):
        """# AC-50: Various LLM providers configurable"""
        config = LLMConfig(provider=provider, model=model)
        manager = MemoryManager(mem0_client=mock_mem0_client, llm_config=config)

        assert manager.llm_provider == provider
        assert manager.llm_model == model

    def test_provider_and_model_in_logging(self, mock_mem0_client):
        """# FR-20: Multi-LLM Support - provider and model visible in initialization"""
        config = LLMConfig(provider="anthropic", model="claude-3-opus")
        # MemoryManager logs info on init with provider/model
        manager = MemoryManager(mem0_client=mock_mem0_client, llm_config=config)

        # Manager should be initialized with the correct config
        assert manager.llm_provider == "anthropic"
        assert manager.llm_model == "claude-3-opus"


class TestLLMConfigBuildConfig:
    """Test LLMConfig._build_config() for all providers.

    These tests cover the missing lines 556-622 in settings.py where
    each LLM provider's configuration is built differently.
    """

    def test_build_config_openai_with_base_url(self):
        """Test OpenAI config building with custom base URL."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            openai_base_url="https://api.openai.com/v1"
        )
        cfg = config._build_config()
        assert cfg["model"] == "gpt-4o"
        assert cfg["openai_base_url"] == "https://api.openai.com/v1"

    def test_build_config_anthropic(self):
        """Test Anthropic config building."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet",
            anthropic_base_url="https://api.anthropic.com"
        )
        cfg = config._build_config()
        assert cfg["model"] == "claude-3-sonnet"
        assert cfg["anthropic_base_url"] == "https://api.anthropic.com"

    def test_build_config_azure_openai(self):
        """Test Azure OpenAI config building."""
        config = LLMConfig(
            provider="azure_openai",
            model="gpt-4",
            azure_api_version="2024-02-01",
            azure_deployment="gpt-4-deployment",
            azure_endpoint="https://example.openai.azure.com"
        )
        cfg = config._build_config()
        assert cfg["model"] == "gpt-4"
        assert cfg["api_version"] == "2024-02-01"
        assert cfg["azure_deployment"] == "gpt-4-deployment"
        assert cfg["azure_endpoint"] == "https://example.openai.azure.com"

    def test_build_config_azure_openai_structured(self):
        """Test Azure OpenAI Structured config building."""
        config = LLMConfig(
            provider="azure_openai_structured",
            model="gpt-4",
            azure_api_version="2024-02-01"
        )
        cfg = config._build_config()
        assert cfg["api_version"] == "2024-02-01"

    def test_build_config_ollama(self):
        """Test Ollama config building."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            ollama_base_url="http://localhost:11434"
        )
        cfg = config._build_config()
        assert cfg["model"] == "llama2"
        assert cfg["ollama_base_url"] == "http://localhost:11434"

    def test_build_config_groq(self):
        """Test Groq config building."""
        config = LLMConfig(
            provider="groq",
            model="llama-3.1-70b-versatile",
            groq_base_url="https://api.groq.com/openai/v1"
        )
        cfg = config._build_config()
        assert cfg["model"] == "llama-3.1-70b-versatile"
        assert cfg["groq_base_url"] == "https://api.groq.com/openai/v1"

    def test_build_config_together(self):
        """Test Together AI config building."""
        config = LLMConfig(
            provider="together",
            model="togethercomputer/m2-bert-80k-8k",
            together_base_url="https://api.together.xyz/v1"
        )
        cfg = config._build_config()
        assert cfg["together_base_url"] == "https://api.together.xyz/v1"

    def test_build_config_aws_bedrock(self):
        """Test AWS Bedrock config building."""
        config = LLMConfig(
            provider="aws_bedrock",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-west-2",
            aws_access_key_id="AKIA...",
            aws_secret_access_key="secret"
        )
        cfg = config._build_config()
        assert cfg["aws_region"] == "us-west-2"
        assert cfg["aws_access_key_id"] == "AKIA..."
        assert cfg["aws_secret_access_key"] == "secret"

    def test_build_config_deepseek(self):
        """Test DeepSeek config building."""
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-chat",
            deepseek_base_url="https://api.deepseek.com/v1"
        )
        cfg = config._build_config()
        assert cfg["deepseek_base_url"] == "https://api.deepseek.com/v1"

    def test_build_config_xai(self):
        """Test xAI config building."""
        config = LLMConfig(
            provider="xai",
            model="grok-1",
            xai_base_url="https://api.x.ai/v1"
        )
        cfg = config._build_config()
        assert cfg["xai_base_url"] == "https://api.x.ai/v1"

    def test_build_config_lmstudio(self):
        """Test LM Studio config building."""
        config = LLMConfig(
            provider="lmstudio",
            model="local-model",
            lmstudio_base_url="http://localhost:1234/v1"
        )
        cfg = config._build_config()
        assert cfg["lmstudio_base_url"] == "http://localhost:1234/v1"

    def test_build_config_vllm(self):
        """Test vLLM config building."""
        config = LLMConfig(
            provider="vllm",
            model="meta-llama/Llama-2-70b",
            vllm_base_url="http://localhost:8000/v1"
        )
        cfg = config._build_config()
        assert cfg["vllm_base_url"] == "http://localhost:8000/v1"

    def test_build_config_litellm(self):
        """Test LiteLLM config building."""
        config = LLMConfig(
            provider="litellm",
            model="gpt-4",
            litellm_base_url="https://litellm.example.com/v1"
        )
        cfg = config._build_config()
        assert cfg["litellm_base_url"] == "https://litellm.example.com/v1"

    def test_build_config_huggingface(self):
        """Test HuggingFace config building."""
        config = LLMConfig(
            provider="huggingface",
            model="meta-llama/Llama-2-70b",
            huggingface_base_url="https://api-inference.huggingface.co/models"
        )
        cfg = config._build_config()
        assert cfg["huggingface_base_url"] == "https://api-inference.huggingface.co/models"

    def test_build_config_with_top_p_and_top_k(self):
        """Test LLM config with top_p and top_k parameters."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            top_p=0.9,
            top_k=40
        )
        cfg = config._build_config()
        assert cfg["top_p"] == 0.9
        assert cfg["top_k"] == 40

    def test_build_config_without_top_p_top_k(self):
        """Test LLM config without top_p and top_k (they're optional)."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4o"
        )
        cfg = config._build_config()
        assert "top_p" not in cfg
        assert "top_k" not in cfg
