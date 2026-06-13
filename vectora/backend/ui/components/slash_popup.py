"""Opções do popup de autocomplete `/comando` (`#command-popup`).

Pura transformação de "texto digitado + lista de comandos" -> `list[Option]`,
sem tocar em widgets montados — só o `OptionList` consome o resultado. Função
isolada para testar o algoritmo de filtragem (prefixo de comando / nome de
modelo) sem precisar montar a App inteira.
"""

from __future__ import annotations

from textual.widgets.option_list import Option


def build_popup_options(
    text: str, slash_commands: list[tuple[str, str]]
) -> list[Option]:
    """Constrói as opções do popup a partir do texto digitado.

    - ``"/"`` ou ``"/cmd"``           -> comandos de `slash_commands` que
      começam com o texto (autocomplete genérico).
    - ``"/model "`` ou ``"/model <prefixo>"`` -> modelos de
      `AVAILABLE_MODELS` cujo nome contém o prefixo (case-insensitive).
    """
    from backend.settings import AVAILABLE_MODELS

    stripped = text.rstrip()
    if stripped == "/model" or text.startswith("/model "):
        prefix = text[len("/model ") :].strip().lower() if " " in text else ""
        opts: list[Option] = []
        for provider, models in AVAILABLE_MODELS.items():
            for model in models:
                if not prefix or prefix in model.lower():
                    label = f" [b]{model:<32}[/b] [dim]{provider}[/dim]"
                    opts.append(Option(label, id=f"/model {model}"))
        return opts

    return [
        Option(f" {cmd:<14}  {desc}", id=cmd)
        for cmd, desc in slash_commands
        if cmd.startswith(text)
    ]
