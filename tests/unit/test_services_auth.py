"""Testes unitários para vectora/services/auth.py (Bloco C — C1/C2).

Cobre:
- hash_password / verify_password
- create_access_token / decode_access_token
- signup: primeiro usuário vira root, segundo vira member, email duplicado
- signin: credenciais válidas e inválidas, audit log
- refresh_tokens: rotação, token revogado, token expirado
- signout: revoga refresh token
- get_user_by_id: encontrado e não encontrado
- change_password: senha atual errada, nova senha curta, revogação de refresh tokens
- env overrides: set / get / delete
- has_users: empty DB e após signup
"""

from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Cada teste usa um banco SQLite temporário isolado."""
    db_file = str(tmp_path / "test_auth.db")

    # Resetar estado global do módulo auth antes de cada teste
    import src.services.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_db_conn", None)
    monkeypatch.setattr(
        auth_mod, "_get_secret", lambda: "test-secret-key-for-unit-tests"
    )

    # Apontar _get_db para o banco temporário
    from pathlib import Path

    import aiosqlite

    original_get_db = auth_mod._get_db

    async def _patched_get_db():
        if auth_mod._db_conn is not None:
            return auth_mod._db_conn
        conn = await aiosqlite.connect(db_file)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await auth_mod._ensure_schema(conn)
        auth_mod._db_conn = conn
        return conn

    monkeypatch.setattr(auth_mod, "_get_db", _patched_get_db)
    yield
    # Fecha a conexão após o teste
    import asyncio

    async def _close():
        if auth_mod._db_conn is not None:
            await auth_mod._db_conn.close()
            auth_mod._db_conn = None

    asyncio.get_event_loop().run_until_complete(_close())


# ---------------------------------------------------------------------------
# Hash de senha
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        from src.services.auth import hash_password

        h = hash_password("senhasegura123")
        assert h != "senhasegura123"
        assert len(h) > 20

    def test_verify_correct_password(self):
        from src.services.auth import hash_password, verify_password

        h = hash_password("minhasenha456!")
        assert verify_password("minhasenha456!", h) is True

    def test_verify_wrong_password(self):
        from src.services.auth import hash_password, verify_password

        h = hash_password("correta123456")
        assert verify_password("errada123456", h) is False

    def test_two_hashes_of_same_password_differ(self):
        from src.services.auth import hash_password

        h1 = hash_password("mesmasenha123")
        h2 = hash_password("mesmasenha123")
        assert h1 != h2  # salt aleatório garante hashes distintos


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


class TestJWT:
    def test_create_and_decode_access_token(self):
        from src.services.auth import User, create_access_token, decode_access_token

        user = User(
            id="u-1",
            email="test@example.com",
            role="member",
            created_at="2024-01-01T00:00:00+00:00",
        )
        token = create_access_token(user)
        payload = decode_access_token(token)

        assert payload["sub"] == "u-1"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "member"

    def test_tampered_token_raises(self):
        from jose import JWTError

        from src.services.auth import User, create_access_token, decode_access_token

        user = User(
            id="u-1",
            email="x@x.com",
            role="viewer",
            created_at="2024-01-01T00:00:00+00:00",
        )
        token = create_access_token(user)
        tampered = token[:-4] + "XXXX"

        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_expired_token_raises(self):
        import time
        from datetime import UTC, datetime, timedelta

        from jose import JWTError, jwt

        # Emite token já expirado
        payload = {
            "sub": "u-x",
            "email": "x@x.com",
            "role": "member",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            payload, "test-secret-key-for-unit-tests", algorithm="HS256"
        )

        from src.services.auth import decode_access_token

        with pytest.raises(JWTError):
            decode_access_token(expired_token)


# ---------------------------------------------------------------------------
# has_users
# ---------------------------------------------------------------------------


class TestHasUsers:
    @pytest.mark.asyncio
    async def test_empty_db_has_no_users(self):
        from src.services.auth import has_users

        assert await has_users() is False

    @pytest.mark.asyncio
    async def test_after_signup_has_users(self):
        from src.services.auth import has_users, signup

        await signup("first@example.com", "senhasegura1234")
        assert await has_users() is True


# ---------------------------------------------------------------------------
# signup
# ---------------------------------------------------------------------------


class TestSignup:
    @pytest.mark.asyncio
    async def test_first_user_is_root(self):
        from src.services.auth import signup

        user, access_token, refresh_token = await signup(
            "root@example.com", "senharootok1234"
        )
        assert user.role == "root"
        assert user.email == "root@example.com"
        assert access_token
        assert refresh_token

    @pytest.mark.asyncio
    async def test_second_user_is_member(self):
        from src.services.auth import signup

        await signup("root@example.com", "senharootok1234")
        user, _, _ = await signup("member@example.com", "senhameter1234")
        assert user.role == "member"

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self):
        from src.services.auth import signup

        await signup("dup@example.com", "senha123456789")
        with pytest.raises(ValueError, match="E-mail já cadastrado"):
            await signup("dup@example.com", "outrasenha123")

    @pytest.mark.asyncio
    async def test_short_password_raises(self):
        from src.services.auth import signup

        with pytest.raises(ValueError, match="mínimo 12"):
            await signup("short@example.com", "curta")

    @pytest.mark.asyncio
    async def test_email_stored_lowercase(self):
        from src.services.auth import signup

        user, _, _ = await signup("Upper@Example.COM", "senhasegura1234")
        assert user.email == "upper@example.com"


# ---------------------------------------------------------------------------
# signin
# ---------------------------------------------------------------------------


class TestSignin:
    @pytest.mark.asyncio
    async def test_valid_credentials(self):
        from src.services.auth import signin, signup

        await signup("user@example.com", "senhasegura1234")
        user, access_token, refresh_token = await signin(
            "user@example.com", "senhasegura1234"
        )
        assert user.email == "user@example.com"
        assert access_token
        assert refresh_token

    @pytest.mark.asyncio
    async def test_wrong_password_raises(self):
        from src.services.auth import signin, signup

        await signup("user2@example.com", "senhasegura1234")
        with pytest.raises(ValueError, match="Credenciais inválidas"):
            await signin("user2@example.com", "senhaerrada1234")

    @pytest.mark.asyncio
    async def test_unknown_email_raises(self):
        from src.services.auth import signin

        with pytest.raises(ValueError, match="Credenciais inválidas"):
            await signin("ghost@example.com", "senhasegura1234")

    @pytest.mark.asyncio
    async def test_case_insensitive_email(self):
        from src.services.auth import signin, signup

        await signup("case@example.com", "senhasegura1234")
        user, _, _ = await signin("CASE@EXAMPLE.COM", "senhasegura1234")
        assert user.email == "case@example.com"

    @pytest.mark.asyncio
    async def test_signin_updates_last_login_at(self):
        from src.services.auth import signin, signup

        user_created, _, _ = await signup("login@example.com", "senhasegura1234")
        assert user_created.last_login_at is None
        user_signed, _, _ = await signin("login@example.com", "senhasegura1234")
        assert user_signed.last_login_at is not None


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    @pytest.mark.asyncio
    async def test_refresh_issues_new_pair(self):
        from src.services.auth import decode_access_token, refresh_tokens, signup

        _, _old_access, old_refresh = await signup(
            "refresh@example.com", "senhasegura1234"
        )
        user, new_access, new_refresh = await refresh_tokens(old_refresh)

        assert user.email == "refresh@example.com"
        # Novo refresh token sempre difere (aleatoriedade)
        assert new_refresh != old_refresh
        # Novo access token é JWT válido para o mesmo usuário
        payload = decode_access_token(new_access)
        assert payload["email"] == "refresh@example.com"

    @pytest.mark.asyncio
    async def test_old_refresh_token_revoked_after_rotation(self):
        from src.services.auth import refresh_tokens, signup

        _, _, refresh = await signup("rot@example.com", "senhasegura1234")
        await refresh_tokens(refresh)

        with pytest.raises(ValueError, match="revogado"):
            await refresh_tokens(refresh)

    @pytest.mark.asyncio
    async def test_invalid_refresh_token_raises(self):
        from src.services.auth import refresh_tokens

        with pytest.raises(ValueError, match="inválido"):
            await refresh_tokens("token-invalido-qualquer")

    @pytest.mark.asyncio
    async def test_expired_refresh_token_raises(self):
        import hashlib
        from datetime import UTC, datetime, timedelta

        from src.services.auth import _get_db, refresh_tokens, signup

        _, _, refresh = await signup("exp@example.com", "senhasegura1234")
        token_hash = hashlib.sha256(refresh.encode()).hexdigest()

        # Força expiração do token
        db = await _get_db()
        past = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        await db.execute(
            "UPDATE refresh_tokens SET expires_at = ? WHERE token_hash = ?",
            (past, token_hash),
        )
        await db.commit()

        with pytest.raises(ValueError, match="expirado"):
            await refresh_tokens(refresh)


# ---------------------------------------------------------------------------
# signout
# ---------------------------------------------------------------------------


class TestSignout:
    @pytest.mark.asyncio
    async def test_signout_revokes_refresh_token(self):
        from src.services.auth import refresh_tokens, signout, signup

        _, _, refresh = await signup("out@example.com", "senhasegura1234")
        await signout(refresh)

        with pytest.raises(ValueError, match="revogado"):
            await refresh_tokens(refresh)

    @pytest.mark.asyncio
    async def test_signout_with_invalid_token_does_not_raise(self):
        from src.services.auth import signout

        # Signout com token inexistente não deve levantar exceção
        await signout("token-invalido-nao-deve-explodir")


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------


class TestGetUserById:
    @pytest.mark.asyncio
    async def test_returns_user(self):
        from src.services.auth import get_user_by_id, signup

        created, _, _ = await signup("find@example.com", "senhasegura1234")
        found = await get_user_by_id(created.id)
        assert found is not None
        assert found.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(self):
        from src.services.auth import get_user_by_id

        result = await get_user_by_id("id-que-nao-existe")
        assert result is None


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_changes_password_successfully(self):
        from src.services.auth import change_password, signin, signup

        user, _, _ = await signup("chpwd@example.com", "senhaantiga1234")
        await change_password(user.id, "senhaantiga1234", "senhanova5678!")

        # Nova senha funciona
        u2, _, _ = await signin("chpwd@example.com", "senhanova5678!")
        assert u2.email == "chpwd@example.com"

    @pytest.mark.asyncio
    async def test_wrong_old_password_raises(self):
        from src.services.auth import change_password, signup

        user, _, _ = await signup("chpwd2@example.com", "senhaantiga1234")
        with pytest.raises(ValueError, match="Senha atual incorreta"):
            await change_password(user.id, "senhaerrada1234", "senhanova5678!")

    @pytest.mark.asyncio
    async def test_short_new_password_raises(self):
        from src.services.auth import change_password, signup

        user, _, _ = await signup("chpwd3@example.com", "senhaantiga1234")
        with pytest.raises(ValueError, match="mínimo 12"):
            await change_password(user.id, "senhaantiga1234", "curta")

    @pytest.mark.asyncio
    async def test_change_password_revokes_existing_refresh_tokens(self):
        from src.services.auth import change_password, refresh_tokens, signup

        user, _, refresh = await signup("chpwd4@example.com", "senhaantiga1234")
        await change_password(user.id, "senhaantiga1234", "senhanova5678!")

        with pytest.raises(ValueError, match="revogado"):
            await refresh_tokens(refresh)


# ---------------------------------------------------------------------------
# Env overrides
# ---------------------------------------------------------------------------


class TestEnvOverrides:
    @pytest.mark.asyncio
    async def test_set_and_get_override(self):
        from src.services.auth import get_env_overrides, set_env_override, signup

        user, _, _ = await signup("env@example.com", "senhasegura1234")
        await set_env_override(user.id, "GITHUB_TOKEN", "ghp_test123")

        overrides = await get_env_overrides(user.id)
        assert overrides["GITHUB_TOKEN"] == "ghp_test123"  # noqa: S105

    @pytest.mark.asyncio
    async def test_delete_override(self):
        from src.services.auth import (
            delete_env_override,
            get_env_overrides,
            set_env_override,
            signup,
        )

        user, _, _ = await signup("env2@example.com", "senhasegura1234")
        await set_env_override(user.id, "MY_KEY", "my_value")
        await delete_env_override(user.id, "MY_KEY")

        overrides = await get_env_overrides(user.id)
        assert "MY_KEY" not in overrides

    @pytest.mark.asyncio
    async def test_override_does_not_affect_other_users(self):
        from src.services.auth import get_env_overrides, set_env_override, signup

        user1, _, _ = await signup("u1@example.com", "senhasegura1234")
        user2, _, _ = await signup("u2@example.com", "senhasegura5678")
        await set_env_override(user1.id, "PRIVATE_KEY", "value1")

        overrides2 = await get_env_overrides(user2.id)
        assert "PRIVATE_KEY" not in overrides2

    @pytest.mark.asyncio
    async def test_empty_overrides_for_new_user(self):
        from src.services.auth import get_env_overrides, signup

        user, _, _ = await signup("empty@example.com", "senhasegura1234")
        overrides = await get_env_overrides(user.id)
        assert overrides == {}


# ---------------------------------------------------------------------------
# Convites de signup (Q8)
# ---------------------------------------------------------------------------


class TestInvites:
    @pytest.mark.asyncio
    async def test_create_and_validate_invite(self):
        from src.services.auth import create_invite, signup, validate_invite

        root, _, _ = await signup("root@example.com", "senharootok1234")
        token, expires_at = await create_invite(root.id, role="member")
        assert token
        assert expires_at

        info = await validate_invite(token)
        assert info is not None
        assert info["role"] == "member"

    @pytest.mark.asyncio
    async def test_signup_with_invite_uses_invite_role(self):
        from src.services.auth import create_invite, signup, validate_invite

        root, _, _ = await signup("root@example.com", "senharootok1234")
        token, _ = await create_invite(root.id, role="admin")
        info = await validate_invite(token)
        assert info is not None

        user, _, _ = await signup(
            "invited@example.com", "senhasegura1234", role=info["role"]
        )
        assert user.role == "admin"

    @pytest.mark.asyncio
    async def test_consume_invalidates_invite(self):
        from src.services.auth import (
            consume_invite,
            create_invite,
            signup,
            validate_invite,
        )

        root, _, _ = await signup("root@example.com", "senharootok1234")
        token, _ = await create_invite(root.id, role="member")
        user, _, _ = await signup("m@example.com", "senhasegura1234", role="member")

        await consume_invite(token, user.id)
        assert await validate_invite(token) is None

    @pytest.mark.asyncio
    async def test_unknown_token_is_invalid(self):
        from src.services.auth import validate_invite

        assert await validate_invite("token-inexistente") is None

    @pytest.mark.asyncio
    async def test_expired_invite_is_invalid(self):
        from datetime import UTC, datetime, timedelta

        from src.services.auth import (
            _get_db,
            _hash_token,
            create_invite,
            signup,
            validate_invite,
        )

        root, _, _ = await signup("root@example.com", "senharootok1234")
        token, _ = await create_invite(root.id, role="member")

        db = await _get_db()
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        await db.execute(
            "UPDATE invites SET expires_at = ? WHERE token_hash = ?",
            (past, _hash_token(token)),
        )
        await db.commit()

        assert await validate_invite(token) is None

    @pytest.mark.asyncio
    async def test_list_and_revoke_invite(self):
        from src.services.auth import (
            create_invite,
            list_invites,
            revoke_invite,
            signup,
        )

        root, _, _ = await signup("root@example.com", "senharootok1234")
        await create_invite(root.id, role="viewer")

        invites = await list_invites()
        assert len(invites) == 1
        token_hash = invites[0]["token_hash"]

        assert await revoke_invite(token_hash) is True
        assert await list_invites() == []

    @pytest.mark.asyncio
    async def test_first_user_ignores_invite_role(self):
        from src.services.auth import signup

        # Sem usuários ainda: a role do convite é ignorada, o 1º vira root
        user, _, _ = await signup("first@example.com", "senhasegura1234", role="viewer")
        assert user.role == "root"
