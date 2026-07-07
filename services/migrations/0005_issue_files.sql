-- Anexos de issue (prints e vídeos curtos): JSON array das keys R2
-- publicadas em issues/<issue_id>/<uuid>-<nome>. NULL = sem anexos.
ALTER TABLE issues ADD COLUMN files TEXT;
