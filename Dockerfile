# Stage 1: Builder — instala dependências e monta o venv completo
FROM python:3.14-slim AS builder

ARG VERSION=0.1.0

WORKDIR /build

# curl só é necessário aqui para instalar uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (apenas no builder)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copiar projeto e construir venv isolado
COPY . .
RUN uv sync --frozen --no-dev

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — imagem mínima, sem uv, sem curl, sem build tools
FROM python:3.14-slim

ARG VERSION=0.1.0

WORKDIR /app

# Copiar venv pronto do builder (sem reinstalar nada)
COPY --from=builder /build/.venv /app/.venv

# Copiar apenas o que o runtime precisa
COPY --from=builder /build/vectora    /app/vectora
COPY --from=builder /build/pyproject.toml /app/pyproject.toml
COPY --from=builder /build/README.md  /app/README.md

# Diretório de dados persistentes (LanceDB, SQLite, config)
RUN mkdir -p /root/.vectora && chmod 777 /root/.vectora

# PATH aponta para o venv — sem uv, sem PYTHONPATH tricks
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    VERSION=${VERSION}

# Health check — verifica que o pacote importa corretamente
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import vectora; import sys; sys.exit(0)" || exit 1

# Chama o entrypoint diretamente do venv (sem overhead do `uv run`)
ENTRYPOINT ["vectora-mcp"]
