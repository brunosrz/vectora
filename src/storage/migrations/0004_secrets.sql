-- Migration 0004: tabela de segredos cifrados por usuário
-- Extrai CREATE TABLE de src/services/secrets/internal.py

-- up
CREATE TABLE IF NOT EXISTS secrets (
    user_id    TEXT NOT NULL,
    key        TEXT NOT NULL,
    ciphertext BLOB NOT NULL,
    nonce      BLOB NOT NULL,
    PRIMARY KEY (user_id, key)
);

-- down
DROP TABLE IF EXISTS secrets;
