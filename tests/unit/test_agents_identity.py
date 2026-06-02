"""Tests for src/agents/_identity.py"""

from __future__ import annotations

import pytest

from src.agents._identity import (
    VECTORA_IDENTITY,
    build_user_context_block,
    detect_system_language,
)

# ---------------------------------------------------------------------------
# VECTORA_IDENTITY (constante)
# ---------------------------------------------------------------------------


def test_identity_is_string():
    assert isinstance(VECTORA_IDENTITY, str)
    assert len(VECTORA_IDENTITY) > 200


def test_identity_contains_stack():
    assert "LangChain" in VECTORA_IDENTITY
    assert "LangGraph" in VECTORA_IDENTITY
    assert "FastMCP" in VECTORA_IDENTITY
    assert "LanceDB" in VECTORA_IDENTITY


def test_identity_contains_license_and_repo():
    assert "Apache 2.0" in VECTORA_IDENTITY
    assert "github.com" in VECTORA_IDENTITY


def test_identity_mentions_cohere():
    assert "Cohere" in VECTORA_IDENTITY


def test_identity_describes_agents():
    assert "Orchestrator" in VECTORA_IDENTITY
    assert "Direct" in VECTORA_IDENTITY
    assert "Search" in VECTORA_IDENTITY
    assert "Coder" in VECTORA_IDENTITY


# ---------------------------------------------------------------------------
# detect_system_language — locale do SO, cru
# ---------------------------------------------------------------------------
#
# Fixture limpa as 3 envs de locale antes de cada teste. Cada caso seta
# explicitamente o que precisa. Sem isso, o locale da máquina onde a suite
# roda contamina as expectativas.


