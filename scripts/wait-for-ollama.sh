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

echo "Checking installed models..."

check_and_pull_model() {
    local ollama_url=$1
    local model_name=$2
    local full_name="${model_name}"
    
    echo "Checking if model '$full_name' is available at $ollama_url..."
    
    installed=$(python -c "
import urllib.request
import json
try:
    resp = urllib.request.urlopen('$ollama_url/api/tags', timeout=10)
    data = json.loads(resp.read().decode())
    models = data.get('models', [])
    names = [m.get('name', '') for m in models]
    print([n for n in names if n.startswith('$model_name') or n == '$model_name' or n == '$full_name'][0] if any(n.startswith('$model_name') or n == '$model_name' or n == '$full_name' for n in names) else '')
except Exception as e:
    print('', end='')
" 2>/dev/null)
    
    if [ -n "$installed" ]; then
        echo "Model '$installed' already installed"
        return 0
    fi
    
    echo "Model '$full_name' not found, pulling..."
    result=$(python -c "
import urllib.request
import json
data = json.dumps({'model': '$full_name', 'stream': False}).encode()
req = urllib.request.Request('$ollama_url/api/pull', data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req, timeout=600)
    print('success' if resp.status == 200 else 'failed')
except Exception as e:
    print(f'error: {e}')
" 2>&1)
    
    if echo "$result" | grep -q "error"; then
        echo "Failed to pull model '$full_name': $result"
        return 1
    fi
    echo "Successfully pulled model '$full_name'"
    return 0
}

LLM_MODEL=$(python -c "import json; f=open('$CONFIG_PATH'); d=json.load(f); print(d.get('llm', {}).get('model', 'qwen2.5:7b'))" 2>/dev/null || echo "qwen2.5:7b")
EMBEDDER_MODEL=$(python -c "import json; f=open('$CONFIG_PATH'); d=json.load(f); print(d.get('embedder', {}).get('model', 'qwen3-embedding:8b'))" 2>/dev/null || echo "qwen3-embedding:8b")

echo "Required LLM model: $LLM_MODEL"
echo "Required embedder model: $EMBEDDER_MODEL"

echo "Ensuring LLM model is available at $OLLAMA_LLM_URL..."
check_and_pull_model "$OLLAMA_LLM_URL" "$LLM_MODEL"

echo "Ensuring embedder model is available at $OLLAMA_EMBEDDER_URL..."
check_and_pull_model "$OLLAMA_EMBEDDER_URL" "$EMBEDDER_MODEL"

echo "All Ollama instances ready, starting MCP server..."
exec python -m mcp_server.main --config-path "$CONFIG_PATH"