# Vectora — Deploy

## Desenvolvimento local (infra apenas)

Sobe Redis, PostgreSQL+pgvector e Qdrant localmente enquanto o servidor
Python roda fora do Docker (`uv run vectora`):

```bash
docker compose -f deploy/compose.dev.yml up -d
```

Adicione ao `.env`:

```env
STORAGE_MODE=complete
REDIS_URL=redis://localhost:6379/0
POSTGRES_DSN=postgresql+asyncpg://vectora:vectora@localhost:5432/vectora
QDRANT_URL=http://localhost:6333
```

## Produção — stack completo

```bash
cp .env.example .env   # editar API keys e senhas
docker compose -f deploy/compose.complete.yml up -d
```

## Parar e limpar

```bash
# Apenas parar (volumes preservados)
docker compose -f deploy/compose.dev.yml down

# Parar e destruir dados
docker compose -f deploy/compose.dev.yml down -v
```

## Portas expostas (dev)

| Serviço     | Porta |
| ----------- | ----- |
| PostgreSQL  | 5432  |
| Redis       | 6379  |
| Qdrant REST | 6333  |
| Qdrant gRPC | 6334  |
