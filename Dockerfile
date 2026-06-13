# syntax=docker/dockerfile:1
# ── Stage 0: Build Vite SPA ────────────────────────────────────────────────
FROM node:24-alpine AS chat-builder

WORKDIR /build/chat

RUN corepack enable && corepack prepare pnpm@11.5.0 --activate

# pnpm-workspace.yaml carrega as settings do pnpm (onlyBuiltDependencies /
# ignoredBuiltDependencies). SEM ele, o `pnpm install` aborta com
# ERR_PNPM_IGNORED_BUILDS: sharp@x no container — por isso ele PRECISA ser
# copiado junto do package.json/lockfile, antes do install.
COPY chat/package.json chat/pnpm-lock.yaml chat/pnpm-workspace.yaml ./
# Cache mount do store do pnpm + fetch-timeout/retries altos: o build deixa de
# falhar por timeout de download em rede lenta e retries reaproveitam o store.
RUN --mount=type=cache,target=/pnpm-store \
    pnpm install --frozen-lockfile --store-dir /pnpm-store \
    --fetch-timeout=600000 --fetch-retries=5

COPY chat/ ./
RUN pnpm build

# ── Stage 1: Python builder ─────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ARG VERSION=0.1.0

# IMPORTANTE: o WORKDIR do builder DEVE ser igual ao do runtime (/app). O uv
# instala o projeto em modo editable — o arquivo `_editable_impl_*.pth` grava o
# caminho ABSOLUTO da raiz (ex.: /app) em sys.path, e os console scripts do venv
# (ex.: `vectora`) recebem um shebang com o caminho ABSOLUTO do python do venv.
# Se o builder usasse /build e o runtime /app, o .pth apontaria para /build
# (inexistente no runtime → `import src` falha) e o shebang para
# /build/.venv/bin/python (inexistente → o entrypoint não executa).
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim

ARG VERSION=0.1.0

WORKDIR /app

# GitPython (src/tools/git.py) exige o binário `git` no PATH em runtime — sem ele
# o backend crasha no import ("Bad git executable"). O python:slim não traz git.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src   /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
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
