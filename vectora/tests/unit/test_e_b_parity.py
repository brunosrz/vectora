"""Testes de paridade E.B — verifica que o harness deepagents está corretamente
configurado e que os componentes-chave do bloco E.B funcionam como esperado.

Cobertura:
    - VectoraContext: construção correta a partir de config dict (E.B-5)
    - Middleware stack: HITL + Summarization montados na ordem certa (E.B-3)
    - HarnessProfiles: anthropic/google_genai/ollama registrados (E.B-4)
    - FilesystemPermission: regras DENY/ALLOW/INTERRUPT (E.B-9)
    - Memory tools: namespace correto + store API (E.B-11)
    - backends.build_store: InMemoryStore sem index quando sem API key (E.B-11)
    - backends.build_backend: rotas CompositeBackend corretas (E.B-8)
    - agent_factory._subagent_specs: ABAC filtering (E.B-2)
    - agent_factory._agents_md_paths: retorna None se não há AGENTS.md (E.B-11)
    - LangSmith: enable/disable não crasham (E.B-13)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# E.B-5 — VectoraContext
# ---------------------------------------------------------------------------


class TestVectoraContext:
    def test_ctx_from_config_full(self):
        """Todos os campos são preenchidos corretamente."""
        from backend.vtypes.context import ctx_from_config

        config = {
            "configurable": {
                "user_id": "u1",
                "workspace_id": "ws1",
                "permission_mode": "ask",
                "org_id": "org1",
                "language": "pt-BR",
                "model": "claude-3-5-sonnet",
                "thread_id": "t1",
            }
        }
        ctx = ctx_from_config(config)
        assert ctx.user_id == "u1"
        assert ctx.workspace_id == "ws1"
        assert ctx.permission_mode == "ask"
        assert ctx.org_id == "org1"
        assert ctx.locale == "pt-BR"
        assert ctx.model == "claude-3-5-sonnet"
        assert ctx.thread_id == "t1"

    def test_ctx_from_config_empty(self):
        """Valores padrão quando config é None."""
        from backend.vtypes.context import ctx_from_config

        ctx = ctx_from_config(None)
        assert ctx.user_id == "local"
        assert ctx.workspace_id == ""
        assert ctx.permission_mode == "ask"

    def test_ctx_from_config_partial(self):
        """Campos ausentes recebem defaults."""
        from backend.vtypes.context import ctx_from_config

        ctx = ctx_from_config({"configurable": {"user_id": "u2"}})
        assert ctx.user_id == "u2"
        assert ctx.permission_mode == "ask"
        assert ctx.locale == ""

    def test_ctx_locale_fallback(self):
        """``locale`` aceita ``language`` como alias."""
        from backend.vtypes.context import ctx_from_config

        ctx = ctx_from_config({"configurable": {"language": "en-US"}})
        assert ctx.locale == "en-US"


# ---------------------------------------------------------------------------
# E.B-3 — Middleware stack
# ---------------------------------------------------------------------------


class TestMiddlewareStack:
    def test_bypass_mode_no_hitl(self):
        """Mode bypass retorna stack sem HITL."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="bypass")
        assert all("HumanInTheLoop" not in type(m).__name__ for m in stack)

    def test_auto_mode_no_hitl(self):
        """Mode auto retorna stack sem HITL."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="auto")
        assert all("HumanInTheLoop" not in type(m).__name__ for m in stack)

    def test_ask_mode_has_hitl(self):
        """Mode ask deve incluir HumanInTheLoopMiddleware."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="ask")
        names = [type(m).__name__ for m in stack]
        assert "HumanInTheLoopMiddleware" in names

    def test_plan_mode_has_hitl(self):
        """Mode plan deve incluir HumanInTheLoopMiddleware."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="plan")
        names = [type(m).__name__ for m in stack]
        assert "HumanInTheLoopMiddleware" in names

    def test_accept_edits_has_hitl(self):
        """Mode accept_edits inclui HITL para terminal (não para file_write)."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="accept_edits")
        names = [type(m).__name__ for m in stack]
        assert "HumanInTheLoopMiddleware" in names

    def test_no_duplicate_summarization_middleware(self):
        """build_middleware_stack não adiciona SummarizationMiddleware —
        create_deep_agent já o inclui incondicionalmente no stack base, e
        adicionar outro causa AssertionError de middleware duplicado."""
        from backend.services.middleware import build_middleware_stack

        stack = build_middleware_stack(permission_mode="ask")
        names = [type(m).__name__ for m in stack]
        assert not any("ummariz" in n for n in names)


