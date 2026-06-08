"""Infraestrutura de i18n da Vectora TUI.

Mesmo formato de `chat/lib/i18n` (CSV `key,en,es,pt-BR` + resolver com
fallback em cascata `idioma → en → chave`), adaptado ao contexto
Python/Textual:

  strings.csv  → fonte de verdade (carregada 1x via `csv.reader` da stdlib,
                 que já resolve aspas/escapes/vírgulas corretamente)
  __init__.py  → `t(key, **kwargs)` — tradução com interpolação `{var}`

Resolução do idioma (`_resolve_language`):
  1. `runtime_settings.language` (preferência persistida via `/language`)
  2. variável de ambiente `LANG` (normalizada: "pt_BR.UTF-8" -> "pt-BR")
  3. fallback final: "en"

Uso:
    from src.ui.i18n import t
    t("tui.help.title")                       # -> "Comandos disponíveis:"
    t("tui.session.current", id=thread_id)    # -> "Sessão atual: abc123"
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).parent / "strings.csv"

# Idiomas suportados — devem bater 1:1 com o cabeçalho de `strings.csv` e com
# `_VALID_LANGUAGES` em `src/services/runtime_settings.py`.
_SUPPORTED_LANGUAGES = ("en", "es", "pt-BR")
_FALLBACK_LANGUAGE = "en"

TranslationMap = dict[str, dict[str, str]]


def _load_translations(path: Path) -> TranslationMap:
    """Carrega e parseia `strings.csv` uma única vez (módulo é importado 1x).

    Usa `csv.reader` da stdlib — resolve aspas/escapes/vírgulas em campos
    sem precisar de um parser manual.
    """
    table: TranslationMap = {}
    if not path.exists():
        logger.warning("ui.i18n: strings.csv não encontrado em %s", path)
        return table

    try:
        with path.open(encoding="utf-8") as fh:
            # Filtra linhas de comentário (`#...`) e em branco antes do
            # csv.reader — comentários não são um conceito do formato CSV.
            rows = list(
                csv.reader(
                    line
                    for line in fh
                    if line.strip() and not line.lstrip().startswith("#")
                )
            )
    except Exception:
        logger.exception("ui.i18n: erro ao ler strings.csv")
        return table

    if not rows:
        return table

    header = rows[0]
    languages = header[1:]
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        key = row[0]
        table[key] = {
            lang: (row[idx + 1] if idx + 1 < len(row) else "")
            for idx, lang in enumerate(languages)
        }
    return table


# Parse executado uma única vez na importação — resultado estático/imutável.
_TRANSLATIONS: TranslationMap = _load_translations(_CSV_PATH)


def _normalize_lang_env(raw: str) -> str | None:
    """Normaliza valores de `$LANG` ("pt_BR.UTF-8") para nosso formato curto.

    Retorna `None` quando não reconhece o idioma — deixa o chamador seguir
    para o próximo passo da cadeia de fallback em vez de assumir "en" cedo
    demais (ex.: locales `C`/`POSIX` não dizem nada sobre o idioma do usuário).
    """
    if not raw:
        return None
    primary = (
        raw.split(".", maxsplit=1)[0]
        .split(":", maxsplit=1)[0]
        .replace("_", "-")
        .lower()
    )
    if primary in ("c", "posix", ""):
        return None
    if primary.startswith("pt"):
        return "pt-BR"
    if primary.startswith("es"):
        return "es"
    if primary.startswith("en"):
        return "en"
    return None


def _resolve_language() -> str:
    """Resolve o idioma ativo: runtime_settings -> $LANG -> "en"."""
    try:
        from src.services.runtime_settings import runtime_settings

        lang = runtime_settings.language
        if lang in _SUPPORTED_LANGUAGES:
            return lang
    except Exception:
        # runtime_settings pode não estar disponível em testes isolados —
        # cai para a heurística de ambiente abaixo.
        pass

    env_lang = _normalize_lang_env(os.environ.get("LANG", ""))
    if env_lang in _SUPPORTED_LANGUAGES:
        return env_lang

    return _FALLBACK_LANGUAGE


def t(key: str, **kwargs: object) -> str:
    """Traduz `key` para o idioma ativo, com interpolação `{var}`.

    Fallback em cascata: idioma ativo -> inglês -> a própria chave (nunca
    levanta `KeyError` — preferimos uma chave "feia" visível no terminal a
    derrubar a TUI por causa de uma string faltando).

    Exemplo:
        t("tui.session.current", id="abc123")
        # -> "Sessão atual: abc123" (pt-BR) | "Current session: abc123" (en)
    """
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        logger.debug("ui.i18n: chave ausente: %s", key)
        return key

    language = _resolve_language()
    template = entry.get(language) or entry.get(_FALLBACK_LANGUAGE) or key

    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        # Placeholder sem valor correspondente — devolve o template cru em
        # vez de quebrar a TUI por causa de uma interpolação malformada.
        return template


__all__ = ["t"]
