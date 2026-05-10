"""
# FR-1: MCP Protocol Integration - Server entry point
# FR-12: SSE Transport for HTTP-based remote connections
# DP-4: Strategy Pattern - Transport selection at runtime
# CPARA-4: HOST (default: 0.0.0.0)
# CPARA-5: PORT (default: 8050)
# CPARA-6: TRANSPORT (default: sse, values: stdio, sse)

Application entry point for Mem0 MCP Server.
Handles transport selection and graceful error handling.
"""

import argparse
import asyncio
import logging
import sys

import mcp_server.prompts  # noqa: F401 - registers all MCP prompts
import mcp_server.tools  # noqa: F401 - registers all MCP tools
from mcp_server import mcp
from mcp_server.config.loader import load_settings
from mcp_server.transport import run_transport

logger = logging.getLogger(__name__)


async def main(
    transport: str | None = None,
    host: str | None = None,
    port: int | None = None,
    config_path: str | None = None,
) -> None:
    """Main entry point for the MCP server.

    Loads configuration, sets up the FastMCP server with lifespan,
    and runs the appropriate transport.

    Args:
        transport: Transport type ("stdio" or "sse"), overrides config
        host: Server bind address for SSE, overrides config
        port: Server bind port for SSE, overrides config
        config_path: Optional path to config file
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
        force=True,
    )

    try:
        settings = load_settings(config_path)

        effective_transport = transport or settings.transport or "sse"
        effective_host = host or settings.host or "0.0.0.0"
        effective_port = port or settings.port or 8050

        mcp.settings = settings

        await run_transport(
            transport=effective_transport,
            host=effective_host,
            port=effective_port,
            mcp_server=mcp,
        )
    except ValueError as e:
        logger.critical(f"Invalid transport configuration: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Failed to start MCP server: {e}")
        print(f"Error: Failed to start MCP server: {e}", file=sys.stderr)
        sys.exit(1)


app = main  # ASGI server compatibility: Uvicorn/Gunicorn look for 'app' variable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mem0 MCP Server",
        epilog="Can also be run via: uvicorn main:app or fastmcp run main.py",
    )
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse"],
        help="Transport type (overrides config)",
    )
    parser.add_argument(
        "--host",
        help="Server bind address for SSE (overrides config)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        help="Server bind port for SSE (overrides config)",
    )
    parser.add_argument(
        "--config-path",
        help="Path to config file (default: ~/.config/mem0-mcp-server/settings.json)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )
    asyncio.run(main(
        transport=args.transport,
        host=args.host,
        port=args.port,
        config_path=args.config_path,
    ))
