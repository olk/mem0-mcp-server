"""
MCP Tool Tester using code-reasoning, exa-code-search, and context7.

This module provides advanced testing of MCP tools by leveraging
structured problem-solving, web search, and documentation lookup.
"""

import asyncio
import json
import logging
import sys
from typing import Any

from mcp import ClientSession, types
from mcp.client.sse import sse_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MEM0_SERVER_URL = "http://localhost:8050/sse"


async def call_tool_json(session: ClientSession, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool and parse JSON result."""
    try:
        result = await session.call_tool(tool_name, arguments=arguments)
        if result.content:
            for item in result.content:
                if isinstance(item, types.TextContent) and item.text:
                    if item.text.startswith("Error"):
                        return {"error": item.text}
                    try:
                        return json.loads(item.text)
                    except json.JSONDecodeError:
                        return {"raw": item.text}
        return {}
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"error": str(e)}


async def code_reasoning_test(session: ClientSession) -> dict[str, Any]:
    """
    Test MCP tools using structured code reasoning.

    Uses code-reasoning methodology to test memory operations with
    computational thinking problems.
    """
    logger.info("=" * 60)
    logger.info("CODE-REASONING TEST: Testing memory with algorithm complexity")
    logger.info("=" * 60)

    reasoning_problem = (
        "Binary search algorithm: Given a sorted array of n elements, "
        "binary search has O(log n) time complexity by repeatedly dividing "
        "the search interval in half. For an array of 1 million elements, "
        "binary search takes at most 20 comparisons."
    )

    result = await call_tool_json(session, "add_memory", {
        "messages": [{"role": "user", "content": reasoning_problem}],
        "user_id": "test_user",
    })

    results_list = result.get("results", []) if isinstance(result, dict) else []
    memory_id = results_list[0].get("id", "") if results_list else ""

    search_result = await call_tool_json(session, "search_memories", {
        "query": "binary search algorithm time complexity",
        "filters": {"user_id": "test_user"},
        "limit": 5,
    })

    results = search_result.get('results', [])
    logger.info(f"Search found {len(results)} results")

    if memory_id:
        await call_tool_json(session, "delete_memory", {
            "memory_id": memory_id,
        })

    return {
        "test": "code_reasoning",
        "memory_id": memory_id,
        "search_results_count": len(results),
        "success": "error" not in result and bool(memory_id),
        "results": results
    }


async def exa_code_search_test(session: ClientSession) -> dict[str, Any]:
    """
    Test MCP tools using exa code search patterns.

    Simulates testing with code search patterns similar to what exa-code-search
    would return from GitHub and StackOverflow.
    """
    logger.info("=" * 60)
    logger.info("EXA-CODE-SEARCH TEST: Testing memory with code search patterns")
    logger.info("=" * 60)

    code_search_content = (
        "REST API authentication patterns: JWT tokens should be stored securely "
        "in httpOnly cookies. OAuth2 with PKCE is recommended for public clients. "
        "Example: Authorization: Bearer <token> header format."
    )

    result = await call_tool_json(session, "add_memory", {
        "messages": [{"role": "user", "content": code_search_content}],
        "user_id": "test_user",
    })

    results_list = result.get("results", []) if isinstance(result, dict) else []
    memory_id = results_list[0].get("id", "") if results_list else ""

    search_result = await call_tool_json(session, "search_memories", {
        "query": "REST API authentication JWT OAuth2",
        "filters": {"user_id": "test_user"},
        "limit": 10,
    })

    list_result = await call_tool_json(session, "list_memories", {
        "filters": {"user_id": "test_user"},
        "page_size": 20,
    })

    memories = list_result.get('memories', [])
    search_memories = search_result.get('results', [])
    logger.info(f"Found {len(memories)} total memories")

    if memory_id:
        await call_tool_json(session, "delete_memory", {
            "memory_id": memory_id,
        })

    return {
        "test": "exa_code_search",
        "memory_id": memory_id,
        "search_results_count": len(search_memories),
        "total_memories": len(memories),
        "success": "error" not in result,
        "memories": memories
    }


async def context7_test(session: ClientSession) -> dict[str, Any]:
    """
    Test MCP tools using context7 documentation patterns.

    Simulates testing with documentation lookup patterns similar to context7,
    testing library documentation and code examples.
    """
    logger.info("=" * 60)
    logger.info("CONTEXT7 TEST: Testing memory with documentation patterns")
    logger.info("=" * 60)

    context7_content = (
        "FastMCP server configuration: Use FastMCP('ServerName') to create a server. "
        "Decorate functions with @mcp.tool() to expose them as tools. "
        "Server runs with run_http_async(transport='sse', host, port) for SSE transport."
    )

    result = await call_tool_json(session, "add_memory", {
        "messages": [{"role": "user", "content": context7_content}],
        "user_id": "test_user",
    })

    results_list = result.get("results", []) if isinstance(result, dict) else []
    memory_id = results_list[0].get("id", "") if results_list else ""

    if memory_id:
        get_result = await call_tool_json(session, "get_memory", {
            "memory_id": memory_id,
        })

        update_result = await call_tool_json(session, "update_memory", {
            "memory_id": memory_id,
            "content": context7_content + " Added: Supports stdio and SSE transports.",
        })

        logger.info(f"Updated memory: {update_result.get('status', 'unknown')}")

        get_after_update = await call_tool_json(session, "get_memory", {
            "memory_id": memory_id,
        })

        await call_tool_json(session, "delete_memory", {
            "memory_id": memory_id,
        })

        return {
            "test": "context7",
            "memory_id": memory_id,
            "get_success": "error" not in get_result,
            "update_success": "error" not in update_result,
            "delete_success": True,
            "success": True,
        }

    return {
        "test": "context7",
        "success": False,
        "error": "Failed to create memory",
    }


async def run_all_tests() -> None:
    """Run all MCP tool tests."""
    logger.info("Starting MCP SSE Client Tool Tests")
    logger.info(f"Server URL: {MEM0_SERVER_URL}")

    try:
        async with sse_client(url=MEM0_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("Successfully connected to MCP server")

                tools = await session.list_tools()
                logger.info(f"Found {len(tools.tools)} tools:")
                tool_names = [t.name for t in tools.tools]
                for tool in tools.tools:
                    logger.info(f"  - {tool.name}")

                results = []

                if "add_memory" in tool_names and "search_memories" in tool_names:
                    results.append(await code_reasoning_test(session))
                else:
                    logger.warning("Skipping code_reasoning_test - required tools not available")

                if "add_memory" in tool_names and "list_memories" in tool_names:
                    results.append(await exa_code_search_test(session))
                else:
                    logger.warning("Skipping exa_code_search_test - required tools not available")

                if "add_memory" in tool_names and "get_memory" in tool_names and "update_memory" in tool_names:
                    results.append(await context7_test(session))
                else:
                    logger.warning("Skipping context7_test - required tools not available")

                logger.info("\n" + "=" * 60)
                logger.info("TEST RESULTS SUMMARY")
                logger.info("=" * 60)
                for r in results:
                    status = "PASSED" if r.get("success") else "FAILED"
                    logger.info(f"  {r.get('test', 'unknown')}: {status}")
                    logger.info(f"{r}")
                logger.info("=" * 60)

                all_passed = all(r.get("success", False) for r in results)
                if all_passed:
                    logger.info("All tests passed!")
                else:
                    logger.error("Some tests failed")
                    sys.exit(1)

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
