"""Serviço de autenticação e identidade do Vectora.

Responsável por:
- Definição dos modelos de identidade (User, Role, Credentials)
- Gerenciamento de tabelas SQLite (users, refresh_tokens)
- Hash seguro de senhas com Argon2id (argon2-cffi)
- Geração e validação de JWT (python-jose, HS256)
- Ciclo de vida dos tokens: access (15min) + refresh (7d, opaque, rotacionado)

Banco de dados: ~/.vectora/checkpoints.db (mesmo que checkpointer LangGraph)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes configuráveis via env
# ---------------------------------------------------------------------------

_SECRET_KEY_PATH = Path.home() / ".vectora" / "auth.key"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("VECTORA_ACCESS_TOKEN_MINUTES", "15"))
_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("VECTORA_REFRESH_TOKEN_DAYS", "7"))
_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

Role = Literal["root", "admin", "member", "viewer"]


class User(BaseModel):
    """Usuário autenticado — saída segura (sem password_hash)."""

    id: str
    email: str
    role: Role
    env_overrides: dict[str, str] = Field(default_factory=dict)
    created_at: str
    last_login_at: str | None = None


class UserInDB(User):
    """Usuário com hash de senha — uso interno apenas."""

    password_hash: str
    env_overrides_json: str = "{}"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: User


class Credentials(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Gerenciamento da chave secreta JWT
# ---------------------------------------------------------------------------


def _load_or_create_secret_key() -> str:
    """Carrega (ou cria) a chave secreta para assinatura JWT.

    O arquivo tem permissões 600 no Unix. No Windows, apenas o criador tem
    acesso por padrão (sem chmod explícito — NTFS herda da pasta pai).
    """
    _SECRET_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _SECRET_KEY_PATH.exists():
        return _SECRET_KEY_PATH.read_text().strip()
    key = secrets.token_hex(64)  # 512 bits
    _SECRET_KEY_PATH.write_text(key)
    try:
        _SECRET_KEY_PATH.chmod(0o600)
    except (AttributeError, NotImplementedError):
        pass  # Windows — sem suporte a chmod
    logger.info("auth: nova chave JWT gerada em %s", _SECRET_KEY_PATH)
    return key


_SECRET_KEY: str | None = None


def _get_secret() -> str:
    global _SECRET_KEY
    if _SECRET_KEY is None:
        _SECRET_KEY = _load_or_create_secret_key()
    return _SECRET_KEY


# ---------------------------------------------------------------------------
# Hashing de senha (Argon2id via argon2-cffi)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Retorna um hash Argon2id seguro para a senha fornecida."""
    from argon2 import PasswordHasher

    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,  # 64 MiB
        parallelism=2,
        hash_len=32,
        salt_len=16,
    )
    return ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha. Retorna True se válida; nunca lança exceção para o caller."""
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    ph = PasswordHasher()
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Exception as exc:
        logger.warning("auth: verify_password erro inesperado: %s", exc)
        return False


# ---------------------------------------------------------------------------
# JWT — access token
# ---------------------------------------------------------------------------


def create_access_token(user: User) -> str:
    """Emite um JWT de acesso com vida útil de ACCESS_TOKEN_EXPIRE_MINUTES."""
    from jose import jwt

    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida e decodifica JWT. Lança JWTError/ExpiredSignatureError em falha."""
    from jose import jwt

    return jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])


# ---------------------------------------------------------------------------
# Refresh token — opaque, hash armazenado no DB
# ---------------------------------------------------------------------------


def _hash_refresh_token(token: str) -> str:
    """SHA-256 do token opaco — armazenado no banco."""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_refresh_token() -> str:
    """Token opaco de 64 bytes hex (512 bits de entropia)."""
    return secrets.token_hex(64)


# ---------------------------------------------------------------------------
# Conexão ao banco
# ---------------------------------------------------------------------------

_db_conn: Any = None


async def _get_db() -> Any:
    """Retorna conexão aiosqlite compartilhada com os schemas de auth."""
    global _db_conn
    if _db_conn is not None:
        return _db_conn

    import aiosqlite

    db_path = Path.home() / ".vectora" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _db_conn = await aiosqlite.connect(str(db_path))
    _db_conn.row_factory = aiosqlite.Row
    await _db_conn.execute("PRAGMA journal_mode=WAL")
    await _ensure_schema(_db_conn)
    return _db_conn