@pytest.fixture
def clean_locale_env(monkeypatch):
    """Remove LC_ALL / LC_MESSAGES / LANG do ambiente do teste."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


class TestDetectSystemLanguage:
    def test_returns_lc_all_when_set(self, clean_locale_env):
        clean_locale_env.setenv("LC_ALL", "pt_BR.UTF-8")
        assert detect_system_language() == "pt_BR"

    def test_returns_lang_when_lc_all_absent(self, clean_locale_env):
        clean_locale_env.setenv("LANG", "en_US.UTF-8")
        assert detect_system_language() == "en_US"

    def test_lc_all_has_priority_over_lang(self, clean_locale_env):
        """LC_ALL vence LANG (semântica POSIX)."""
        clean_locale_env.setenv("LC_ALL", "es_ES.UTF-8")
        clean_locale_env.setenv("LANG", "pt_BR.UTF-8")
        assert detect_system_language() == "es_ES"

    def test_lc_messages_between_lc_all_and_lang(self, clean_locale_env):
        """LC_MESSAGES > LANG quando LC_ALL ausente."""
        clean_locale_env.setenv("LC_MESSAGES", "fr_FR.UTF-8")
        clean_locale_env.setenv("LANG", "pt_BR.UTF-8")
        assert detect_system_language() == "fr_FR"

    def test_drops_encoding_suffix(self, clean_locale_env):
        """`.UTF-8`, `.cp1252` etc. são descartados — só o sufixo de encoding."""
        clean_locale_env.setenv("LC_ALL", "pt_BR.UTF-8")
        assert detect_system_language() == "pt_BR"

        clean_locale_env.delenv("LC_ALL")
        clean_locale_env.setenv("LANG", "es_AR.ISO8859-1")
        assert detect_system_language() == "es_AR"

    def test_no_normalization_of_format(self, clean_locale_env):
        """O formato é repassado cru — hífen vs underscore, código longo etc."""
        clean_locale_env.setenv("LC_ALL", "es-419")
        assert detect_system_language() == "es-419"

        clean_locale_env.delenv("LC_ALL")
        clean_locale_env.setenv("LANG", "pt-br")
        assert detect_system_language() == "pt-br"

    def test_ignores_c_and_posix_locales(self, clean_locale_env):
        """`C` e `POSIX` são locales "neutros" — equivalem a "sem preferência"."""
        clean_locale_env.setenv("LC_ALL", "C")
        # Sem fallback do SO, deve devolver vazio. Mocka getdefaultlocale para
        # garantir resposta vazia mesmo num ambiente que tenha locale do SO.
        import src.agents._identity as identity_mod

        clean_locale_env.setattr(
            identity_mod, "__name__", identity_mod.__name__
        )  # noop; mantém referência
        # Patch direto no módulo locale para isolar do SO real
        import locale as _locale

        clean_locale_env.setattr(_locale, "getdefaultlocale", lambda: (None, None))
        clean_locale_env.setattr(_locale, "getlocale", lambda *a, **kw: (None, None))
        assert detect_system_language() == ""

        clean_locale_env.setenv("LC_ALL", "POSIX")
        assert detect_system_language() == ""

    def test_returns_empty_when_nothing_set_and_locale_empty(self, clean_locale_env):
        """Sem env vars e sem locale do SO → string vazia."""
        import locale as _locale

        clean_locale_env.setattr(_locale, "getdefaultlocale", lambda: (None, None))
        clean_locale_env.setattr(_locale, "getlocale", lambda *a, **kw: (None, None))
        assert detect_system_language() == ""

    def test_falls_back_to_getdefaultlocale(self, clean_locale_env):
        """Sem env vars, getdefaultlocale do Python decide (caso típico Windows)."""
        import locale as _locale

        clean_locale_env.setattr(
            _locale, "getdefaultlocale", lambda: ("pt_BR", "cp1252")
        )
        assert detect_system_language() == "pt_BR"

    def test_accepts_windows_style_locale(self, clean_locale_env):
        """Locale estilo Windows ('Portuguese_Brazil') é repassado cru."""
        import locale as _locale

        clean_locale_env.setattr(_locale, "getdefaultlocale", lambda: (None, None))
        clean_locale_env.setattr(
            _locale, "getlocale", lambda *a, **kw: ("Portuguese_Brazil", "1252")
        )
        assert detect_system_language() == "Portuguese_Brazil"


# ---------------------------------------------------------------------------
# build_user_context_block — montagem do bloco
# ---------------------------------------------------------------------------


class TestBuildUserContextBlock:
    def test_returns_empty_for_none_config(self):
        assert build_user_context_block(None) == ""

    def test_returns_empty_for_empty_dict(self):
        assert build_user_context_block({}) == ""

    def test_returns_empty_when_neither_name_nor_language(self):
        assert build_user_context_block({"thread_id": "abc"}) == ""

    def test_includes_name_line(self):
        block = build_user_context_block({"user_name": "Bruno Soares"})
        assert "## Contexto do usuário atual" in block
        assert "Bruno Soares" in block
        assert "**Nome:**" in block

    def test_includes_language_line(self):
        block = build_user_context_block({"language": "pt_BR"})
        assert "## Contexto do usuário atual" in block
        assert "`pt_BR`" in block
        assert "**Idioma preferido:**" in block

    def test_includes_both_when_present(self):
        block = build_user_context_block(
            {"user_name": "Maria José", "language": "es-419"}
        )
        assert "Maria José" in block
        assert "`es-419`" in block

    def test_locale_string_is_passed_raw(self):
        """Qualquer formato do SO entra literal — sem dicionário de mapeamento."""
        for raw in ("pt_BR", "es-419", "en_US", "pt-br", "pt-pt", "Portuguese_Brazil"):
            block = build_user_context_block({"language": raw})
            assert f"`{raw}`" in block

    def test_strips_whitespace_around_name(self):
        block = build_user_context_block({"user_name": "  Bruno  "})
        # O bloco contém o nome após strip, mas o helper apenas remove
        # whitespace nas pontas — espaços internos devem ser preservados.
        assert "Bruno" in block
        # Não há os 2 espaços extras no início
        assert "  Bruno  " not in block

    def test_name_with_accents_and_apostrophe(self):
        """UTF-8 livre — sem rejeição de acentos, ç, apóstrofo, espaço."""
        names = ["João D'Ávila", "Maria José", "François", "Iñaki", "山田太郎"]
        for n in names:
            block = build_user_context_block({"user_name": n})
            assert n in block

    def test_ignores_empty_string_values(self):
        """user_name="" e language="" não devem produzir linhas vazias."""
        assert build_user_context_block({"user_name": "", "language": ""}) == ""

    def test_does_not_leak_other_configurable_fields(self):
        """Apenas user_name e language são consumidos — workspace_id e cia ignorados."""
        block = build_user_context_block(
            {
                "user_name": "Bruno",
                "language": "pt_BR",
                "workspace_id": "ws-secret",
                "thread_id": "thread-secret",
                "user_id": "user-secret",
            }
        )
        assert "ws-secret" not in block
        assert "thread-secret" not in block
        assert "user-secret" not in block
