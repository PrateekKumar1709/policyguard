# PolicyGuard MCP Server
# Multi-stage build for production deployment

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir fastmcp pydantic pyyaml python-dotenv

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY src/ ./src/
COPY manifest.yaml .

# Create data directory
RUN mkdir -p /app/data

# Create non-root user
RUN useradd -m -u 1000 policyguard && \
    chown -R policyguard:policyguard /app
USER policyguard

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT_MODE=http
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose MCP port
EXPOSE 8000

# Run the server
ENTRYPOINT ["python", "src/main.py"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
