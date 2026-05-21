"""Tests for vectora/agents/supervisor.py"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from vectora.agents.supervisor import classify_intent, supervisor

if TYPE_CHECKING:
    from vectora.state import State

# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------


class TestClassifyIntent:
    def test_direct_greeting(self):
        for text in ("oi", "olá", "hello", "hi", "bom dia", "boa tarde"):
            assert classify_intent(text) == "direct", f"failed for: {text}"

    def test_direct_thanks(self):
        assert classify_intent("obrigado") == "direct"
        assert classify_intent("valeu") == "direct"

    def test_direct_who_are_you(self):
        assert classify_intent("quem é você") == "direct"
        assert classify_intent("o que você faz") == "direct"

    def test_direct_short_fallback(self):
        assert classify_intent("ok") == "direct"

    def test_coder_file_operations(self):
        assert classify_intent("cria um arquivo main.py") == "coder"
        assert classify_intent("edita o script") == "coder"

    def test_coder_git(self):
        assert classify_intent("rode git commit -m 'fix'") == "coder"
        assert classify_intent("git status do projeto") == "coder"

    def test_coder_terminal(self):
        assert classify_intent("executa npm install no terminal") == "coder"
        assert classify_intent("instala o pacote via pip") == "coder"

    def test_search_web_explicit(self):
        assert classify_intent("busca na web sobre Python 3.14") == "search"
        assert classify_intent("pesquisa na internet por notícias") == "search"

    def test_rag_document(self):
        assert classify_intent("o que diz o documento sobre JWT?") == "rag"
        assert classify_intent("busque na base de conhecimento") == "rag"

    def test_rag_de_acordo_com(self):
        assert (
            classify_intent("de acordo com a documentação, como configurar?") == "rag"
        )

    def test_long_question_fallback_is_now_direct(self):
        # Fase 1: fallback mudou de rag → direct para evitar RAG como universal fallback
        result = classify_intent("explique como funciona a arquitetura do sistema?")
        assert result == "direct"

    def test_general_knowledge_goes_to_direct(self):
        assert classify_intent("qual é a capital da França?") == "direct"
        assert classify_intent("quanto é 2 mais 2?") == "direct"
        assert classify_intent("me explica o que é um transformer") == "direct"

    # --- Fase 1: Identity patterns → direct (nunca RAG/web) ---

    def test_identity_name_goes_to_direct(self):
        assert classify_intent("meu nome é Bruno Soares") == "direct"
        assert classify_intent("me chamo Bruno") == "direct"

    def test_identity_creator_claim_goes_to_direct(self):
        assert classify_intent("sou o criador do Vectora") == "direct"
        assert classify_intent("sou o desenvolvedor do sistema") == "direct"
        assert classify_intent("eu sou o bruno, lembra de mim?") == "direct"

    def test_identity_recognition_request_goes_to_direct(self):
        assert classify_intent("você me conhece?") == "direct"
        assert classify_intent("lembra de mim?") == "direct"
        assert classify_intent("me reconhece?") == "direct"

    def test_identity_full_phrase_goes_to_direct(self):
        # Frase exata que causou o bug reportado pelo usuário
        result = classify_intent(
            "Meu nome e bruno soares, lembra de mim? eu sou seu criador"
        )
        assert result == "direct"

    # --- Fase 1: URL patterns → search (fetch_url) ---

    def test_explicit_url_goes_to_search(self):
        assert classify_intent("https://www.linkedin.com/in/bruno-soares/") == "search"
        assert classify_intent("http://example.com/page") == "search"

    def test_url_embedded_in_text_goes_to_search(self):
        assert (
            classify_intent("acessa esse link: https://github.com/brunosrz/vectora")
            == "search"
        )

    def test_url_github_goes_to_search(self):
        assert classify_intent("https://github.com/brunosrz/vectora") == "search"

    # --- Fase 1: File path patterns → coder (filesystem) ---

    def test_windows_filepath_goes_to_coder(self):
        assert classify_intent(r"C:\Users\Machi\Desktop\vectora\cv.md") == "coder"
        assert (
            classify_intent(r"C:\Users\Machi\Desktop\vectora\vectora\agent.py")
            == "coder"
        )

    def test_unix_filepath_goes_to_coder(self):
        assert classify_intent("/home/user/documents/resume.pdf") == "coder"
        assert classify_intent("/Users/bruno/project/main.py") == "coder"

    def test_home_relative_filepath_goes_to_coder(self):
        assert classify_intent("~/projects/vectora/README.md") == "coder"

    def test_filepath_in_context_goes_to_coder(self):
        assert (
            classify_intent(r"leia esse arquivo: C:\Users\Machi\Desktop\cv.md")
            == "coder"
        )

    # --- RAG keywords ainda funcionam ---

    def test_rag_according_to_docs(self):
        assert classify_intent("de acordo com os documentos indexados") == "rag"

    def test_rag_documentation(self):
        assert classify_intent("na documentacao do projeto") == "rag"
        assert classify_intent("na documentação do sistema") == "rag"

    def test_rag_knowledge_base(self):
        assert classify_intent("busque na base de conhecimento") == "rag"


# ---------------------------------------------------------------------------
# supervisor node
# ---------------------------------------------------------------------------


class TestSupervisor:
    @pytest.mark.asyncio
    async def test_greeting_routes_to_direct(self):
        state: State = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }
        cmd = await supervisor(state)
        assert isinstance(cmd, Command)
        assert cmd.goto == "direct"
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "direct"

    @pytest.mark.asyncio
    async def test_coder_routes_to_coder(self):
        state: State = {
            "messages": [HumanMessage(content="cria um arquivo main.py")],
            "session_metadata": {},
        }
        cmd = await supervisor(state)
        assert cmd.goto == "coder"
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "coder"

    @pytest.mark.asyncio
    async def test_rag_routes_to_rag_subgraph(self):
        state: State = {
            "messages": [HumanMessage(content="o que diz o documento sobre auth?")],
            "session_metadata": {},
        }
        cmd = await supervisor(state)
        assert cmd.goto == "rag_subgraph"
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "rag"

    @pytest.mark.asyncio
    async def test_uses_last_human_message(self):
        state: State = {
            "messages": [
                HumanMessage(content="o que diz o documento?"),  # → rag
                AIMessage(content="Resposta"),
                HumanMessage(content="oi"),  # → direct (última)
            ],
            "session_metadata": {},
        }
        cmd = await supervisor(state)
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "direct"

    @pytest.mark.asyncio
    async def test_empty_messages_defaults_to_direct(self):
        state: State = {"messages": [], "session_metadata": {}}
        cmd = await supervisor(state)
        assert cmd.goto == "direct"

    @pytest.mark.asyncio
    async def test_no_human_message_defaults_to_direct(self):
        state: State = {
            "messages": [AIMessage(content="resposta")],
            "session_metadata": {},
        }
        cmd = await supervisor(state)
        assert cmd.goto == "direct"