async def _ensure_schema(db: Any) -> None:
    """Cria tabelas de auth se não existirem."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id                 TEXT PRIMARY KEY,
            email              TEXT NOT NULL UNIQUE,
            password_hash      TEXT NOT NULL,
            role               TEXT NOT NULL DEFAULT 'member',
            env_overrides_json TEXT NOT NULL DEFAULT '{}',
            created_at         TEXT NOT NULL,
            last_login_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_hash  TEXT    PRIMARY KEY,
            user_id     TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at  TEXT    NOT NULL,
            revoked     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit (
            id            TEXT    PRIMARY KEY,
            user_id       TEXT,
            action        TEXT    NOT NULL,
            target_type   TEXT,
            target_id     TEXT,
            timestamp     TEXT    NOT NULL,
            ip            TEXT,
            user_agent    TEXT,
            success       INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT    NOT NULL DEFAULT '{}'
        );
    """)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers internos de banco
# ---------------------------------------------------------------------------


def _row_to_user(row: Any) -> UserInDB:
    import json

    env = {}
    try:
        env = json.loads(row["env_overrides_json"] or "{}")
    except Exception:
        pass
    return UserInDB(
        id=row["id"],
        email=row["email"],
        role=row["role"],
        env_overrides=env,
        env_overrides_json=row["env_overrides_json"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        last_login_at=row["last_login_at"],
    )


async def _count_users(db: Any) -> int:
    async with db.execute("SELECT COUNT(*) FROM users") as cur:
        row = await cur.fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# API pública do serviço
# ---------------------------------------------------------------------------


async def has_users() -> bool:
    """True se já existe pelo menos um usuário cadastrado."""
    db = await _get_db()
    return await _count_users(db) > 0


async def signup(email: str, password: str) -> tuple[User, str, str]:
    """Cria um novo usuário.

    O primeiro usuário vira root automaticamente. Os demais viram member.

    Returns:
        (user, access_token, refresh_token)

    Raises:
        ValueError: email já cadastrado ou validação falhou
    """
    if len(password) < 12:
        raise ValueError("Senha deve ter no mínimo 12 caracteres.")

    db = await _get_db()
    count = await _count_users(db)
    role: Role = "root" if count == 0 else "member"

    now = datetime.now(UTC).isoformat()
    user_id = str(uuid.uuid4())
    ph = hash_password(password)

    try:
        await db.execute(
            "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email.lower().strip(), ph, role, now),
        )
        await db.commit()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ValueError("E-mail já cadastrado.") from exc
        raise

    user = User(id=user_id, email=email.lower().strip(), role=role, created_at=now)
    access_token = create_access_token(user)
    refresh_token = await _issue_refresh_token(db, user_id)

    await _write_audit(db, user_id, "signup", success=True)
    logger.info("auth: novo usuário criado id=%s role=%s", user_id, role)
    return user, access_token, refresh_token


async def signin(email: str, password: str, *, ip: str = "") -> tuple[User, str, str]:
    """Autentica usuário com email + senha.

    Returns:
        (user, access_token, refresh_token)

    Raises:
        ValueError: credenciais inválidas
    """
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ) as cur:
        row = await cur.fetchone()

    if row is None or not verify_password(password, row["password_hash"]):
        await _write_audit(
            db,
            None,
            "signin_failed",
            success=False,
            metadata={"email": email, "ip": ip},
        )
        raise ValueError("Credenciais inválidas.")

    user_in_db = _row_to_user(row)
    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?", (now, user_in_db.id)
    )
    await db.commit()

    user = User(
        id=user_in_db.id,
        email=user_in_db.email,
        role=user_in_db.role,
        env_overrides=user_in_db.env_overrides,
        created_at=user_in_db.created_at,
        last_login_at=now,
    )
    access_token = create_access_token(user)
    refresh_token = await _issue_refresh_token(db, user.id)

    await _write_audit(db, user.id, "signin", success=True, metadata={"ip": ip})
    return user, access_token, refresh_token


async def refresh_tokens(refresh_token: str) -> tuple[User, str, str]:
    """Valida refresh token, emite novo par de tokens (rotação).

    O token antigo é revogado imediatamente.

    Raises:
        ValueError: token inválido, expirado ou revogado
    """
    db = await _get_db()
    token_hash = _hash_refresh_token(refresh_token)
    now_str = datetime.now(UTC).isoformat()

    async with db.execute(
        "SELECT * FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        raise ValueError("Refresh token inválido.")
    if row["revoked"]:
        raise ValueError("Refresh token já foi revogado.")
    if row["expires_at"] < now_str:
        raise ValueError("Refresh token expirado.")

    # Revoga o token atual
    await db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
    )

    # Carrega usuário
    async with db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)) as cur:
        user_row = await cur.fetchone()
    if user_row is None:
        raise ValueError("Usuário não encontrado.")

    user_in_db = _row_to_user(user_row)
    user = User(
        id=user_in_db.id,
        email=user_in_db.email,
        role=user_in_db.role,
        env_overrides=user_in_db.env_overrides,
        created_at=user_in_db.created_at,
        last_login_at=user_in_db.last_login_at,
    )
    access_token = create_access_token(user)
    new_refresh = await _issue_refresh_token(db, user.id)

    await _write_audit(db, user.id, "refresh_token_rotation", success=True)
    return user, access_token, new_refresh


