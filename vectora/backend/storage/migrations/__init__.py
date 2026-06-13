"""Runner de schema versioning para SQLite.

Substitui o padrão ``ALTER TABLE … suppress(Exception)`` espalhado pelos
services por um sistema declarativo de migrations versionadas.
"""

from backend.storage.migrations.runner import MigrationRunner, run_migrations

__all__ = ["MigrationRunner", "run_migrations"]
