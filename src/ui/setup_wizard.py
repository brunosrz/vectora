"""Setup Wizard — Configuração interativa do Vectora.

Fluxo em 3 etapas:
  1. Cohere API key  — obrigatório (embeddings + reranking RAG)
  2. Tavily API key  — obrigatório (busca web em tempo real)
  3. LLM provider    — escolha: Gemini (free), Cohere (free, usa key acima),
                       OpenAI (paid), Anthropic (paid), Ollama (local, sem key)
     └─ Ollama: pede o nome do model que o usuário já tem instalado

Ao final: testa a conexão com o LLM e lança o chat.
"""

import asyncio
import getpass
import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração dos providers de LLM
# ---------------------------------------------------------------------------
LLM_PROVIDERS: dict[str, dict[str, str]] = {
    "1": {
        "name": "Google Gemini",
        "tier": "free",
        "provider_id": "google-genai",
        "env_var": "GOOGLE_API_KEY",
        "url": "https://aistudio.google.com/app/apikey",
        "default_model": "gemini-2.5-flash",
    },
    "2": {
        "name": "Cohere",
        "tier": "free",
        "provider_id": "cohere",
        "env_var": "COHERE_API_KEY",  # mesma key já pedida no passo 1
        "url": "https://dashboard.cohere.com/api-keys",
        "default_model": "command-a-03-2025",
    },
    "3": {
        "name": "OpenAI",
        "tier": "paid",
        "provider_id": "openai",
        "env_var": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
        "default_model": "gpt-4o",
    },
    "4": {
        "name": "Anthropic Claude",
        "tier": "paid",
        "provider_id": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com/",
        "default_model": "claude-sonnet-4-6",
    },
    "5": {
        "name": "Ollama (Local)",
        "tier": "local",
        "provider_id": "ollama",
        "env_var": "",
        "url": "https://ollama.ai",
        "default_model": "",  # usuário informa o model instalado
    },
}


# ---------------------------------------------------------------------------
# Helpers de persistência
# ---------------------------------------------------------------------------


def _upsert_env_key(env_file: Path, key: str, value: str) -> None:
    """Insere ou atualiza uma KEY=value no arquivo .env."""
    lines: list[str] = []
    found = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_keys_to_env(keys: dict[str, str]) -> None:
    """Salva as API keys em ~/.vectora/.env."""
    env_file = Path.home() / ".vectora" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    for key, value in keys.items():
        if value:
            _upsert_env_key(env_file, key, value)


def _save_provider_to_settings(provider_id: str, model: str) -> None:
    """Salva provider e model ativos em ~/.vectora/settings.json."""
    from src.services.runtime_settings import runtime_settings

    runtime_settings.set_active_model(provider_id, model)
    logger.info(
        "Provider salvo",
        extra={"provider": provider_id, "model": model},
    )


# ---------------------------------------------------------------------------
# Carregamento de LLM para teste de conexão
# ---------------------------------------------------------------------------


def _load_llm_for_test(provider_id: str, model: str, api_key: str | None) -> Any:
    """Instancia o LLM correto para o teste de conexão."""
    if provider_id == "google-genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(api_key=api_key, model=model)

    if provider_id == "openai":
        from langchain_openai import ChatOpenAI  # ty: ignore[unresolved-import]

        return ChatOpenAI(api_key=api_key, model=model)

    if provider_id == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # ty: ignore[missing-argument]
            api_key=api_key,  # ty: ignore[invalid-argument-type]
            model=model,  # ty: ignore[unknown-argument]
        )

    if provider_id == "cohere":
        from langchain_cohere import ChatCohere

        # NÃO usar SecretStr — causa 401 (langchain-core str(SecretStr) → "**********")
        return ChatCohere(
            cohere_api_key=api_key,  # ty: ignore[invalid-argument-type]
            model=model,
        )

    if provider_id == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model)

    msg = f"Provider desconhecido: {provider_id}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Etapa 1 — Cohere API Key (sempre obrigatório)
# ---------------------------------------------------------------------------


