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
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_SETTINGS_FILE = Path.home() / ".vectora" / "settings.json"

_DEFAULTS: dict = {
    "active_provider": "google-genai",
    "active_model": "gemini-2.5-flash",
    "verbosity": 0,
}


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
    def verbosity(self) -> int:
        """Verbosity level 0-5. 0 = silent, 5 = full debug panel."""
        return int(self.get("verbosity", 0))  # type: ignore[arg-type]

    @property
    def debug_mode(self) -> bool:
        """Backward-compat: True when verbosity >= 5."""
        return self.verbosity >= 5

    # ─── Métodos de negócio ───────────────────────────────────────────────────

    def set_active_model(self, provider: str, model: str) -> None:
        """Troca provider + model ativos e persiste (thread-safe)."""
        with self._lock:
            self._data["active_provider"] = provider
            self._data["active_model"] = model
            self._save()
        logger.info("runtime_settings: provider=%s model=%s", provider, model)

    def set_verbosity(self, level: int) -> None:
        """Define verbosity level (0-5) e persiste."""
        self.set("verbosity", max(0, min(5, level)))

    def set_debug_mode(self, enabled: bool) -> None:
        """Backward-compat: liga/desliga verbosity entre 0 e 5."""
        self.set_verbosity(5 if enabled else 0)

    @property
    def last_session_by_dir(self) -> dict[str, str]:
        """Mapping of working directory path -> thread_id (6-digit string)."""
        val = self.get("last_session_by_dir", {})
        return val if isinstance(val, dict) else {}

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
