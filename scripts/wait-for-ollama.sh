#!/bin/bash

OLLAMA_EMBEDDER_URL="${OLLAMA_EMBEDDER_URL:-http://ollama-qwen3-embedding:11434}"
OLLAMA_LLM_URL="${OLLAMA_LLM_URL:-http://ollama-qwen:11434}"
CONFIG_PATH="${CONFIG_PATH:-/app/config/settings.json}"
MAX_RETRIES=60
RETRY_INTERVAL=10

echo "Waiting for Ollama embedder (qwen3-embedding:8b) to be ready at $OLLAMA_EMBEDDER_URL..."

for i in $(seq 1 $MAX_RETRIES); do
    if python -c "import urllib.request; urllib.request.urlopen('$OLLAMA_EMBEDDER_URL/api/tags')" 2>/dev/null; then
        echo "Ollama embedder is responding"
        break
    fi
    echo "Ollama embedder not responding, retry $i/$MAX_RETRIES..."
    sleep $RETRY_INTERVAL
done

echo "Waiting for Ollama LLM (qwen2.5:7b) to be ready at $OLLAMA_LLM_URL..."

for i in $(seq 1 $MAX_RETRIES); do
    if python -c "import urllib.request; urllib.request.urlopen('$OLLAMA_LLM_URL/api/tags')" 2>/dev/null; then
        echo "Ollama LLM is responding"
        break
    fi
    echo "Ollama LLM not responding, retry $i/$MAX_RETRIES..."
    sleep $RETRY_INTERVAL
done

echo "All Ollama instances ready, starting MCP server..."
exec python -m mcp_server.main --config-path "$CONFIG_PATH"