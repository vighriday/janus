# JANUS API — FastAPI on uv. Build context is the repo root so the synthetic
# corpus under data/ is available to the in-process decision graph at runtime.
# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies first (cached layer) from the lockfile only.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=api/uv.lock,target=uv.lock \
    --mount=type=bind,source=api/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then the project source.
COPY api/ /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
RUN useradd -m -u 1000 app

# App code + venv from the builder, and the corpus the graph loads at startup.
# core.py resolves the corpus via parents[3]/data/corpus from
# janus/pipeline/core.py, so with the package at /app/api/janus the corpus must
# sit at /app/api/data/corpus.
COPY --from=builder --chown=app:app /app /app/api
COPY --chown=app:app data /app/api/data

ENV PATH="/app/api/.venv/bin:$PATH"
WORKDIR /app/api
USER app
EXPOSE 8000
CMD ["uvicorn", "janus.app:app", "--host", "0.0.0.0", "--port", "8000"]
