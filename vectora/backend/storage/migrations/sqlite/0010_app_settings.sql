-- Migration 0010: tabela key-value de configuração não-secreta do app
-- (provider/model ativo, storage_mode, auth_required, nome/empresa do
-- usuário local, prefs do frontend etc.) — espelha o schema que
-- RuntimeSettings cria idempotentemente em backend/workspace/runtime_settings.py,
-- no mesmo checkpoints.db de users/secrets.

-- up
CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- down
DROP TABLE IF EXISTS app_settings;
