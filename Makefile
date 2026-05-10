# Makefile for MCP server
# FR-001: Build automation with uv integration
# IC-001: All targets use uv for consistent environment

# Variables
# MVAR-1: Python version for the project
PYTHON_VERSION := 3.12
# MVAR-2: Docker image name
DOCKER_IMAGE := mem0-mcp-server
# MVAR-3: Docker image tag
DOCKER_TAG := latest

.PHONY: help install lint typecheck test test-unit test-integration test-all test-coverage lint-fix build run clean docker-test docker-build docker-up docker-down docker-logs docker-logs-follow

.DEFAULT_GOAL := help

##@ General

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## MAKE-2: Install dependencies using uv sync (including dev)
	uv sync --extra dev

lint: install ## MAKE-4: Run ruff check for linting
	uv run ruff check .

typecheck: install ## MAKE-5: Run pyright for type checking
	uv run pyright

test: test-all ## MAKE-3: Run all tests (unit + integration)

test-unit: install ## Run unit tests without Docker
	uv run pytest tests/transport/ -v --tb=short

test-integration: install ## Run integration tests (requires Docker stack)
	@echo "Starting Docker services..."
	docker compose up -d --wait ollama-qwen3-embedding
	docker compose up -d --wait ollama-qwen
	@echo "Waiting for Ollama to be healthy..."
	@timeout=60; \
	while ! docker compose exec -T ollama-qwen3-embedding ollama list 2>/dev/null | grep -q qwen3-embedding; do \
		echo "Waiting for Ollama models..."; \
		sleep 5; \
		timeout=$$((timeout - 1)); \
		if [ $$timeout -le 0 ]; then \
			echo "Timeout waiting for Ollama"; \
			exit 1; \
		fi; \
	done
	@echo "Ollama is healthy. Running integration tests..."
	uv run pytest tests/integration/ -v --tb=short -m integration
	@echo "Integration tests complete."

test-all: install ## Run unit and integration tests
	uv run pytest tests/ -v --tb=short -m "not integration"

test-coverage: install ## Run tests with coverage report
	uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint-fix: install ## Auto-fix linting issues
	uv run ruff check --fix .
	uv run ruff format .

##@ Docker

docker-test: ## MAKE-3a: Build test image and run pytest
	docker build --target test -t $(DOCKER_IMAGE):test .
	docker run --rm $(DOCKER_IMAGE):test bash -c 'cd /app && /usr/local/bin/uv run pytest'

docker-build: ## MAKE-3b: Build Docker test image with dev dependencies
	docker build --target production -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-up: ## MAKE-9: Start services with docker compose
	docker compose up -d --build

docker-down: ## MAKE-10: Stop services with docker compose
	docker compose down

docker-logs: ## MAKE-11: Show docker compose logs (one-time)
	docker compose logs

docker-logs-follow: ## MAKE-11a: Show and follow docker compose logs
	docker compose logs -f

run: install ## MAKE-7: Run development server
	uv run uvicorn src.mcp.main:app --reload --host 0.0.0.0 --port 8000

##@ Maintenance

clean: ## MAKE-8: Clean build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache .hypothesis
	rm -rf build dist *.egg-info .eggs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):test 2>/dev/null || true
