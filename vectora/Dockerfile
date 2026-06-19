# syntax=docker/dockerfile:1
# ── Stage 0: Build Vite SPA ────────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /build/frontend

RUN corepack enable && corepack prepare pnpm@11.5.0 --activate

# pnpm-workspace.yaml carrega as settings do pnpm (onlyBuiltDependencies /
# ignoredBuiltDependencies). SEM ele, o `pnpm install` aborta com
# ERR_PNPM_IGNORED_BUILDS: sharp@x no container — por isso ele PRECISA ser
# copiado junto do package.json/lockfile, antes do install.
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# Cache mount do store do pnpm + fetch-timeout/retries altos: o build deixa de
# falhar por timeout de download em rede lenta e retries reaproveitam o store.
RUN --mount=type=cache,target=/pnpm-store \
    pnpm install --frozen-lockfile --store-dir /pnpm-store \
    --fetch-timeout=600000 --fetch-retries=5

COPY frontend/ ./
RUN pnpm build

# ── Stage 1: Nuitka builder (compila o backend para binário C) ──────────────
# Produto pago de código fechado: o runtime NÃO recebe nenhum `.py` do backend.
# Compilamos `backend/launcher.py` → binário onefile `vectora` (as diretivas
# `nuitka-project:` vivem no próprio launcher.py). A SPA Vite é embutida no
# binário como `chat_static/` via --include-data-dir.
FROM python:3.13-slim AS nuitka-builder

WORKDIR /app

# build-essential: compilador C que o Nuitka usa. patchelf: exigido pelo modo
# onefile no Linux (reescreve o RPATH do binário). ccache: acelera rebuilds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential patchelf ccache curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/ ./backend/
COPY README.md ./
# A SPA precisa existir em frontend/dist no momento da compilação — o Nuitka
# a embute no binário (--include-data-dir aponta para ../frontend/dist).
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Compila o binário onefile. As flags estão no launcher.py (nuitka-project:);
# --assume-yes-for-downloads evita prompt do gcc/ccache em ambiente não-tty.
RUN --mount=type=cache,target=/root/.cache/ccache \
    uv run python -m nuitka --assume-yes-for-downloads backend/launcher.py

# ── Stage 2: Runtime (só o binário compilado, sem fonte Python) ─────────────
FROM python:3.13-slim

ARG VERSION=0.1.0

WORKDIR /app

# GitPython (backend/tools/git.py) exige o binário `git` no PATH em runtime — sem
# ele o backend crasha no import ("Bad git executable"). O slim não traz git.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Apenas o binário compilado entra no runtime — nenhum `.py` do backend, nenhum
# venv, nenhuma fonte. A SPA Vite já está embutida no binário (chat_static).
COPY --from=nuitka-builder /app/dist-nuitka/vectora /usr/local/bin/vectora

RUN mkdir -p /root/.vectora && chmod 700 /root/.vectora

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    VERSION=${VERSION}

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Sem display no container → vectora start degrada para servidor puro
# (backend + MCP em /mcp + SPA), sem bandeja nem janela.
ENTRYPOINT ["vectora", "start"]