# ---------------------------------------------------------------------------
# E.B-4 — HarnessProfiles
# ---------------------------------------------------------------------------


class TestHarnessProfiles:
    def test_register_profiles_idempotent(self):
        """_register_profiles() pode ser chamado múltiplas vezes sem erro."""
        from backend.services.profiles import _register_profiles

        _register_profiles()
        _register_profiles()  # segunda chamada: sem exceção

    def test_profiles_cover_providers(self):
        """Os três providers principais devem ter perfis registrados."""
        from backend.services.profiles import _register_profiles

        with patch("deepagents.register_harness_profile") as mock_reg:
            _register_profiles()
        keys = [call.args[0] for call in mock_reg.call_args_list]
        assert "anthropic" in keys
        # Chave deve bater com o provider resolvido pelo LangChain
        # (ChatGoogleGenerativeAI → "google_genai"), não com o id de settings.
        assert "google_genai" in keys
        assert "ollama" in keys


# ---------------------------------------------------------------------------
# E.B-9 — FilesystemPermission
# ---------------------------------------------------------------------------


class TestFilesystemPermission:
    def test_deny_env_file(self):
        """Arquivos .env devem ser DENY para qualquer operação."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.check(".env", "read") == "deny"
        assert FS_PERMISSION.check(".env", "write") == "deny"
        assert FS_PERMISSION.check("project/.env.local", "read") == "deny"

    def test_deny_ssh_key(self):
        """Chaves SSH privadas devem ser DENY."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.check("id_rsa", "read") == "deny"
        assert FS_PERMISSION.check("/home/user/.ssh/id_ed25519", "read") == "deny"

    def test_allow_workspace(self):
        """Paths sob /workspace/ devem ser ALLOW."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.check("/workspace/src/main.py", "read") == "allow"
        assert FS_PERMISSION.check("/workspace/package.json", "write") == "allow"

    def test_allow_memories_read(self):
        """Leitura de memórias deve ser ALLOW."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.check("/memories/notes.md", "read") == "allow"

    def test_deny_skills_write(self):
        """Escrita em skills deve ser DENY."""
        from backend.services.permissions import FS_PERMISSION

        assert (
            FS_PERMISSION.check("/memories/skills/my-skill/SKILL.md", "write") == "deny"
        )

    def test_allow_skills_read(self):
        """Leitura de skills deve ser ALLOW."""
        from backend.services.permissions import FS_PERMISSION

        assert (
            FS_PERMISSION.check("/memories/skills/my-skill/SKILL.md", "read") == "allow"
        )

    def test_interrupt_external_write(self):
        """Escrita fora do workspace deve ser INTERRUPT."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.check("/tmp/something.txt", "write") == "interrupt"
        assert FS_PERMISSION.check("/home/user/notes.txt", "write") == "interrupt"

    def test_allow_external_read(self):
        """Leitura fora do workspace deve ser ALLOW (sem interrupt)."""
        from backend.services.permissions import FS_PERMISSION

        result = FS_PERMISSION.check("/tmp/something.txt", "read")
        assert result == "allow"

    def test_is_allowed_helper(self):
        """Atalho is_allowed() funciona corretamente."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.is_allowed("/workspace/file.py", "read") is True
        assert FS_PERMISSION.is_allowed(".env", "read") is False

    def test_requires_interrupt_helper(self):
        """requires_interrupt() detecta ops que precisam de aprovação."""
        from backend.services.permissions import FS_PERMISSION

        assert FS_PERMISSION.requires_interrupt("/tmp/file.txt", "write") is True
        assert FS_PERMISSION.requires_interrupt("/workspace/file.py", "write") is False


# ---------------------------------------------------------------------------
# E.B-11 — Memory tools namespace + store API
# ---------------------------------------------------------------------------


