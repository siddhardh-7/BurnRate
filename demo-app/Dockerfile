FROM python:3.11-slim
WORKDIR /app

# Build context is project root — gives access to packages/burnrate-otel
COPY packages/burnrate-otel /burnrate-otel
RUN pip install --no-cache-dir /burnrate-otel

COPY demo-app/pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY demo-app/src ./src

CMD ["python", "-m", "demo.app"]
