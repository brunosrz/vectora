"""Runner de schema migrations para SQLite.

Substitui o padrão ``CREATE TABLE IF NOT EXISTS … ALTER TABLE suppress(Exception)``
espalhado pelos services por um sistema declarativo e versionado.

Cada migration é um arquivo ``NNNN_<nome>.sql`` com seções ``-- up`` e ``-- down``
separando os comandos de upgrade e downgrade. O runner mantém a tabela interna
``schema_migrations`` com versão, timestamp e SHA-256 do conteúdo do arquivo para
detectar drift (arquivo modificado após aplicação).

Uso (código):
    runner = MigrationRunner(conn, migrations_dir)
    status = await runner.status()
    await runner.upgrade()           # aplica todas as pendentes
    await runner.downgrade("0002")   # reverte até (inclusive) a versão 0002

CLI:
    vectora storage migrate status
    vectora storage migrate upgrade
    vectora storage migrate downgrade 0002
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema interno de controle
# ---------------------------------------------------------------------------

_CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT    PRIMARY KEY,
    name       TEXT    NOT NULL,
    applied_at TEXT    NOT NULL,
    checksum   TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# MigrationFile — representação de um arquivo .sql
# ---------------------------------------------------------------------------


@dataclass
class MigrationFile:
    """Arquivo de migration parseado.

    Attributes:
        version:  String numérica extraída do nome (ex: ``"0001"``).
        name:     Nome descritivo após o número (ex: ``"auth"``).
        path:     Caminho absoluto do arquivo ``.sql``.
        up_sql:   Comandos SQL de upgrade (seção ``-- up``).
        down_sql: Comandos SQL de downgrade (seção ``-- down``).
        checksum: SHA-256 do conteúdo completo do arquivo.
    """

    version: str
    name: str
    path: Path
    up_sql: str
    down_sql: str
    checksum: str


@dataclass
class MigrationStatus:
    """Status de uma migration individual.

    Attributes:
        version:     Versão da migration.
        name:        Nome descritivo.
        applied:     True se já foi aplicada ao banco.
        applied_at:  ISO timestamp da aplicação (None se pendente).
        drift:       True se o arquivo foi modificado após a aplicação.
    """

    version: str
    name: str
    applied: bool
    applied_at: str | None
    drift: bool


# ---------------------------------------------------------------------------
# Parser de arquivos .sql
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^--\s*(up|down)\s*$", re.IGNORECASE | re.MULTILINE)


def _parse_sql_file(path: Path) -> MigrationFile:
    """Lê e parseia um arquivo `NNNN_name.sql`.

    O arquivo deve conter as seções ``-- up`` e ``-- down`` separando os
    blocos de upgrade e downgrade. Seções fora dessas marcações são ignoradas.

    Raises:
        ValueError: Se o nome do arquivo não segue o padrão ``NNNN_<nome>.sql``.
    """
    stem = path.stem
    m = re.match(r"^(\d{4})_(.+)$", stem)
    if not m:
        raise ValueError(
            f"Nome de migration inválido: {path.name!r}. "
            "Esperado: NNNN_<nome>.sql (ex: 0001_auth.sql)"
        )
    version, name = m.group(1), m.group(2)

    content = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode()).hexdigest()

    # Divide o arquivo em seções pelo marcador "-- up" / "-- down"
    parts = _SECTION_RE.split(content)
    sections: dict[str, str] = {}
    i = 1  # parts[0] é o texto antes do primeiro marcador (geralmente comentário)
    while i < len(parts) - 1:
        section_name = parts[i].strip().lower()
        section_body = parts[i + 1]
        sections[section_name] = section_body
        i += 2

    return MigrationFile(
        version=version,
        name=name,
        path=path,
        up_sql=sections.get("up", ""),
        down_sql=sections.get("down", ""),
        checksum=checksum,
    )


# ---------------------------------------------------------------------------
# MigrationRunner
# ---------------------------------------------------------------------------


class MigrationRunner:
    """Aplica e reverte migrations em um banco SQLite assíncrono.

    Args:
        conn:           Conexão ``aiosqlite.Connection`` aberta.
        migrations_dir: Diretório com os arquivos ``NNNN_*.sql``.
                        Default: diretório ``migrations/`` ao lado deste arquivo.
    """

    def __init__(
        self,
        conn: Any,  # aiosqlite.Connection
        migrations_dir: str | Path | None = None,
    ) -> None:
        self._conn = conn
        self._dir = (
            Path(migrations_dir) if migrations_dir else Path(__file__).parent / "sqlite"
        )

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

    async def _ensure_control_table(self) -> None:
        """Cria a tabela ``schema_migrations`` se não existir."""
        await self._conn.executescript(_CONTROL_SCHEMA)
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Leitura de estado
    # ------------------------------------------------------------------

    def _load_files(self) -> list[MigrationFile]:
        """Retorna todos os arquivos ``.sql`` do diretório, ordenados por versão."""
        files = sorted(
            self._dir.glob("*.sql"),
            key=lambda p: p.stem.split("_")[0],
        )
        result = []
        for f in files:
            try:
                result.append(_parse_sql_file(f))
            except ValueError as exc:
                logger.warning("storage/migrations: ignorando arquivo: %s", exc)
        return result

    async def _applied(self) -> dict[str, dict[str, str]]:
        """Retorna dict ``{version: {applied_at, checksum}}`` das migrations aplicadas."""
        await self._ensure_control_table()
        cursor = await self._conn.execute(
            "SELECT version, applied_at, checksum FROM schema_migrations ORDER BY version"
        )
        rows = await cursor.fetchall()
        return {
            r["version"]: {"applied_at": r["applied_at"], "checksum": r["checksum"]}
            for r in rows
        }

    async def status(self) -> list[MigrationStatus]:
        """Retorna o status de cada migration (aplicada / pendente / drift).

        Returns:
            Lista ordenada por versão.
        """
        files = self._load_files()
        applied = await self._applied()
        result = []
        for mf in files:
            rec = applied.get(mf.version)
            if rec is None:
                result.append(
                    MigrationStatus(
                        version=mf.version,
                        name=mf.name,
                        applied=False,
                        applied_at=None,
                        drift=False,
                    )
                )
            else:
                drift = rec["checksum"] != mf.checksum
                result.append(
                    MigrationStatus(
                        version=mf.version,
                        name=mf.name,
                        applied=True,
                        applied_at=rec["applied_at"],
                        drift=drift,
                    )
                )
        return result

    # ------------------------------------------------------------------
    # Upgrade
    # ------------------------------------------------------------------

    async def upgrade(self, target: str | None = None) -> list[str]:
        """Aplica todas as migrations pendentes até ``target`` (inclusive).

        Args:
            target: Versão máxima a aplicar (ex: ``"0003"``). Se None, aplica
                    todas as pendentes.

        Returns:
            Lista de versões aplicadas nesta chamada.
        """
        files = self._load_files()
        applied = await self._applied()
        applied_now: list[str] = []

        for mf in files:
            if target is not None and mf.version > target:
                break
            if mf.version in applied:
                continue
            if not mf.up_sql.strip():
                logger.warning(
                    "storage/migrations: migration %s não tem seção -- up, pulando",
                    mf.version,
                )
                continue
            logger.info("storage/migrations: aplicando %s_%s", mf.version, mf.name)
            await self._conn.executescript(mf.up_sql)
            now = datetime.now(UTC).isoformat()
            await self._conn.execute(
                "INSERT OR REPLACE INTO schema_migrations "
                "(version, name, applied_at, checksum) VALUES (?, ?, ?, ?)",
                (mf.version, mf.name, now, mf.checksum),
            )
            await self._conn.commit()
            applied_now.append(mf.version)
            logger.info("storage/migrations: %s_%s aplicada", mf.version, mf.name)

        if not applied_now:
            logger.info("storage/migrations: banco atualizado — nada a fazer")
        return applied_now

    # ------------------------------------------------------------------
    # Downgrade
    # ------------------------------------------------------------------

    async def downgrade(self, target: str) -> list[str]:
        """Reverte migrations até ``target`` (inclusive — target é revertida).

        Args:
            target: Versão mais antiga a reverter (ex: ``"0002"`` reverte
                    ``0003``, ``0002`` nessa ordem).

        Returns:
            Lista de versões revertidas nesta chamada.
        """
        files = self._load_files()
        applied = await self._applied()
        # Reverte em ordem decrescente de versão
        to_revert = sorted(
            [mf for mf in files if mf.version in applied and mf.version >= target],
            key=lambda mf: mf.version,
            reverse=True,
        )
        reverted: list[str] = []
        for mf in to_revert:
            if not mf.down_sql.strip():
                logger.warning(
                    "storage/migrations: migration %s não tem seção -- down, pulando",
                    mf.version,
                )
                continue
            logger.info("storage/migrations: revertendo %s_%s", mf.version, mf.name)
            await self._conn.executescript(mf.down_sql)
            await self._conn.execute(
                "DELETE FROM schema_migrations WHERE version = ?", (mf.version,)
            )
            await self._conn.commit()
            reverted.append(mf.version)
            logger.info("storage/migrations: %s_%s revertida", mf.version, mf.name)
        return reverted


# ---------------------------------------------------------------------------
# Atalho de conveniência
# ---------------------------------------------------------------------------


async def run_migrations(
    conn: Any,
    migrations_dir: str | Path | None = None,
    *,
    target: str | None = None,
) -> list[str]:
    """Aplica todas as migrations pendentes em ``conn``.

    Atalho para uso no startup de services:

        from backend.storage.migrations import run_migrations
        await run_migrations(conn)

    Args:
        conn:            Conexão aiosqlite aberta.
        migrations_dir:  Diretório com ``NNNN_*.sql``. Default: pasta ``migrations/``.
        target:          Versão máxima (inclusive). None = tudo.

    Returns:
        Lista de versões aplicadas.
    """
    runner = MigrationRunner(conn, migrations_dir)
    return await runner.upgrade(target=target)
