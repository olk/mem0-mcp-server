# =============================================================================
# Multi-stage Dockerfile for mem0-mcp-server
# =============================================================================
# FR-001: Multi-stage build targeting production as specified in
#         PRD.deployment_specifications.container_orchestration.dockerfile
# PLAN.deployment_implementation.dockerfile: multi_stage=true targeting production
#
# Stage 1: Build stage with Python 3.12 and uv for dependency installation
# Stage 2: Production stage with minimal packages, non-root user, and security
# =============================================================================

# Stage 1: Build stage
# TECH-1: Python 3.12 base for dependency installation
# TECH-6: uv package manager for fast dependency installation
FROM python:3.12-slim-bookworm AS build

# Install uv package manager
# TECH-6: uv provides 10-100x faster installs than pip with built-in auditing
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
# Use --no-dev for production builds as per security best practices
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Download spaCy model for NLP functionality (lemma, NER, etc.)
# NOTE: mem0ai[nlp] installs spaCy but not the model itself
RUN /app/.venv/bin/python -m spacy download en_core_web_sm

# Copy application source code
COPY src/ ./src/

# =============================================================================
# Stage 2: Test stage (includes dev dependencies)
# =============================================================================
FROM build AS test

# Install dev dependencies for testing (including pytest)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras

# Copy test files
COPY tests/ ./tests/

# =============================================================================
# Stage 3: Production stage
# =============================================================================
FROM python:3.12-slim-bookworm AS production

# Create non-root user for security
# IC-001: Non-root user required for container security best practices
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy installed packages from build stage
COPY --from=build /app/.venv /app/.venv

# Create nltk_data directory and download stopwords for redisvl search
# NOTE: NLTK data is runtime data, not a Python package dependency, so it cannot
# be specified in pyproject.toml. This downloads the stopwords corpus at build
# time so it's available when redisvl performs BM25 keyword search.
RUN mkdir -p /app/.venv/nltk_data && \
    /app/.venv/bin/python -c "import nltk; nltk.download('stopwords', download_dir='/app/.venv/nltk_data')"

# Copy application source
COPY --from=build /app/src ./src
COPY --from=build /app/pyproject.toml ./

# Set environment variables for the application
# Set Python to use virtualenv
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="/app/.venv/bin:$PATH"
# Add /app/src to PYTHONPATH so 'mcp_server' package can be found
ENV PYTHONPATH="/app/src"
# Python optimization for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# NLTK data path for redisvl search stopwords
ENV NLTK_DATA=/app/.venv/nltk_data

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port for SSE
# PRD.deployment_specifications: Port 8050 for SSE server
EXPOSE 8050

# Healthcheck using Python's built-in HTTP server or application's health endpoint
# Using wget to check if the service is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8050/health || exit 1

# Run the MCP server
# Default command - can be overridden at runtime
CMD ["/app/.venv/bin/python", "-m", "src.mcp_server.main"]

# =============================================================================
# Metadata labels
# =============================================================================
LABEL org.opencontainers.image.title="mem0-mcp-server"
LABEL org.opencontainers.image.description="Mem0 MCP server for AI memory management"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Mem0 Platform Team"
