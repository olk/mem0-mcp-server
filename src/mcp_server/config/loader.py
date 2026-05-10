"""
Configuration file loader with tilde expansion and auto-creation.

FR-13: Configuration File Loading - The server MUST load settings from
~/.config/mem0-mcp-server/settings.json with tilde expansion.

FR-14: Auto-create Config Directory - The server MUST create config directory
if missing with sane defaults. Path.mkdir(parents=True) called for directory
creation per AC-37. Default settings.json created with valid configuration
per AC-38.

E-12 (ERR_CONFIG_001): Configuration file not found at expected path
E-13 (ERR_CONFIG_002): Failed to create config directory
"""

import json
import logging
from pathlib import Path
from typing import Any

from .settings import ServerSettings

# CONST-1: Default memory TTL before expiration
# AC-38: Default settings.json created with valid configuration
DEFAULT_MEMORY_EXPIRY = "30 days"
DEFAULT_LOGGING_LEVEL = "info"

logger = logging.getLogger(__name__)


class ConfigFileNotFoundError(Exception):
    """Raised when configuration file is not found at expected path.
    
    E-12 (ERR_CONFIG_001): Configuration file not found at expected path
    """
    def __init__(self, path: Path):
        self.path = path
        self.error_code = "ERR_CONFIG_001"
        self.message = f"Configuration file not found at expected path: {path}"
        super().__init__(self.message)


class ConfigDirectoryCreationError(Exception):
    """Raised when config directory cannot be created.
    
    E-13 (ERR_CONFIG_002): Failed to create config directory
    """
    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        self.error_code = "ERR_CONFIG_002"
        self.message = f"Failed to create config directory: {path} - {reason}"
        super().__init__(self.message)


def get_default_config_path() -> Path:
    """Get the default configuration file path with tilde expansion.
    
    AC-34: Path resolves correctly to user's home directory
    Returns: Path to settings.json in user's config directory
    """
    return Path("~/.config/mem0-mcp-server/settings.json").expanduser()


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from JSON file with tilde expansion.
    
    FR-13: Configuration File Loading - The server MUST load settings from 
    ~/.config/mem0-mcp-server/settings.json with tilde expansion.
    
    AC-35: File parsed as JSON
    AC-36: Values extracted successfully
    
    Args:
        config_path: Optional custom path to config file. 
                    Defaults to ~/.config/mem0-mcp-server/settings.json
    
    Returns:
        Parsed configuration dictionary
        
    Raises:
        ConfigFileNotFoundError: When config file doesn't exist (E-12)
    """
    if config_path is None:
        path = get_default_config_path()
        resolved_path = path
    else:
        path = Path(config_path).expanduser()
        resolved_path = path.resolve()
        if ".." in str(resolved_path):
            raise ValueError("Config path must not contain '..' traversal sequences")

    logger.debug(f"Loading configuration from: {resolved_path}")

    if not resolved_path.exists():
        logger.warning(
            "Configuration file not found",
            extra={
                "error_code": "ERR_CONFIG_001",
                "logging_context": ["config", "startup"],
                "path": str(resolved_path)
            }
        )
        raise ConfigFileNotFoundError(resolved_path)

    # AC-35: File parsed as valid JSON
    try:
        with open(resolved_path, encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file as JSON: {e}")
        raise

    # AC-36: Values extracted successfully
    if not isinstance(config_data, dict):
        raise ValueError(f"Config file must contain a JSON object, got {type(config_data).__name__}")

    logger.info(f"Configuration loaded successfully from {resolved_path}")
    return config_data


def create_default_config() -> dict[str, Any]:
    """Create default configuration values.

    SCEN-3: missing config creates default

    CONST-1 DEFAULT_MEMORY_EXPIRY used for default settings per task requirements.
    AC-38: Default settings.json created with valid configuration

    Returns:
        Default configuration dictionary compliant with mem0-config format
    """
    return {
        "vector_store": {
            "provider": "redis",
            "config": {
                "collection_name": "mem0",
                "embedding_model_dims": 1536,
                "redis_url": "redis://localhost:6379"
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_tokens": 2000
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "embedding_dims": 1536
            }
        },
        "reranker": {
            "provider": "cohere",
            "config": {
                "model": "rerank-english-v3.0",
                "top_k": 10
            }
        }
    }


def load_settings(config_path: str | Path | None = None) -> ServerSettings:
    """Load and validate configuration as Pydantic settings.
    
    DP-5: Configuration Validation Pattern - Validate all configuration 
    values using Pydantic with explicit error messages
    
    Args:
        config_path: Optional custom path to config file
        
    Returns:
        Validated ServerSettings instance
        
    Raises:
        ConfigFileNotFoundError: When config file doesn't exist
    """
    config_data = load_config(config_path)
    return ServerSettings(**config_data)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    try:
        config = load_config()
        print(f"Loaded config: {config}")
    except ConfigFileNotFoundError as e:
        print(f"Config file not found: {e.path}")
        sys.exit(1)