class TestMemoryToolsNamespace:
    def test_user_id_from_config_authenticated(self):
        """user_id autenticado deve ser retornado limpo."""
        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import _user_id_from_config

        config: RunnableConfig = {"configurable": {"user_id": "abc123"}}
        assert _user_id_from_config(config) == "abc123"

    def test_user_id_from_config_workspace(self):
        """workspace_id usado quando não há user_id."""
        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import _user_id_from_config

        config: RunnableConfig = {"configurable": {"workspace_id": "ws1"}}
        assert _user_id_from_config(config) == "workspace_ws1"

    def test_user_id_from_config_thread_fallback(self):
        """thread_id como fallback."""
        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import _user_id_from_config

        config: RunnableConfig = {"configurable": {"thread_id": "t42"}}
        assert _user_id_from_config(config) == "session_t42"

    def test_user_id_from_config_none(self):
        """None retorna 'local'."""
        from backend.tools.memory import _user_id_from_config

        assert _user_id_from_config(None) == "local"

    def test_memory_namespace_structure(self):
        """Namespace deve ser tupla 3-uple."""
        from langchain_core.runnables import RunnableConfig

        from backend.tools.memory import _memory_namespace

        config: RunnableConfig = {"configurable": {"user_id": "u1"}}
        ns = _memory_namespace(config)
        assert ns == ("user", "u1", "memories")
        assert isinstance(ns, tuple)
        assert len(ns) == 3


# ---------------------------------------------------------------------------
# E.B-11 — backends.build_store
# ---------------------------------------------------------------------------


class TestBuildStore:
    async def test_build_store_returns_async_sqlite_store(self):
        """build_store() (async) retorna AsyncSqliteStore persistente (F5)."""
        import contextlib

        from langgraph.store.sqlite.aio import AsyncSqliteStore

        from backend.services.backends import build_store

        with patch("backend.services.backends._build_index", return_value=None):
            store = await build_store()
        assert isinstance(store, AsyncSqliteStore)
        # Fecha a conexão aiosqlite aberta pelo store para não vazar handle.
        with contextlib.suppress(Exception):
            await store.conn.close()

    def test_build_store_no_index_when_no_key(self):
        """Sem API key Cohere, build_store() retorna store sem indexação."""
        from backend.services.backends import _build_index

        with patch("backend.settings.settings") as mock_s:
            mock_s.embedding_model = "embed-multilingual-v3.0"
            mock_s.get_cohere_api_key.return_value = None
            result = _build_index(None)
        assert result is None


# ---------------------------------------------------------------------------
# E.B-8 — backends.build_backend routes
# ---------------------------------------------------------------------------


class TestBuildBackend:
    def test_composite_backend_created(self):
        """build_backend() deve criar CompositeBackend sem erros."""
        from backend.services.backends import build_backend

        backend = build_backend(workspace_id=None, user_id="u1")
        assert backend is not None


# ---------------------------------------------------------------------------
# E.B-2 — _subagent_specs ABAC
# ---------------------------------------------------------------------------


class TestSubagentSpecs:
    def test_subagent_specs_returns_two(self):
        """Por padrão retorna coder + search."""
        from backend.services.agent_factory import _subagent_specs

        specs = _subagent_specs()
        names = [s["name"] for s in specs]
        assert "coder" in names
        assert "search" in names
        assert len(specs) == 2

    def test_subagent_specs_abac_filtering(self):
        """Com user_id e disabled tools, tools são removidas das specs."""
        from backend.services.agent_factory import _subagent_specs

        fake_tool = MagicMock()
        fake_tool.name = "file_write"
        fake_tool2 = MagicMock()
        fake_tool2.name = "terminal"

        with (
            patch(
                "backend.agents.coder.SUBAGENT_SPEC",
                {
                    "name": "coder",
                    "description": "d",
                    "system_prompt": "s",
                    "tools": [fake_tool, fake_tool2],
                },
            ),
            patch(
                "backend.agents.search.SUBAGENT_SPEC",
                {
                    "name": "search",
                    "description": "d",
                    "system_prompt": "s",
                    "tools": [],
                },
            ),
            patch(
                "backend.services.tool_policy.get_disabled", return_value=["file_write"]
            ),
        ):
            specs = _subagent_specs(user_id="u1")

        coder_spec = next(s for s in specs if s["name"] == "coder")
        tool_names = [t.name for t in coder_spec["tools"]]
        assert "file_write" not in tool_names
        assert "terminal" in tool_names

    def test_subagent_specs_global_disable_applies_without_user_id(
        self, tmp_path, monkeypatch
    ):
        """Kill-switch global (admin) filtra subagents mesmo sem user_id (sessão local)."""
        from backend.services import tool_policy
        from backend.services.agent_factory import _subagent_specs

        monkeypatch.setattr(tool_policy, "_policy_dir", lambda: tmp_path / "tools")
        tool_policy.set_disabled(tool_policy.GLOBAL_SCOPE, ["file_write"])

        fake_tool = MagicMock()
        fake_tool.name = "file_write"
        fake_tool2 = MagicMock()
        fake_tool2.name = "terminal"

        with (
            patch(
                "backend.agents.coder.SUBAGENT_SPEC",
                {
                    "name": "coder",
                    "description": "d",
                    "system_prompt": "s",
                    "tools": [fake_tool, fake_tool2],
                },
            ),
            patch(
                "backend.agents.search.SUBAGENT_SPEC",
                {
                    "name": "search",
                    "description": "d",
                    "system_prompt": "s",
                    "tools": [],
                },
            ),
        ):
            specs = _subagent_specs()  # sem user_id — sessão local

        coder_spec = next(s for s in specs if s["name"] == "coder")
        tool_names = [t.name for t in coder_spec["tools"]]
        assert "file_write" not in tool_names
        assert "terminal" in tool_names


