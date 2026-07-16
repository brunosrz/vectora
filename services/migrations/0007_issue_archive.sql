-- Arquivar issue (soft-delete): NULL = ativa, visível nas listagens públicas
-- e de admin. Arquivada some das duas listagens por padrão mas continua
-- acessível via GET /admin/issues/:id (admin pode desarquivar).
ALTER TABLE issues ADD COLUMN archived_at TEXT;
