FROM python:3.11-slim
WORKDIR /app
# Install official SigNoz MCP server (Go binary)
RUN apt-get update && apt-get install -y wget && \
    wget -q https://github.com/SigNoz/signoz-mcp-server/releases/latest/download/signoz-mcp-server-linux-amd64 \
    -O /usr/local/bin/signoz-mcp-server && \
    chmod +x /usr/local/bin/signoz-mcp-server && \
    apt-get remove -y wget && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY . .
CMD ["python", "-m", "guard.webhook"]
