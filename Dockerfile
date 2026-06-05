# ── Stage 0: Build Vite SPA ────────────────────────────────────────────────
FROM node:22-alpine AS chat-builder

WORKDIR /build/chat

RUN corepack enable && corepack prepare pnpm@11.5.0 --activate

COPY chat/package.json chat/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY chat/ ./
RUN pnpm build

# ── Stage 1: Python builder ─────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ARG VERSION=0.1.0

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen --no-dev

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim

ARG VERSION=0.1.0

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src   /app/src
COPY --from=builder /build/pyproject.toml /app/pyproject.toml
COPY --from=chat-builder /build/chat/dist /app/chat/dist

RUN mkdir -p /root/.vectora && chmod 700 /root/.vectora

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    VERSION=${VERSION}

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["vectora", "server", "web"]
