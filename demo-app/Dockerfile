FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
# Install burnrate-otel from the monorepo (or PyPI once published)
COPY ../packages/burnrate-otel /burnrate-otel
RUN pip install --no-cache-dir /burnrate-otel && pip install --no-cache-dir -e .
COPY . .
CMD ["python", "-m", "demo.app"]
