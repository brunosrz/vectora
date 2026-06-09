-- Extensões necessárias para o Vectora em modo complete.
-- Executado automaticamente pelo PostgreSQL na criação do banco.

CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector: similaridade semântica
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- busca textual fuzzy
CREATE EXTENSION IF NOT EXISTS btree_gin;    -- índices compostos eficientes