async def _step_cohere_key(console: Console) -> str:
    """Coleta a Cohere API key, obrigatória para embeddings e reranking."""
    console.print(
        Rule("[bold cyan]Passo 1 de 3 — Cohere API Key[/bold cyan]", style="cyan")
    )
    console.print(
        "\n[bold]Cohere é obrigatório[/bold] — fornece os embeddings e o reranker "
        "usados pelo RAG (busca vetorial semântica).\n"
        "Plano gratuito disponível: "
        "[cyan]https://dashboard.cohere.com/api-keys[/cyan]\n"
    )

    api_key = getpass.getpass("Cohere API key (oculta): ").strip()
    if not api_key:
        console.print("[red]Cohere API key é obrigatória.[/red]")
        sys.exit(1)

    console.print("[green]✓ Cohere key recebida.[/green]\n")
    return api_key


# ---------------------------------------------------------------------------
# Etapa 2 — Tavily API Key (sempre obrigatório)
# ---------------------------------------------------------------------------


async def _step_tavily_key(console: Console) -> str:
    """Coleta a Tavily API key, obrigatória para busca web."""
    console.print(
        Rule("[bold cyan]Passo 2 de 3 — Tavily API Key[/bold cyan]", style="cyan")
    )
    console.print(
        "\n[bold]Tavily é obrigatório[/bold] — fornece busca web em tempo real "
        "e extração de conteúdo de URLs.\n"
        "Plano gratuito disponível: [cyan]https://tavily.com[/cyan]\n"
    )

    api_key = getpass.getpass("Tavily API key (oculta): ").strip()
    if not api_key:
        console.print("[red]Tavily API key é obrigatória.[/red]")
        sys.exit(1)

    console.print("[green]✓ Tavily key recebida.[/green]\n")
    return api_key


# ---------------------------------------------------------------------------
# Etapa 3 — Seleção do LLM provider
# ---------------------------------------------------------------------------


