"""Pipeline de referência: webhook `pull_request.opened` → diff → comentário.

Percorre o caminho real de tool-calling (`langchain.agents.create_agent` +
tools de produção `github_fetch_pr_diff`/`github_post_pr_comment`), com um
``BaseChatModel`` real (não um mock do agente inteiro — CLAUDE.md/plano:
"testa o pipeline, não a qualidade do LLM") que decide os tool calls a
partir do mesmo payload embutido no prompt por
``background_tasks.run_task``. Só a chamada HTTP real ao GitHub é mockada.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from backend.tools.github import github_fetch_pr_diff, github_post_pr_comment

_PR_PAYLOAD = {
    "action": "opened",
    "number": 42,
    "pull_request": {
        "number": 42,
        "title": "Corrige loop de erro no worker de embedding",
        "diff_url": "https://github.com/vectora-labs/vectora/pull/42.diff",
        "html_url": "https://github.com/vectora-labs/vectora/pull/42",
    },
    "repository": {"full_name": "vectora-labs/vectora"},
}


def _tool_result(message: ToolMessage) -> dict[str, Any]:
    """As tools deste módulo sempre devolvem uma string JSON — nunca a
    forma multimodal (`list`) que `ToolMessage.content` também permite."""
    assert isinstance(message.content, str)
    return json.loads(message.content)


def _build_prompt(payload: dict[str, Any]) -> str:
    """Mesma construção de `run_task` (background_tasks.py) — payload
    truncado a 4000 chars embutido como bloco JSON na instrução."""
    base = "Revise o Pull Request e comente com observações objetivas."
    evt = json.dumps(payload, ensure_ascii=False)[:4000]
    return f"{base}\n\n## Evento recebido\n```json\n{evt}\n```"


class _ScriptedReviewerModel(BaseChatModel):
    """BaseChatModel real que decide os 2 tool calls a partir do payload,
    igual a um LLM real leria o JSON embutido no prompt — só a sequência é
    scriptada para o teste ser determinístico (não a qualidade do texto)."""

    model_config = {"arbitrary_types_allowed": True}
    payload: dict[str, Any]
    tools_bound: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-reviewer"

    def bind_tools(self, tools, **kwargs):
        self.tools_bound = list(tools)
        return self

    async def _agenerate(
        self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ) -> ChatResult:
        repo_full = self.payload["repository"]["full_name"]
        owner, repo = repo_full.split("/", 1)
        pr_number = self.payload["pull_request"]["number"]

        diff_result_msg = next(
            (
                m
                for m in messages
                if isinstance(m, ToolMessage) and m.name == "github_fetch_pr_diff"
            ),
            None,
        )
        has_comment_result = any(
            isinstance(m, ToolMessage) and m.name == "github_post_pr_comment"
            for m in messages
        )
        diff_failed = diff_result_msg is not None and (
            _tool_result(diff_result_msg).get("status") == "error"
        )

        if diff_failed:
            # LLM real leria o erro tipado da tool e pararia de tentar
            # comentar num PR cujo diff não conseguiu buscar.
            msg = AIMessage(content="Não consegui buscar o diff do PR — parando aqui.")
        elif diff_result_msg is None:
            msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "github_fetch_pr_diff",
                        "args": {"owner": owner, "repo": repo, "pr_number": pr_number},
                        "id": "call_diff",
                    }
                ],
            )
        elif not has_comment_result:
            msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "github_post_pr_comment",
                        "args": {
                            "owner": owner,
                            "repo": repo,
                            "pr_number": pr_number,
                            "body": "Revisado — sem observações bloqueantes.",
                        },
                        "id": "call_comment",
                    }
                ],
            )
        else:
            msg = AIMessage(content="Revisão concluída.")

        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise NotImplementedError  # só o caminho async é exercitado aqui


def _mock_httpx(diff_response: MagicMock, comment_response: MagicMock):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_ctx.get = AsyncMock(return_value=diff_response)
    mock_ctx.post = AsyncMock(return_value=comment_response)
    return mock_ctx


@pytest.mark.asyncio
async def test_pull_request_opened_busca_diff_e_comenta_com_argumentos_corretos(
    monkeypatch,
):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")

    diff_response = MagicMock()
    diff_response.status_code = 200
    diff_response.text = "diff --git a/backend/embedding/background.py ..."

    comment_response = MagicMock()
    comment_response.status_code = 201
    comment_response.json.return_value = {
        "html_url": "https://github.com/vectora-labs/vectora/pull/42#issuecomment-1"
    }

    model = _ScriptedReviewerModel(payload=_PR_PAYLOAD)
    agent = create_agent(model, [github_fetch_pr_diff, github_post_pr_comment])

    prompt = _build_prompt(_PR_PAYLOAD)

    mock_ctx = _mock_httpx(diff_response, comment_response)
    with patch("httpx.AsyncClient", return_value=mock_ctx):
        result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})

    # A tool de diff e a de comentário foram chamadas com owner/repo/PR
    # number extraídos do payload — confirmado pelas URLs reais batidas.
    diff_url = mock_ctx.get.call_args.args[0]
    assert diff_url == "https://api.github.com/repos/vectora-labs/vectora/pulls/42"
    comment_url = mock_ctx.post.call_args.args[0]
    assert (
        comment_url
        == "https://api.github.com/repos/vectora-labs/vectora/issues/42/comments"
    )

    messages = result["messages"]
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 2

    diff_result = _tool_result(tool_messages[0])
    assert diff_result["status"] == "ok"
    assert "background.py" in diff_result["diff"]

    comment_result = _tool_result(tool_messages[1])
    assert comment_result["status"] == "ok"
    assert "issuecomment-1" in comment_result["comment_url"]

    final = messages[-1]
    assert isinstance(final, AIMessage)
    assert final.tool_calls == []


@pytest.mark.asyncio
async def test_erro_ao_buscar_diff_nao_derruba_o_agente_nem_chama_comentario(
    monkeypatch,
):
    """Erro/borda: diff falha (repo/PR inexistente) — o agente recebe o erro
    tipado da tool (nunca uma exceção) e não avança pro comentário."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")

    diff_response = MagicMock()
    diff_response.status_code = 404
    diff_response.text = "Not Found"

    model = _ScriptedReviewerModel(payload=_PR_PAYLOAD)
    agent = create_agent(model, [github_fetch_pr_diff, github_post_pr_comment])
    prompt = _build_prompt(_PR_PAYLOAD)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_ctx.get = AsyncMock(return_value=diff_response)
    mock_ctx.post = AsyncMock(side_effect=AssertionError("não deveria comentar"))

    with patch("httpx.AsyncClient", return_value=mock_ctx):
        result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    diff_result = _tool_result(tool_messages[0])
    assert diff_result["status"] == "error"
    assert "404" in diff_result["error"]
