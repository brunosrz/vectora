"""Temas da Vectora TUI (Textual `DEFAULT_CSS`).

Define a CSS em três variantes nomeadas e expõe um resolvedor único
(`get_theme_css`) que a TUI consulta a partir de ``runtime_settings.theme``
(persistido em ``~/.vectora/settings.json`` via ``/theme``, no mesmo padrão
de ``/model``/``/debug``).

Limitação conhecida: Textual lê ``DEFAULT_CSS`` como atributo de classe — não
há (ainda) reload automático de stylesheet ao trocar `runtime_settings.theme`
em runtime. A app resolve o tema na construção (`__init__`/definição de
classe); uma troca via `/theme` exige reabrir a TUI até existir um mecanismo
de `refresh_css` dedicado (ver TODO em `app.py`).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# VECTORA_DARK — tema padrão (tons escuros navy/azul, paleta principal da TUI)
# ---------------------------------------------------------------------------

VECTORA_DARK = """
Screen {
    background: #0a0e1a;
}

Header {
    background: #0a0e1a;
    color: #60a5fa;
    height: 1;
}

#messages {
    width: 1fr;
    height: 1fr;
    padding: 1 2;
    background: #0a0e1a;
    scrollbar-size: 1 1;
    scrollbar-color: #1e3a5f #0a0e1a;
}

#bottom-area {
    dock: bottom;
    height: auto;
    background: #0a0e1a;
    border-top: solid #1e2d40;
}

#command-popup {
    display: none;
    background: #0d1525;
    border: round #3b82f6;
    height: auto;
    max-height: 8;
    margin: 0 2;
}

#input-row {
    height: 3;
    padding: 0;
    align: left middle;
}

#input-prompt {
    width: 3;
    color: #3b82f6;
    content-align: center middle;
    text-style: bold;
}

Input {
    width: 1fr;
    background: #0a0e1a;
    border: tall #0a0e1a;
    color: #e2e8f0;
    padding: 0 2 0 0;
    margin: 0 1 0 0;
}

Input:focus {
    border: tall #3b82f6;
    background: #0a0e1a;
}

#status-bar {
    height: 1;
    background: #0d1525;
    padding: 0 2;
}

#status-info {
    width: 1fr;
    color: #374151;
    content-align: left middle;
}

#status-keys {
    width: auto;
    color: #1e3a5f;
    content-align: right middle;
}

.msg-user {
    color: #e2e8f0;
    margin: 1 0 0 0;
}

.msg-assistant {
    color: #93c5fd;
    margin: 0 0 1 0;
}

.msg-system {
    color: #374151;
    text-style: italic;
}

OptionList {
    background: #0d1525;
    padding: 0;
    scrollbar-size: 1 1;
}

OptionList > .option-list--option {
    padding: 0 1;
    height: 1;
    color: #a0aec0;
}

OptionList > .option-list--option-highlighted {
    background: #1e3a5f;
    color: #60a5fa;
}
"""

# ---------------------------------------------------------------------------
# VECTORA_LIGHT — paleta clara (mesma estrutura/seletores, tons invertidos)
# ---------------------------------------------------------------------------

VECTORA_LIGHT = """
Screen {
    background: #f8fafc;
}

Header {
    background: #f8fafc;
    color: #2563eb;
    height: 1;
}

#messages {
    width: 1fr;
    height: 1fr;
    padding: 1 2;
    background: #f8fafc;
    scrollbar-size: 1 1;
    scrollbar-color: #cbd5e1 #f8fafc;
}

#bottom-area {
    dock: bottom;
    height: auto;
    background: #f8fafc;
    border-top: solid #e2e8f0;
}

#command-popup {
    display: none;
    background: #ffffff;
    border: round #2563eb;
    height: auto;
    max-height: 8;
    margin: 0 2;
}

#input-row {
    height: 3;
    padding: 0;
    align: left middle;
}

#input-prompt {
    width: 3;
    color: #2563eb;
    content-align: center middle;
    text-style: bold;
}

Input {
    width: 1fr;
    background: #ffffff;
    border: tall #ffffff;
    color: #1e293b;
    padding: 0 2 0 0;
    margin: 0 1 0 0;
}

Input:focus {
    border: tall #2563eb;
    background: #ffffff;
}

#status-bar {
    height: 1;
    background: #eef2f7;
    padding: 0 2;
}

#status-info {
    width: 1fr;
    color: #64748b;
    content-align: left middle;
}

#status-keys {
    width: auto;
    color: #94a3b8;
    content-align: right middle;
}

.msg-user {
    color: #1e293b;
    margin: 1 0 0 0;
}

.msg-assistant {
    color: #1d4ed8;
    margin: 0 0 1 0;
}

.msg-system {
    color: #64748b;
    text-style: italic;
}

OptionList {
    background: #ffffff;
    padding: 0;
    scrollbar-size: 1 1;
}

OptionList > .option-list--option {
    padding: 0 1;
    height: 1;
    color: #475569;
}

OptionList > .option-list--option-highlighted {
    background: #dbeafe;
    color: #2563eb;
}
"""

# ---------------------------------------------------------------------------
# VECTORA_SYSTEM — segue o terminal do usuário
# ---------------------------------------------------------------------------
#
# Textual não expõe "o terminal está em modo claro ou escuro" de forma
# portável (depende de `COLORFGBG`, que nem todo emulador define). Em vez de
# heurísticas frágeis, "system" reaproveita a paleta escura — é a opção mais
# segura como ponto de partida (a maioria dos terminais de desenvolvedor é
# escura) e fica pronta para, no futuro, ler `$COLORFGBG`/`$TERM_PROGRAM`
# e escolher entre DARK/LIGHT dinamicamente sem quebrar quem já depende do
# valor "system" hoje.
VECTORA_SYSTEM = VECTORA_DARK


_THEMES: dict[str, str] = {
    "dark": VECTORA_DARK,
    "light": VECTORA_LIGHT,
    "system": VECTORA_SYSTEM,
}


def get_theme_css(name: str) -> str:
    """Resolve o nome do tema (`runtime_settings.theme`) para a CSS Textual.

    Nomes desconhecidos caem em `VECTORA_DARK` — mesma postura defensiva de
    `RuntimeSettings.theme` (nunca deixa a TUI sem stylesheet por causa de
    um valor inválido em `settings.json`).
    """
    return _THEMES.get(name, VECTORA_DARK)