# ---------------------------------------------------------------------------
# E.B-11 — _agents_md_paths
# ---------------------------------------------------------------------------


class TestAgentsMdPaths:
    def test_returns_none_when_no_file(self, tmp_path):
        """Sem AGENTS.md retorna None."""
        from backend.services.agent_factory import _agents_md_paths

        with patch("backend.services.agent_factory.Path") as mock_path_cls:
            mock_home = MagicMock()
            mock_path_cls.home.return_value = mock_home
            mock_agents_md = MagicMock()
            mock_agents_md.is_file.return_value = False
            mock_home.__truediv__.return_value.__truediv__.return_value = mock_agents_md
            result = _agents_md_paths()
        assert result is None

    def test_returns_list_when_file_exists(self):
        """Com AGENTS.md existente retorna lista com o path."""
        from backend.services.agent_factory import _agents_md_paths

        with patch("backend.services.agent_factory.Path") as mock_path_cls:
            mock_home = MagicMock()
            mock_path_cls.home.return_value = mock_home
            mock_agents_md = MagicMock()
            mock_agents_md.is_file.return_value = True
            mock_agents_md.__str__.return_value = "/home/user/.vectora/AGENTS.md"
            mock_home.__truediv__.return_value.__truediv__.return_value = mock_agents_md
            result = _agents_md_paths()
        assert isinstance(result, list)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# E.B-13 — LangSmith enable/disable
# ---------------------------------------------------------------------------


class TestLangSmith:
    def test_enable_disabled_by_default(self):
        """Com langsmith_tracing=False, enable retorna False."""
        from backend.services.tracer import enable_langsmith_tracing

        with patch("backend.settings.settings") as mock_s:
            mock_s.langsmith_tracing = False
            result = enable_langsmith_tracing()
        assert result is False

    def test_enable_without_key_returns_false(self):
        """Com tracing=True mas sem api_key, retorna False."""
        import os

        from backend.services.tracer import enable_langsmith_tracing

        env_backup = {
            k: os.environ.pop(k, None)
            for k in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY")
        }
        try:
            with patch("backend.settings.settings") as mock_s:
                mock_s.langsmith_tracing = True
                mock_s.langsmith_api_key = None
                result = enable_langsmith_tracing()
            assert result is False
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

    def test_enable_sets_env_vars(self):
        """Com tracing=True e api_key, seta vars de ambiente corretamente."""
        import os

        from backend.services.tracer import (
            disable_langsmith_tracing,
            enable_langsmith_tracing,
        )

        try:
            with patch("backend.settings.settings") as mock_s:
                mock_s.langsmith_tracing = True
                mock_s.langsmith_api_key = "ls-test-key"
                mock_s.langsmith_project = "test-project"
                mock_s.langsmith_endpoint = None
                result = enable_langsmith_tracing()

            assert result is True
            assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
            assert os.environ.get("LANGCHAIN_API_KEY") == "ls-test-key"
            assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
        finally:
            disable_langsmith_tracing()

    def test_disable_clears_env_vars(self):
        """disable_langsmith_tracing() remove as vars."""
        import os

        from backend.services.tracer import disable_langsmith_tracing

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = "test"
        disable_langsmith_tracing()
        assert "LANGCHAIN_TRACING_V2" not in os.environ
        assert "LANGCHAIN_API_KEY" not in os.environ