async def _step_select_llm(
    console: Console, cohere_key: str
) -> tuple[str, str, str | None]:
    """Seleciona o provider de LLM e coleta model/key.

    Returns:
        (provider_id, model, api_key_or_None)
    """
    console.print(
        Rule("[bold cyan]Passo 3 de 3 — Provider de LLM[/bold cyan]", style="cyan")
    )
    console.print("\n[bold]Escolha o modelo de linguagem:[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("#", style="dim", width=3)
    table.add_column("Provider", style="bold")
    table.add_column("Plano", style="yellow")
    table.add_column("Model padrão")

    tier_labels = {
        "free": "[green]gratuito[/green]",
        "paid": "[red]pago[/red]",
        "local": "[blue]local[/blue]",
    }
    for key, info in LLM_PROVIDERS.items():
        model_display = info["default_model"] or "[dim]você define[/dim]"
        table.add_row(key, info["name"], tier_labels[info["tier"]], model_display)

    console.print(table)
    console.print()

    # Seleção do provider
    provider_choice = None
    while provider_choice not in LLM_PROVIDERS:
        raw = (await asyncio.to_thread(input, "Escolha o provider (1-5): ")).strip()
        if raw in LLM_PROVIDERS:
            provider_choice = raw
        else:
            console.print("[red]Opção inválida. Escolha entre 1 e 5.[/red]")

    provider_info = LLM_PROVIDERS[provider_choice]
    provider_id = provider_info["provider_id"]
    console.print(f"\n[green]✓ {provider_info['name']} selecionado.[/green]\n")

    # Ollama — pede o model instalado pelo usuário
    if provider_id == "ollama":
        console.print(
            "[bold]Ollama[/bold] usa modelos que você instalou localmente.\n"
            "Execute [cyan]ollama list[/cyan] para ver os disponíveis.\n"
            "Exemplos: [dim]llama3:8b  mistral  codellama  qwen2.5:7b[/dim]\n"
        )
        model = (await asyncio.to_thread(input, "Nome do model Ollama: ")).strip()
        if not model:
            console.print("[red]Nome do model é obrigatório para Ollama.[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Model: {model}[/green]\n")
        return provider_id, model, None

    # Cohere como LLM — reutiliza a key já coletada no passo 1
    if provider_id == "cohere":
        console.print("[dim]Reutilizando a Cohere API key do passo 1.[/dim]\n")
        return provider_id, provider_info["default_model"], cohere_key

    # Demais providers — pede API key
    console.print(
        f"[bold]{provider_info['name']} API key:[/bold]\n"
        f"[cyan]{provider_info['url']}[/cyan]\n"
    )
    api_key = getpass.getpass(f"{provider_info['name']} API key (oculta): ").strip()
    if not api_key:
        console.print(f"[red]API key é obrigatória para {provider_info['name']}.[/red]")
        sys.exit(1)

    console.print(f"[green]✓ {provider_info['name']} key recebida.[/green]\n")
    return provider_id, provider_info["default_model"], api_key


# ---------------------------------------------------------------------------
# Teste de conexão
# ---------------------------------------------------------------------------


async def _test_connection(
    console: Console,
    provider_id: str,
    model: str,
    api_key: str | None,
) -> None:
    """Testa a conexão com o LLM escolhido."""
    console.print("[bold]Testando conexão...[/bold]\n")

    try:
        llm = _load_llm_for_test(provider_id, model, api_key)

        with console.status(
            "[bold cyan]Conectando ao LLM...[/bold cyan]", spinner="dots"
        ):
            response = await llm.ainvoke("Say 'Connected!' in one word.")

        console.print(
            Panel(
                f"[green]✓ Conexão bem-sucedida![/green]\n"
                f"[cyan]Resposta: {response.content}[/cyan]",
                title="[bold green]Teste de Conexão[/bold green]",
                style="green",
                expand=False,
            )
        )
        console.print()

    except Exception as exc:
        console.print(
            Panel(
                f"[red]{exc!s}[/red]",
                title="[bold red]✗ Conexão Falhou[/bold red]",
                style="red",
            )
        )
        logger.exception("Teste de conexão falhou")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------


async def run_setup() -> None:
    """Executa o wizard completo de configuração."""
    console = Console()

    console.print(
        Panel(
            "[bold cyan]Vectora Setup Wizard[/bold cyan]\n"
            "[dim]Configure suas API keys e escolha o LLM provider[/dim]",
            style="bold blue",
            expand=False,
        )
    )
    console.print()

    # Passo 1 — Cohere (sempre obrigatório)
    cohere_key = await _step_cohere_key(console)

    # Passo 2 — Tavily (sempre obrigatório)
    tavily_key = await _step_tavily_key(console)

    # Passo 3 — LLM provider
    provider_id, model, llm_api_key = await _step_select_llm(console, cohere_key)

    # Teste de conexão com o LLM
    await _test_connection(console, provider_id, model, llm_api_key)

    # Salvar keys em ~/.vectora/.env
    keys_to_save: dict[str, str] = {
        "COHERE_API_KEY": cohere_key,
        "TAVILY_API_KEY": tavily_key,
    }
    if llm_api_key and provider_id != "cohere":
        env_var = next(
            (
                v["env_var"]
                for v in LLM_PROVIDERS.values()
                if v["provider_id"] == provider_id
            ),
            "",
        )
        if env_var:
            keys_to_save[env_var] = llm_api_key

    _save_keys_to_env(keys_to_save)
    _save_provider_to_settings(provider_id, model)

    console.print(
        Panel(
            "[green]✓ Configuração salva em ~/.vectora/.env[/green]",
            title="[bold]Setup Completo[/bold]",
            style="green",
            expand=False,
        )
    )
    console.print()
    console.print(Rule("[bold cyan]Iniciando Vectora Chat[/bold cyan]", style="cyan"))
    console.print()

    from src.ui.chat import run_chat

    await run_chat()


def run_setup_sync() -> None:
    """Entry point síncrono para o setup wizard."""
    asyncio.run(run_setup())


if __name__ == "__main__":
    run_setup_sync()
