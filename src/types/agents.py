from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.types.metrics import UIMetrics

AgentName = Literal["coder", "search", "rag"]


class SubTask(BaseModel):
    """Tarefa individual para execução paralela de agentes (C5)."""

    agent: AgentName = Field(description="Sub-agent responsável por esta task.")
    task_query: str = Field(
        description="Instrução clara e autossuficiente — como uma task_query de delegate."
    )
    reason: str = Field(
        default="", description="Por que esta task é independente das demais."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class MemoryEntry(BaseModel):
    """Par key/content para persistência automática de informações do usuário."""

    key: str = Field(
        description=(
            "Chave única e descritiva da memória. Use snake_case curto. "
            "Exemplos: 'nome', 'idade', 'projeto_principal', 'linguagem_preferida', "
            "'cargo', 'empresa', 'cidade', 'objetivo_atual'."
        )
    )
    content: str = Field(
        description="Conteúdo da memória em linguagem natural, como uma frase completa."
    )


class OrchestratorDecision(BaseModel):
    """Decisão do orchestrator: responder inline, delegar ou executar em paralelo."""

    action: Literal["respond", "delegate", "parallel"] = Field(
        description="Ação decidida pelo orchestrator."
    )
    response: str | None = Field(
        default=None,
        description="Resposta completa em markdown (somente quando action == 'respond').",
    )
    delegate_to: AgentName | None = Field(
        default=None,
        description="Sub-agent alvo (somente quando action == 'delegate').",
    )
    task_query: str | None = Field(
        default=None,
        description="Instrução clara e concisa para o sub-agent — 1 a 3 frases diretas.",
    )
    parallel_tasks: list[SubTask] | None = Field(
        default=None,
        description="Lista de tasks independentes para execução paralela (somente action == 'parallel').",
    )
    save_memories: list[MemoryEntry] | None = Field(
        default=None,
        description=(
            "Memórias a salvar ANTES de responder. Preencha sempre que o usuário "
            "compartilhar informações pessoais (nome, idade, cargo, projetos, "
            "preferências, localização, stack, etc.). Pode ser preenchido junto "
            "com qualquer action — não precisa ser exclusivo."
        ),
    )
    reason: str = Field(
        description="Uma frase curta explicando a decisão — útil para logs e debug."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CoderResult(BaseModel):
    """Resultado estruturado do Coder Agent após concluir uma tarefa."""

    summary: str = Field(description="Resumo do que foi feito (1-3 frases).")
    files_changed: list[str] = Field(
        default_factory=list,
        description="Caminhos dos arquivos criados ou modificados.",
    )
    tests_run: bool = Field(
        default=False,
        description="True se foram executados testes (pytest, npm test, etc.).",
    )
    success: bool = Field(
        default=True, description="True se a tarefa foi concluída sem erros graves."
    )
    next_steps: str | None = Field(
        default=None, description="Sugestão de próximo passo, se aplicável."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class SearchResult(BaseModel):
    """Resultado estruturado do Search Agent após concluir uma pesquisa."""

    summary: str = Field(description="Resumo do que foi encontrado (1-3 frases).")
    sources: list[str] = Field(
        default_factory=list,
        description="URLs das fontes consultadas (web_search, fetch_url).",
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confiança nos resultados de 0.0 a 1.0.",
    )
    web_search_used: bool = Field(
        default=False, description="True se web_search ou fetch_url foram chamados."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ParallelResult(BaseModel):
    """Resultado de uma task executada em paralelo (C5)."""

    agent: str = Field(description="Sub-agent responsável por esta task.")
    task: str = Field(description="Instrução/task executada.")
    reason: str = Field(default="", description="Por que esta task era independente.")
    response: str = Field(description="Resposta gerada pelo agent.")
    success: bool = Field(
        default=True, description="True se a execução foi bem-sucedida."
    )

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)
