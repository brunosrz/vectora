-- Migration 0004: segredos cifrados por usuário (SQLite)

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
