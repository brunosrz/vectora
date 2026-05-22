"""/model command — list and switch LLM models."""

import asyncio
import getpass
import logging
import os
from typing import Any

from rich.panel import Panel
from rich.table import Table

from vectora.services.runtime_settings import runtime_settings
from vectora.ui.commands._shared import (
    AVAILABLE_MODELS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_COLOR,
    PROVIDER_DISPLAY,
    PROVIDER_KEY_URL,
    apply_model_change,
    find_provider_for_model,
    has_api_key,
    save_api_key_to_env,
)
from vectora.ui.main import SuccessPanel

logger = logging.getLogger(__name__)


async def prompt_for_api_key(provider: str, key_env: str, console: Any) -> str | None:
    """Solicita a API key do provider inline no chat.

    Retorna a chave digitada, ou None se o usuário cancelar.
    """
    display = PROVIDER_DISPLAY.get(provider, provider)
    url = PROVIDER_KEY_URL.get(provider, "")

    body = (
        f"[yellow] Chave API do {display} não configurada.[/yellow]\n\n"
        f"Variável necessária: [bold]{key_env}[/bold]\n"
    )
    if url:
        body += f"Obtenha sua chave em: [cyan]{url}[/cyan]\n"
    body += "\n[dim]Digite a chave abaixo (Enter em branco para cancelar).[/dim]"

    console.print(
        Panel(
            body,
            title=f"[bold yellow]🔑 API Key — {display}[/bold yellow]",
            border_style="yellow",
        )
    )

    try:
        key = await asyncio.to_thread(getpass.getpass, f"  {display} API key: ")
    except KeyboardInterrupt, EOFError:
        console.print("[dim]Cancelado.[/dim]")
        return None

    key = key.strip()
    if not key:
        console.print("[dim]Cancelado — nenhuma chave fornecida.[/dim]")
        return None

    return key


def display_all_models(console: Any) -> None:
    """Exibe tabela com todos os modelos de todos os providers."""
    active_provider = runtime_settings.active_provider
    active_model = runtime_settings.active_model

    table = Table(
        title="Modelos Disponíveis",
        style="cyan",
        show_lines=False,
        expand=False,
    )
    table.add_column("Provider", style="bold", width=14, no_wrap=True)
    table.add_column("Modelo", width=32, no_wrap=True)
    table.add_column("Chave", justify="center", width=7)
    table.add_column("Status", width=12)

    for provider, models in AVAILABLE_MODELS.items():
        has_key = has_api_key(provider)
        key_icon = "[green]✓[/green]" if has_key else "[red]✗[/red]"
        color = PROVIDER_COLOR.get(provider, "white")

        for i, model in enumerate(models):
            is_active = provider == active_provider and model == active_model
            provider_cell = (
                f"[{color}]{PROVIDER_DISPLAY.get(provider, provider)}[/{color}]"
                if i == 0
                else ""
            )
            model_cell = f"[bold green]{model}[/bold green]" if is_active else model
            key_cell = key_icon if i == 0 else ""
            status_cell = (
                "[bold green]◉ ativo[/bold green]"
                if is_active
                else ("[dim]sem chave[/dim]" if (i == 0 and not has_key) else "")
            )
            table.add_row(provider_cell, model_cell, key_cell, status_cell)

    console.print(Panel(table, border_style="cyan", expand=False))
    console.print(
        "[dim]Use [bold]/model <nome>[/bold] para trocar. "
        "Ex: [bold]/model gemini-2.5-flash[/bold] ou [bold]/model command-a-03-2025[/bold][/dim]"
    )


async def handle_model_command(args: str, console: Any) -> None:
    """Handle /model command — list all models or switch to the specified one.

    Without args: shows table with all providers and models.
    With args: switches to the model (any provider), prompting for API key if needed.
    """
    if not args.strip():
        display_all_models(console)
        return

    new_model = args.strip()
    provider = find_provider_for_model(new_model)

    if provider is None:
        console.print(f"[red]Modelo '[bold]{new_model}[/bold]' não encontrado.[/red]")
        console.print(
            "[dim]Use [bold]/model[/bold] para ver todos os modelos disponíveis.[/dim]"
        )
        return

    key_env = PROVIDER_API_KEY_ENV.get(provider)
    if key_env and not has_api_key(provider):
        key = await prompt_for_api_key(provider, key_env, console)
        if not key:
            return

        save_api_key_to_env(key_env, key)
        os.environ[key_env] = key
        console.print(
            f"[green]✓ Chave {key_env} configurada e salva em ~/.vectora/.env[/green]"
        )

    try:
        apply_model_change(provider, new_model)
        display = PROVIDER_DISPLAY.get(provider, provider)
        console.print(
            SuccessPanel.render(
                f"Modelo ativo: [bold]{new_model}[/bold]  ({display})\n"
                "[dim]Próxima mensagem usará o novo modelo.[/dim]"
            )
        )
        logger.info("Model changed: provider=%s model=%s", provider, new_model)
    except Exception as e:
        console.print(f"[red]Erro ao trocar modelo: {e}[/red]")
        logger.exception("Failed to apply model change")


# Backward-compat aliases
_prompt_for_api_key = prompt_for_api_key
_display_all_models = display_all_models
_handle_model_command = handle_model_command
