"""RuntimeSettings — Preferências de runtime persistidas em ~/.vectora/settings.json.

Separação clara de responsabilidades:
  ~/.vectora/.env      → segredos (API keys, tokens) — NÃO versionar
  ~/.vectora/settings.json → preferências não-secretas (provider ativo, model, debug)

Diferente do Settings (pydantic, lido na startup), o RuntimeSettings pode ser
atualizado em tempo de execução via /model, /debug, etc., e as mudanças são
imediatamente persistidas e aplicadas sem reiniciar.

Uso:
    from vectora.services.runtime_settings import runtime_settings
    runtime_settings.set_active_model("google-genai", "gemini-2.5-flash")
    print(runtime_settings.active_provider)  # "google-genai"
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

_SETTINGS_FILE = Path.home() / ".vectora" / "settings.json"

_DEFAULTS: dict = {
    "active_provider": "google-genai",
    "active_model": "gemini-2.5-flash",
    "theme": "dark",
    "language": "en",
}

# Temas válidos da TUI (ver `src/ui/theme.py`: VECTORA_DARK/LIGHT/SYSTEM).
_VALID_THEMES = ("dark", "light", "system")

# Idiomas válidos da TUI (ver `src/ui/i18n`: csv `key,en,es,pt-BR`).
_VALID_LANGUAGES = ("en", "es", "pt-BR")


class RuntimeSettings:
    """Thin JSON store para preferências de runtime não-secretas.

    Thread-safe: leituras são lock-free (snapshot atômico do dict Python);
    escritas usam threading.Lock para evitar race condition quando múltiplos
    threads (ex: UI thread + background worker) chamam set() simultaneamente.
    """

    def __init__(self, path: Path = _SETTINGS_FILE) -> None:
        self._path = path
        self._data: dict = {}
        self._lock = threading.Lock()
        self._load()

    # ─── I/O ────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Carrega do disco; silencia erros e usa defaults."""
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
                logger.debug("runtime_settings: carregado de %s", self._path)
            except Exception as e:
                logger.warning(
                    "runtime_settings: erro ao carregar (%s) — usando defaults", e
                )
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        """Persiste para disco; silencia erros (nunca trava o runtime)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("runtime_settings: salvo em %s", self._path)
        except Exception as e:
            logger.warning("runtime_settings: erro ao salvar (%s)", e)

    def reload(self) -> None:
        """Recarrega do disco (útil após mudanças externas)."""
        with self._lock:
            self._load()

    # ─── Acesso genérico ─────────────────────────────────────────────────────

    def get(self, key: str, default: object = None) -> object:
        """Retorna valor do settings.json, com fallback para _DEFAULTS.

        Leitura é lock-free: Python GIL garante atomicidade do dict.get().
        """
        return self._data.get(key, _DEFAULTS.get(key, default))

    def set(self, key: str, value: object) -> None:
        """Persiste um valor de forma thread-safe."""
        with self._lock:
            self._data[key] = value
            self._save()

    # ─── Properties tipadas ───────────────────────────────────────────────────

    @property
    def active_provider(self) -> str:
        return str(self.get("active_provider", "google-genai"))

    @property
    def active_model(self) -> str:
        return str(self.get("active_model", "gemini-2.5-flash"))

    @property
    def theme(self) -> str:
        """Tema ativo da TUI: 'dark' | 'light' | 'system' (ver `src/ui/theme.py`)."""
        raw = str(self.get("theme", "dark"))
        return raw if raw in _VALID_THEMES else "dark"

    @property
    def language(self) -> str:
        """Idioma ativo da TUI: 'en' | 'es' | 'pt-BR' (ver `src/ui/i18n`).

        Resolução em `src/ui/i18n/__init__.py::t()` segue
        `runtime_settings.language` → env `LANG` → "en".
        """
        raw = str(self.get("language", "en"))
        return raw if raw in _VALID_LANGUAGES else "en"

    # ─── Métodos de negócio ───────────────────────────────────────────────────

    @property
    def storage_mode(self) -> str:
        """Modo de storage ativo: 'lite' (SQLite+LanceDB) | 'complete' (Postgres+Qdrant+Redis).

        Sobrepõe `Settings.storage_mode` em runtime (alterado via
        `PATCH /admin/storage`, ver `src/api/handlers/admin.py`).
        """
        raw = str(self.get("storage_mode", "lite"))
        return raw if raw in ("lite", "complete") else "lite"

    @storage_mode.setter
    def storage_mode(self, value: str) -> None:
        self.set("storage_mode", value if value in ("lite", "complete") else "lite")

    def get_service_startup(self, service: str) -> dict:
        """Configuração de auto-start para um serviço self-hosted do modo
        "complete" (``postgres`` | ``redis`` | ``qdrant``).

        Retorna ``{"self_hosted": bool, "start_command": str | None}``. Usado
        por ``POST /admin/storage/test`` (Setup Wizard) para tentar subir o
        serviço localmente quando a conexão falha. Não se aplica a serviços
        terceirizados (Supabase, Upstash, Qdrant Cloud etc.).
        """
        services = self.get("storage_services", {})
        if not isinstance(services, dict):
            return {"self_hosted": False, "start_command": None}
        cfg = cast("dict[str, Any]", services).get(service)
        if not isinstance(cfg, dict):
            return {"self_hosted": False, "start_command": None}
        return {
            "self_hosted": bool(cfg.get("self_hosted", False)),
            "start_command": cfg.get("start_command") or None,
        }

    def set_service_startup(
        self, service: str, *, self_hosted: bool, start_command: str | None
    ) -> None:
        """Persiste a configuração de auto-start de um serviço self-hosted."""
        with self._lock:
            services = self._data.get("storage_services", {})
            if not isinstance(services, dict):
                services = {}
            services[service] = {
                "self_hosted": self_hosted,
                "start_command": start_command,
            }
            self._data["storage_services"] = services
            self._save()

    def set_active_model(self, provider: str, model: str) -> None:
        """Troca provider + model ativos e persiste (thread-safe)."""
        with self._lock:
            self._data["active_provider"] = provider
            self._data["active_model"] = model
            self._save()
        logger.info("runtime_settings: provider=%s model=%s", provider, model)

    def set_theme(self, theme: str) -> None:
        """Define o tema da TUI ('dark'|'light'|'system') e persiste.

        Valores fora de `_VALID_THEMES` caem em 'dark' — mantém o arquivo
        consistente mesmo se um valor inválido chegar via edição manual
        do settings.json ou de uma versão futura/antiga do app.
        """
        self.set("theme", theme if theme in _VALID_THEMES else "dark")

    def set_language(self, language: str) -> None:
        """Define o idioma da TUI ('en'|'es'|'pt-BR') e persiste.

        Mesma lógica defensiva de `set_theme` — valor inválido cai em 'en'.
        """
        self.set("language", language if language in _VALID_LANGUAGES else "en")

    @property
    def fallback_order(self) -> list[str]:
        """Ordem de fallback de providers LLM (lista de 'provider:model')."""
        val = self.get("llm_fallback_order", [])
        return [str(x) for x in val] if isinstance(val, list) else []

    def set_fallback_order(self, order: list[str]) -> None:
        """Define a ordem de fallback de LLM e persiste.

        Filtra entradas vazias/em branco, preserva a ordem fornecida.
        """
        clean = [str(x).strip() for x in order if str(x).strip()]
        self.set("llm_fallback_order", clean)

    @property
    def last_session_by_dir(self) -> dict[str, str]:
        """Mapping of working directory path -> thread_id (6-digit string)."""
        val = self.get("last_session_by_dir", {})
        if not isinstance(val, dict):
            return {}
        return {str(k): str(v) for k, v in val.items()}

    def get_session_for_dir(self, cwd: str) -> str | None:
        """Return the last thread_id used in the given directory, or None."""
        return self.last_session_by_dir.get(cwd)

    def set_session_for_dir(self, cwd: str, thread_id: str) -> None:
        """Persist the last thread_id used in the given directory."""
        with self._lock:
            mapping = dict(self.last_session_by_dir)
            mapping[cwd] = thread_id
            self._data["last_session_by_dir"] = mapping
            self._save()


# Singleton — único por processo
runtime_settings = RuntimeSettings()


# ── Orquestração de troca de modelo ──────────────────────────────────────────


def _invalidate_default_graph() -> None:
    """Invalida o grafo deep-agent do modelo padrão após troca de provider/model."""
    try:
        from backend.services.agent_factory import reset_default_graph

        reset_default_graph()
    except Exception as e:
        logger.warning("Erro ao invalidar grafo do modelo padrão: %s", e)


def apply_model_change(provider: str, model: str) -> None:
    """Aplica troca de provider/model: settings.json + os.environ + Settings em memória + singletons LLM."""
    from backend.settings import PROVIDER_MODEL_ENV, settings

    # 1. Persiste em settings.json
    runtime_settings.set_active_model(provider, model)

    # 2. Atualiza os.environ (efeito imediato para load_llm())
    os.environ["LLM_PROVIDER"] = provider
    if env_var := PROVIDER_MODEL_ENV.get(provider):
        os.environ[env_var] = model

    # 3. Atualiza o singleton Settings em memória
    try:
        settings.llm_provider = provider  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        settings.set_model(provider, model)
    except Exception as e:
        logger.warning("Erro ao atualizar settings singleton: %s", e)

    # 4. Invalida o grafo do modelo padrão -> próxima chamada recompila com o novo LLM
    _invalidate_default_graph()
    logger.info("Model aplicado: provider=%s model=%s", provider, model)
