"""Adapters que envolvem os mecanismos de persistência já existentes com a
interface uniforme ``get(key)``/``set(key, value)`` exigida por
``backend.config.registry.SettingField`` — nenhum deles substitui o
mecanismo real, só declara um contrato comum por cima.
"""

from __future__ import annotations


class EnvAdapter:
    """Envolve ``backend/services/env_keys.py`` — persiste em ``.env`` +
    ``os.environ`` + ``settings`` (singleton em memória), mesmo caminho já
    usado por ``/auth/envs`` e ``/admin/api-keys``.
    """

    def __init__(self, env_var: str) -> None:
        self.env_var = env_var

    def get(self, key: str) -> object:
        from backend.settings import settings

        return getattr(settings, self.env_var.lower(), None)

    def set(self, key: str, value: object) -> None:
        from backend.services.env_keys import apply_llm_env_key, default_env_file

        apply_llm_env_key(default_env_file(), self.env_var, str(value or ""))


class RuntimeSettingsAdapter:
    """Envolve ``backend/workspace/runtime_settings.py`` (SQLite
    ``app_settings``, global — não por usuário). ``settings_key`` permite
    apontar pra uma chave interna diferente do nome público do campo (ex.:
    campo público ``timezone`` → chave interna ``user_timezone``).
    """

    def __init__(self, settings_key: str | None = None) -> None:
        self.settings_key = settings_key

    def get(self, key: str) -> object:
        from backend.workspace.runtime_settings import runtime_settings

        return runtime_settings.get(self.settings_key or key)

    def set(self, key: str, value: object) -> None:
        from backend.workspace.runtime_settings import runtime_settings

        runtime_settings.set(self.settings_key or key, value)


class ConfigTomlAdapter:
    """Envolve ``backend/services/license.py::write_config_section``
    (``~/.vectora/config.toml``) — usado pela seção ``[server]`` hoje
    consumida por ``/admin/config``. Mantém ``settings`` (singleton em
    memória) sincronizado, mesmo padrão do handler REST existente.
    """

    def __init__(self, section: str, toml_key: str | None = None) -> None:
        self.section = section
        self.toml_key = toml_key

    def get(self, key: str) -> object:
        from backend.settings import settings

        return getattr(settings, self.toml_key or key, None)

    def set(self, key: str, value: object) -> None:
        from backend.services.license import write_config_section
        from backend.settings import settings

        if value is not None and not isinstance(value, (str, int, bool)):
            msg = f"ConfigTomlAdapter só aceita str/int/bool/None, recebeu {type(value)!r}"
            raise TypeError(msg)
        attr = self.toml_key or key
        object.__setattr__(settings, attr, value)
        write_config_section(self.section, {attr: value})


class RegisteredModelsTableAdapter:
    """Envolve as tabelas SQLite ad hoc de modelos registrados por gateway do
    `provider_routing` (``ollama_registered_models`` / ``openrouter_registered_models``
    / ``nine_router_registered_models``). Reusa o resolver de DB e as funções
    internas do handler — não duplica a lógica de tabela.
    """

    def __init__(self, table: str) -> None:
        self.table = table

    async def list_items(self) -> list[dict[str, str]]:
        from backend.api.handlers.provider_routing import _list_registered

        rows = await _list_registered(self.table)
        return [{"id": r.id, "tag": r.tag, "created_at": r.created_at} for r in rows]

    async def add(self, item: dict[str, str]) -> dict[str, str]:
        from backend.api.handlers.provider_routing import _register

        registered = await _register(self.table, item["tag"])
        return {
            "id": registered.id,
            "tag": registered.tag,
            "created_at": registered.created_at,
        }

    async def remove(self, item_id: str) -> None:
        from backend.api.handlers.provider_routing import _unregister

        await _unregister(self.table, item_id)