async def signout(refresh_token: str) -> None:
    """Revoga refresh token (logout)."""
    db = await _get_db()
    token_hash = _hash_refresh_token(refresh_token)
    await db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
    )
    await db.commit()
    await _write_audit(db, None, "signout", success=True)


async def get_user_by_id(user_id: str) -> User | None:
    """Retorna User pelo ID, ou None se não existir."""
    db = await _get_db()
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    u = _row_to_user(row)
    return User(
        id=u.id,
        email=u.email,
        role=u.role,
        env_overrides=u.env_overrides,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


async def change_password(user_id: str, old_password: str, new_password: str) -> None:
    """Muda senha do usuário após validar a senha atual.

    Raises:
        ValueError: senha atual incorreta ou nova senha inválida
    """
    if len(new_password) < 12:
        raise ValueError("Nova senha deve ter no mínimo 12 caracteres.")

    db = await _get_db()
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    if row is None:
        raise ValueError("Usuário não encontrado.")
    if not verify_password(old_password, row["password_hash"]):
        raise ValueError("Senha atual incorreta.")

    new_hash = hash_password(new_password)
    await db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id)
    )
    # Revoga todos os refresh tokens existentes ao trocar senha
    await db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,)
    )
    await db.commit()
    await _write_audit(db, user_id, "change_password", success=True)


# ---------------------------------------------------------------------------
# Env overrides por usuário (C10)
# ---------------------------------------------------------------------------


async def get_env_overrides(user_id: str) -> dict[str, str]:
    """Retorna os env overrides do usuário."""
    import json

    db = await _get_db()
    async with db.execute(
        "SELECT env_overrides_json FROM users WHERE id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return {}
    try:
        return json.loads(row[0] or "{}")
    except Exception:
        return {}


async def set_env_override(user_id: str, key: str, value: str) -> None:
    """Define (ou sobrescreve) um env override para o usuário."""
    import json

    overrides = await get_env_overrides(user_id)
    overrides[key] = value
    db = await _get_db()
    await db.execute(
        "UPDATE users SET env_overrides_json = ? WHERE id = ?",
        (json.dumps(overrides), user_id),
    )
    await db.commit()


async def delete_env_override(user_id: str, key: str) -> None:
    """Remove um env override do usuário."""
    import json

    overrides = await get_env_overrides(user_id)
    overrides.pop(key, None)
    db = await _get_db()
    await db.execute(
        "UPDATE users SET env_overrides_json = ? WHERE id = ?",
        (json.dumps(overrides), user_id),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


async def _issue_refresh_token(db: Any, user_id: str) -> str:
    """Gera, persiste e retorna um novo refresh token opaco."""
    token = _generate_refresh_token()
    token_hash = _hash_refresh_token(token)
    now = datetime.now(UTC)
    expires_at = (now + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    await db.execute(
        "INSERT INTO refresh_tokens (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (token_hash, user_id, expires_at, now.isoformat()),
    )
    await db.commit()
    return token


async def _write_audit(
    db: Any,
    user_id: str | None,
    action: str,
    *,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip: str = "",
) -> None:
    """Registra evento no audit log (best-effort — nunca propaga exceção)."""
    import json

    try:
        await db.execute(
            """INSERT INTO audit (id, user_id, action, target_type, target_id,
               timestamp, ip, success, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user_id,
                action,
                target_type,
                target_id,
                datetime.now(UTC).isoformat(),
                ip,
                1 if success else 0,
                json.dumps(metadata or {}),
            ),
        )
        await db.commit()
    except Exception as exc:
        logger.warning("auth: falha ao escrever audit log: %s", exc)


# Exportamos write_audit para uso externo (handlers, middleware)
write_audit = _write_audit


async def get_db_for_audit() -> Any:
    """Expõe conexão para handlers externos escreverem audit entries."""
    return await _get_db()
