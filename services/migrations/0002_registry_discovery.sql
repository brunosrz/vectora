-- Discovery automático de MCP/Skills (services/src/registry/discovery.ts,
-- rodado pelo scheduled() do Worker). `catalog_source` distingue linhas
-- curadas manualmente (seed de 0001_schema.sql, sempre 'curated') das
-- descobertas automaticamente ('official' para o registry oficial de MCP,
-- 'github' para skills achadas via GitHub code search) — o upsert do
-- discovery nunca sobrescreve uma linha 'curated', mesmo que o id colida.
ALTER TABLE mcp_catalog ADD COLUMN icon_url TEXT;
ALTER TABLE mcp_catalog ADD COLUMN catalog_source TEXT NOT NULL DEFAULT 'curated';
ALTER TABLE skills_catalog ADD COLUMN catalog_source TEXT NOT NULL DEFAULT 'curated';
