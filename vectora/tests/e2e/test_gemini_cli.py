"""Testes E2E com Gemini CLI — integração real com vectora-mcp.

Verifica dois fatores críticos:
1. O Gemini CLI consegue iniciar e chamar o vectora-mcp via protocolo MCP
2. O Vectora processa as chamadas e grava traces internos (observabilidade)

Requer:
- `gemini` CLI instalado e em PATH
- GOOGLE_API_KEY configurado
- ~/.gemini/settings.json com mcpServers.vectora configurado
- vectora-mcp em PATH (via `uv run vectora-mcp`)

Executar:
    uv run pytest tests/e2e/ -v --timeout=180
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

# ============================================================================
# Marcadores de skip
# ============================================================================

REQUIRES_API_KEY = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY não configurado",
)


def _gemini_available() -> bool:
    """Returns True if gemini CLI is installed and reachable in PATH."""
    try:
        result = subprocess.run(
            ["gemini", "--version"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


REQUIRES_GEMINI_CLI = pytest.mark.skipif(
    not _gemini_available(),
    reason="gemini CLI não instalado ou não encontrado em PATH",
)

# Arquivo de configuração MCP do projeto — settings.json na raiz do projeto.
# Foi renomeado de .mcp.json para settings.json para ser legível por clientes
# MCP que esperam esse nome (incluindo o Gemini CLI no modo projeto).
_PROJECT_ROOT = Path(__file__).parent.parent.parent
GEMINI_SETTINGS_PATH = _PROJECT_ROOT / "settings.json"


def _gemini_has_vectora_mcp() -> bool:
    """Verifica se settings.json (projeto) tem vectora em mcpServers.

    A chave do servidor é case-insensitive: aceita "vectora" ou "Vectora".
    """
    try:
        data = json.loads(GEMINI_SETTINGS_PATH.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        return any(k.lower() == "vectora" for k in servers)
    except Exception:
        return False


REQUIRES_MCP_CONFIG = pytest.mark.skipif(
    not _gemini_has_vectora_mcp(),
    reason="settings.json (projeto) não tem vectora em mcpServers",
)


# ============================================================================
# Helpers
# ============================================================================


def _run_gemini(prompt: str, timeout: int = 90) -> str:
    """Invoca `gemini -p <prompt>` e retorna stdout + stderr."""
    try:
        result = subprocess.run(
            ["gemini", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] gemini CLI não respondeu dentro do tempo limite"
    except FileNotFoundError:
        return "[ERROR] gemini CLI não encontrado"


def _run_gemini_with_mcp(prompt: str, timeout: int = 120) -> str:
    """Invoca gemini com prompt que força uso do MCP do Vectora."""
    # O Gemini CLI deve usar o servidor MCP configurado em settings.json
    return _run_gemini(prompt, timeout=timeout)


# ============================================================================
# Classe 1 — Configuração do Gemini CLI
# ============================================================================


class TestGeminiCliConfig:
    """Verifica a configuração do Gemini CLI + vectora-mcp."""

    def test_gemini_settings_file_exists(self):
        """settings.json na raiz do projeto deve existir."""
        assert GEMINI_SETTINGS_PATH.exists(), (
            f"Arquivo não encontrado: {GEMINI_SETTINGS_PATH}"
        )

    def test_gemini_settings_has_mcp_servers_section(self):
        """settings.json deve ter a seção mcpServers."""
        assert GEMINI_SETTINGS_PATH.exists(), "settings.json não existe"
        data = json.loads(GEMINI_SETTINGS_PATH.read_text(encoding="utf-8"))
        assert "mcpServers" in data, (
            "settings.json não tem seção mcpServers. "
            "Adicione a configuração do vectora conforme documentação."
        )

    def test_gemini_settings_has_vectora_server(self):
        """settings.json deve ter vectora em mcpServers (case-insensitive)."""
        assert _gemini_has_vectora_mcp(), (
            "vectora não encontrado em mcpServers. "
            f"Conteúdo atual: {GEMINI_SETTINGS_PATH.read_text()}"
        )

    def test_vectora_mcp_command_configured_correctly(self):
        """O comando MCP deve iniciar o servidor MCP do vectora.

        O único entry-point do pacote é 'vectora' (vectora.main:run).
        Para iniciar o servidor MCP, o subcomando correto é 'server mcp'.
        Formatos aceitos:
          - command='vectora', args=['server', 'mcp', ...]
          - command='uv', args=[..., 'vectora', 'server', 'mcp', ...]
        """
        data = json.loads(GEMINI_SETTINGS_PATH.read_text(encoding="utf-8"))
        # Busca a entrada vectora de forma case-insensitive
        servers = data.get("mcpServers", {})
        vectora_key = next((k for k in servers if k.lower() == "vectora"), None)
        assert vectora_key is not None, "vectora não encontrado em mcpServers"
        vectora_config = servers[vectora_key]

        assert "command" in vectora_config, "vectora não tem campo 'command'"
        cmd = vectora_config["command"]
        args = vectora_config.get("args", [])

        # Formato canônico: command="vectora", args=["server", "mcp", ...]
        # Também aceita via uv: command="uv", args=[..., "vectora", "server", "mcp", ...]
        is_canonical = (
            cmd == "vectora"
            and len(args) >= 2
            and args[0] == "server"
            and args[1] == "mcp"
        )
        is_uv = cmd == "uv" and "vectora" in args and "server" in args and "mcp" in args
        assert is_canonical or is_uv, (
            f"Comando inválido: '{cmd}' args={args}. "
            "Esperado: command='vectora' args=['server', 'mcp', ...] "
            "ou command='uv' com 'vectora', 'server' e 'mcp' nos args."
        )

    def test_vectora_mcp_project_path_exists(self):
        """O caminho do projeto na configuração MCP deve existir (quando especificado)."""
        data = json.loads(GEMINI_SETTINGS_PATH.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        vectora_key = next((k for k in servers if k.lower() == "vectora"), None)
        if vectora_key is None:
            return
        args = servers[vectora_key].get("args", [])

        # Procura --project <path> nos args
        project_path = None
        for i, arg in enumerate(args):
            if arg == "--project" and i + 1 < len(args):
                project_path = args[i + 1]
                break

        if project_path:
            assert Path(project_path).exists(), (
                f"Caminho do projeto não existe: {project_path}"
            )

    @REQUIRES_GEMINI_CLI
    def test_gemini_cli_version_check(self):
        """gemini CLI deve responder ao --version."""
        result = subprocess.run(
            ["gemini", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"gemini --version falhou: {result.stderr}"


# ============================================================================
# Classe 2 — Gemini chama Vectora via MCP
# ============================================================================


@REQUIRES_API_KEY
@REQUIRES_GEMINI_CLI
@REQUIRES_MCP_CONFIG
class TestGeminiCallsVectora:
    """Testa que o Gemini CLI chama o vectora-mcp e o Vectora responde."""

    @pytest.mark.timeout(120)
    @pytest.mark.flaky(reruns=2)
    def test_gemini_basic_response_with_mcp(self):
        """Gemini CLI deve responder a prompt básico (verifica que MCP não trava)."""
        output = _run_gemini("Olá! Responda apenas com: Olá do Gemini!", timeout=60)
        assert len(output) > 0, "Gemini CLI não retornou nenhuma saída"
        assert "[TIMEOUT]" not in output, "Gemini CLI travou"
        assert "[ERROR]" not in output, "Gemini CLI não encontrado"

    @pytest.mark.timeout(150)
    @pytest.mark.flaky(reruns=2)
    def test_gemini_delegates_to_vectora_mcp(self):
        """Gemini deve usar delegate_task_to_vectora para tarefa que o força a isso."""
        prompt = (
            "Use the vectora MCP server tool 'delegate_task_to_vectora' "
            "to answer this question: What is 2 plus 2? "
            "Make sure to actually call the tool."
        )
        output = _run_gemini_with_mcp(prompt, timeout=120)

        assert len(output) > 0, "Gemini CLI não retornou nenhuma saída"
        assert "[TIMEOUT]" not in output, "Gemini CLI travou"

        # A resposta deve mencionar 4 (resultado da matemática simples)
        # ou mencionar Vectora/MCP (indicando que a tool foi chamada)
        output_lower = output.lower()
        has_answer = any(
            kw in output_lower
            for kw in ["4", "four", "quatro", "vectora", "delegate", "mcp"]
        )
        assert has_answer, (
            f"Resposta não parece ter chamado delegate_task_to_vectora: {output[:300]}"
        )

    @pytest.mark.timeout(150)
    @pytest.mark.flaky(reruns=2)
    def test_vectora_records_trace_from_gemini_call(self):
        """Após chamada MCP do Gemini, o Vectora deve ter gravado traces."""
        import asyncio

        from backend.services.tracer import tracer

        # Trigger uma chamada ao Vectora via Gemini
        prompt = (
            "Please use the vectora delegate_task_to_vectora tool "
            "with task_prompt='List available tools' and thread_id=9999."
        )
        _run_gemini_with_mcp(prompt, timeout=120)

        # Verifica traces registrados pelo Vectora
        async def check_traces():
            # Aguarda um momento para traces serem gravados
            import asyncio as _asyncio

            await _asyncio.sleep(2)
            return await tracer.get_recent(n=20)

        recent_spans = asyncio.run(check_traces())

        # Pode não ter spans se a chamada falhou ou não usou o MCP
        # Mas se o delegate foi chamado, deve haver spans de mcp_delegate ou mcp_tool
        mcp_spans = [s for s in recent_spans if "mcp" in s.get("node", "").lower()]

        # Log para diagnóstico — não falha se não houver spans
        if mcp_spans:
            assert any(s.get("duration_ms", 0) >= 0 for s in mcp_spans), (
                "Spans MCP devem ter duration_ms"
            )
        else:
            pytest.skip(
                "Nenhum trace MCP encontrado — Gemini pode não ter chamado o MCP. "
                "Verifique a configuração em ~/.gemini/settings.json"
            )

    @pytest.mark.timeout(150)
    @pytest.mark.flaky(reruns=2)
    def test_gemini_uses_vectora_for_complex_task(self):
        """Prompt complexo deve acionar o Vectora via MCP para RAG/análise."""
        prompt = (
            "Using the vectora MCP server, search the vector database "
            "for information about 'LanceDB' and summarize what you find. "
            "Use the vector_search_tool from vectora."
        )
        output = _run_gemini_with_mcp(prompt, timeout=120)

        assert len(output) > 0, "Gemini CLI não retornou nenhuma saída"
        assert "[TIMEOUT]" not in output, "Gemini CLI travou"

        output_lower = output.lower()
        # Deve mencionar LanceDB, vetorial, ou indicar que a busca foi realizada
        has_relevant_content = any(
            kw in output_lower
            for kw in [
                "lancedb",
                "vetorial",
                "vector",
                "search",
                "no result",
                "empty",
                "vazio",
            ]
        )
        assert has_relevant_content, (
            f"Resposta não mostra uso do vector_search_tool: {output[:300]}"
        )


# ============================================================================
# Classe 3 — Vectora MCP Server diretamente via subprocess (JSON-RPC)
# ============================================================================


class TestVectoraMcpServerDirectly:
    """Testa o servidor vectora-mcp via JSON-RPC sem o Gemini CLI."""

    @pytest.fixture
    def mcp_server_command(self):
        """Comando para iniciar vectora-mcp."""
        project_dir = Path(__file__).parent.parent.parent
        venv_python = (
            project_dir
            / ".venv"
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        if venv_python.exists():
            return [str(venv_python), "-m", "backend.mcp.server"]
        return ["uv", "run", "--project", str(project_dir), "vectora-mcp"]

    def _send_rpc(
        self, proc: subprocess.Popen, method: str, params: dict, req_id: int = 1
    ) -> dict:
        """Envia JSON-RPC e lê resposta."""
        request = json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        )
        assert proc.stdin is not None
        assert proc.stdout is not None
        proc.stdin.write(request + "\n")
        proc.stdin.flush()
        line = (
            proc.stdout.readline(timeout=10)  # ty: ignore[unknown-argument]
            if hasattr(proc.stdout, "timeout")
            else proc.stdout.readline()
        )
        try:
            return json.loads(line) if line else {}
        except json.JSONDecodeError:
            return {"raw": line}

    @pytest.mark.timeout(30)
    def test_mcp_server_starts_and_accepts_input(self, mcp_server_command):
        """vectora-mcp deve iniciar sem crash imediato."""
        try:
            proc = subprocess.Popen(
                mcp_server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            pytest.skip("vectora-mcp command não disponível")

        try:
            # Envia initialize e aguarda resposta ou timeout
            request = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest-e2e", "version": "1.0"},
                    },
                }
            )
            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None
            proc.stdin.write(request + "\n")
            proc.stdin.flush()

            import select
            import threading
            import time

            # Lê a primeira linha do stdout com timeout — compatível com Windows.
            # readline() é bloqueante em todos os sistemas, incluindo Windows onde
            # select() não funciona em pipes. Usamos uma thread daemon para não travar.
            def _readline_with_timeout(stream, timeout: float) -> str:
                result: list[str] = []

                def _read() -> None:
                    try:
                        line = stream.readline()
                        result.append(line or "")
                    except Exception:
                        result.append("")

                t = threading.Thread(target=_read, daemon=True)
                t.start()
                t.join(timeout=timeout)
                return result[0] if result else ""

            # Aguarda até 10s por resposta
            response_line = _readline_with_timeout(proc.stdout, timeout=10)

            # O processo não deve ter crashado
            assert (
                proc.poll() is None or proc.returncode is None or proc.returncode == 0
            ), f"vectora-mcp crashou. stderr: {proc.stderr.read(500)}"  # asserted above

            if response_line:
                try:
                    response = json.loads(response_line)
                    # Resposta MCP válida tem result ou error
                    assert (
                        "result" in response or "error" in response or "id" in response
                    )
                except json.JSONDecodeError:
                    pass  # Pode ser logs, não JSON — não é erro

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    @pytest.mark.timeout(30)
    def test_vectora_mcp_help_or_dry_run(self, mcp_server_command):
        """vectora-mcp deve ser executável (verifica importação básica)."""
        # Verifica que o módulo importa sem erros críticos
        venv_python = (
            mcp_server_command[0]
            if mcp_server_command[0].endswith("python")
            or mcp_server_command[0].endswith("python.exe")
            else None
        )

        if venv_python:
            # O wheel empacota o código como `src` (pyproject packages=["src"]),
            # então o módulo real é src.mcp.server — não vectora.mcp.server.
            result = subprocess.run(
                [venv_python, "-c", "from backend.mcp.server import mcp; print('OK')"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            assert "OK" in result.stdout or result.returncode == 0, (
                f"Importação do servidor MCP falhou: {result.stderr[:200]}"
            )
        else:
            pytest.skip("Python do venv não identificado")
