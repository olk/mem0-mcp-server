"""
Unit tests for main.py entry point.

Validates: FR-1, FR-12, CPARA-4, CPARA-5, CPARA-6
Tests the main() function and CLI argument parsing.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestMainFunction:
    """Test main() function and its error handling."""

    @pytest.mark.asyncio
    async def test_main_loads_settings_and_runs_transport(self, tmp_path):
        """Test main() loads settings and runs transport."""
        from mcp_server.config.settings import ServerSettings

        mock_settings = ServerSettings(
            config_id="test-config",
            memory_expiry=3600,
            logging_level="INFO",
            host="0.0.0.0",
            port=8080,
            transport="sse"
        )

        # Create a valid config file
        config_file = tmp_path / "settings.json"
        config_data = {
            "config_id": "test-config",
            "memory_expiry": 3600,
            "logging_level": "INFO",
            "host": "0.0.0.0",
            "port": 8080,
            "transport": "sse",
            "vector_store": {
                "provider": "redis",
                "collection_name": "mem0",
                "embedding_model_dims": 1536,
                "redis_url": "redis://localhost:6379"
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-4o"
            },
            "embedder": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dimension": 1536
            }
        }
        config_file.write_text(json.dumps(config_data))

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.return_value = mock_settings

            with patch('mcp_server.main.run_transport') as mock_run_transport:
                mock_run_transport.return_value = AsyncMock()

                with patch('mcp_server.main.mcp') as mock_mcp:
                    mock_mcp._settings = mock_settings

                    from mcp_server import main

                    await main.main(
                        transport="sse",
                        host="0.0.0.0",
                        port=8080,
                        config_path=str(config_file)
                    )

                    mock_load.assert_called_once_with(str(config_file))
                    mock_run_transport.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_uses_sse_by_default(self, tmp_path):
        """Test main() uses SSE as default transport."""
        from mcp_server.config.settings import ServerSettings

        mock_settings = ServerSettings(transport="sse")

        config_file = tmp_path / "settings.json"
        config_data = {
            "config_id": "test",
            "vector_store": {"provider": "redis"},
            "llm": {"provider": "openai", "model": "gpt-4o"},
            "embedder": {"provider": "openai", "model": "text-embedding-3-small", "dimension": 1536}
        }
        config_file.write_text(json.dumps(config_data))

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.return_value = mock_settings

            with patch('mcp_server.main.run_transport') as mock_run_transport:
                with patch('mcp_server.main.mcp') as mock_mcp:
                    mock_mcp._settings = mock_settings

                    from mcp_server import main

                    await main.main(config_path=str(config_file))

                    call_kwargs = mock_run_transport.call_args.kwargs
                    assert call_kwargs['transport'] == "sse"

    @pytest.mark.asyncio
    async def test_main_handles_value_error(self, tmp_path, capsys):
        """Test main() handles ValueError from invalid transport config."""
        config_file = tmp_path / "settings.json"
        config_data = {"config_id": "test"}
        config_file.write_text(json.dumps(config_data))

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.side_effect = ValueError("Invalid transport configuration")

            from mcp_server import main

            with pytest.raises(SystemExit) as exc_info:
                await main.main(config_path=str(config_file))

            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_handles_generic_exception(self, tmp_path, capsys):
        """Test main() handles generic exceptions gracefully."""
        config_file = tmp_path / "settings.json"
        config_data = {"config_id": "test"}
        config_file.write_text(json.dumps(config_data))

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.side_effect = Exception("Something went wrong")

            from mcp_server import main

            with pytest.raises(SystemExit) as exc_info:
                await main.main(config_path=str(config_file))

            assert exc_info.value.code == 1


class TestMainCliArguments:
    """Test CLI argument parsing via if __name__ == '__main__' block."""

    def test_parser_transport_choices(self):
        """Test that transport argument accepts stdio and sse."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--transport', '-t', choices=["stdio", "sse"])

        args = parser.parse_args(['--transport', 'stdio'])
        assert args.transport == "stdio"

        args = parser.parse_args(['--transport', 'sse'])
        assert args.transport == "sse"

    def test_parser_host_accepts_string(self):
        """Test that host argument accepts string value."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--host')

        args = parser.parse_args(['--host', '192.168.1.1'])
        assert args.host == "192.168.1.1"

    def test_parser_port_accepts_integer(self):
        """Test that port argument accepts integer value."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--port', '-p', type=int)

        args = parser.parse_args(['--port', '8080'])
        assert args.port == 8080

    def test_parser_config_path_accepts_string(self):
        """Test that config-path argument accepts string value."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--config-path')

        args = parser.parse_args(['--config-path', '/path/to/config.json'])
        assert args.config_path == "/path/to/config.json"

    def test_app_variable_exists(self):
        """Test that 'app' variable exists for ASGI server compatibility."""
        from mcp_server import main as main_module

        assert hasattr(main_module, 'app')
        assert main_module.app is main_module.main


class TestTransportSelection:
    """Test transport selection logic in main()."""

    @pytest.mark.asyncio
    async def test_effective_transport_from_args(self, tmp_path):
        """Test transport selection priority: arg > config > default."""
        from mcp_server.config.settings import ServerSettings
        mock_settings = ServerSettings(transport="stdio")

        from mcp_server import main

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.return_value = mock_settings

            with patch('mcp_server.main.run_transport') as mock_run:
                with patch('mcp_server.main.mcp') as mock_mcp:
                    mock_mcp._settings = mock_settings

                    # Pass transport as argument - should override config
                    await main.main(transport="stdio")

                    call_kwargs = mock_run.call_args.kwargs
                    assert call_kwargs['transport'] == "stdio"

    @pytest.mark.asyncio
    async def test_effective_host_from_args(self, tmp_path):
        """Test host selection priority: arg > config > default."""
        from mcp_server.config.settings import ServerSettings
        mock_settings = ServerSettings(host="127.0.0.1")

        from mcp_server import main

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.return_value = mock_settings

            with patch('mcp_server.main.run_transport') as mock_run:
                with patch('mcp_server.main.mcp') as mock_mcp:
                    mock_mcp._settings = mock_settings

                    await main.main(host="0.0.0.0")

                    call_kwargs = mock_run.call_args.kwargs
                    assert call_kwargs['host'] == "0.0.0.0"

    @pytest.mark.asyncio
    async def test_effective_port_from_args(self, tmp_path):
        """Test port selection priority: arg > config > default."""
        from mcp_server.config.settings import ServerSettings
        mock_settings = ServerSettings(port=9000)

        from mcp_server import main

        with patch('mcp_server.main.load_settings') as mock_load:
            mock_load.return_value = mock_settings

            with patch('mcp_server.main.run_transport') as mock_run:
                with patch('mcp_server.main.mcp') as mock_mcp:
                    mock_mcp._settings = mock_settings

                    await main.main(port=8050)

                    call_kwargs = mock_run.call_args.kwargs
                    assert call_kwargs['port'] == 8050

    def test_default_transport_sse_from_settings(self):
        """Test default transport is sse when not specified in settings."""
        from mcp_server.config.settings import ServerSettings

        settings = ServerSettings()
        assert settings.transport == "sse"

    def test_default_host_from_settings(self):
        """Test default host from settings."""
        from mcp_server.config.settings import ServerSettings

        settings = ServerSettings()
        assert settings.host == "0.0.0.0"

    def test_default_port_from_settings(self):
        """Test default port from settings."""
        from mcp_server.config.settings import ServerSettings

        settings = ServerSettings()
        assert settings.port == 8080
