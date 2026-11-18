# syntax=docker/dockerfile:1
# Build context: repository root (the API imports the ingest package and data/ files).
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app/apps/api:/app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY ingest ./ingest
COPY db ./db
COPY apps/api/app ./apps/api/app
COPY data/institution.json data/uiuc_units.yaml data/keyword_stoplist.txt data/keyword_generic.txt ./data/
RUN useradd --system app && chown -R app /app
USER app
EXPOSE 8010
HEALTHCHECK --interval=10s --timeout=3s --retries=12 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=2)" || exit 1
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
