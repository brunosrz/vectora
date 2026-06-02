"""RAG Agent — Referências de arquitetura e curador de workspace.

O "agente RAG" do Vectora é implementado como um **subgrafo LangGraph**
de múltiplos nós em `src/nodes/rag_subgraph.py`, não como uma função
de agente única (como `coder` e `search`). Isso reflete a diferença
arquitetural: o RAG é um pipeline de recuperação/decisão/reranking/injeção,
não uma sessão LLM em loop.

Fluxo interno do subgrafo:
  START → rag_expand_query → rag_retrieve → rag_decide_node
            ├── (score ≥ 0.7) → rag_inject → END
            ├── (score ≥ 0.4) → rag_rerank → rag_search_audit → rag_inject → END
            └── (score < 0.4) → rag_websearch → rag_search_audit → rag_inject → END

  rag_search_audit: Search Agent valida os docs pós-rerank. Pode chamar
  manage_retriever (delete), fetch_url e embedding (bucket "search") para
  corrigir a base antes do inject. Score alto (≥ 0.7) vai direto.

Integração no grafo principal (`graph.py`):
  orchestrator (routing_decision="rag") → rag_subgraph → orchestrator (síntese)

Para construir o subgrafo, use:
  from vectora.nodes.rag_subgraph import build_rag_subgraph
  rag_subgraph = build_rag_subgraph()

O orchestrator delega ao `rag_subgraph` quando `routing_decision == "rag"`.
Após o subgrafo injetar o contexto como SystemMessage(name="rag_context"),
o orchestrator é re-invocado e entra no caminho de síntese determinístico
(`_is_post_rag()` → `_synthesize_after_rag()` → END).

Curator (B4):
  `curate_workspace_knowledge(workspace_id)` é chamado pelo BackgroundEmbeddingWorker
  após cada batch de ingestão (debounce 30s). Faz 1 LLM call por batch para
  resumir o conhecimento adicionado e atualizar o MANIFEST.md do workspace.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Re-exporta build_rag_subgraph para importação unificada via agents.*
from src.nodes.rag_subgraph import build_rag_subgraph

__all__ = ["build_rag_subgraph", "curate_workspace_knowledge"]

# ---------------------------------------------------------------------------
# RAG Curator (B4)
# ---------------------------------------------------------------------------

_curator_llm = None


def _get_curator_llm() -> object:
    """LLM singleton para síntese do curator (plain, sem structured output)."""
    global _curator_llm
    if _curator_llm is None:
        from src.services.utils import load_llm

        _curator_llm = load_llm()
        logger.debug("curator LLM inicializado")
    return _curator_llm


async def curate_workspace_knowledge(workspace_id: str) -> str:
    """Sintetiza o conhecimento novo de um workspace e atualiza o MANIFEST.md.

    Chamado pelo BackgroundEmbeddingWorker após cada batch de ingestão
    (debounce ≥ 30s). Faz exatamente 1 LLM call por flush — ingestar
    1000 arquivos = 1 call de síntese, não 1000.

    Fluxo:
    1. Lê o MANIFEST.md existente (se houver) para contexto acumulado
    2. Amostra docs recentemente indexados do LanceDB (via vector_search)
    3. LLM sintetiza o que foi adicionado em linguagem natural
    4. Escreve MANIFEST.md atualizado + buckets/<bucket>.md
    5. Chama workspace_registry.bump_version() → orchestrator recarrega contexto

    Args:
        workspace_id: ID do workspace a curar

    Returns:
        Mensagem de status da curadoria
    """
    try:
        from src.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws is None:
            return f"workspace {workspace_id} não encontrado"

        # Cria diretório de manifests se necessário
        manifest_dir = ws.manifest_dir()
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / "buckets").mkdir(parents=True, exist_ok=True)

        # Amostra docs indexados para o LLM sintetizar
        sample_docs = await _sample_recent_docs(workspace_id)
        if not sample_docs:
            return f"workspace {workspace_id}: nenhum doc amostrado, curadoria pulada"

        # Contexto acumulado (manifest existente, se houver)
        existing_manifest = ""
        manifest_path = ws.manifest_path()
        if manifest_path.exists():
            import contextlib

            with contextlib.suppress(Exception):
                existing_manifest = manifest_path.read_text(
                    encoding="utf-8", errors="ignore"
                )

        # Prompt de síntese
        prompt = _build_curator_prompt(ws.name, ws.cwd, sample_docs, existing_manifest)

        # Chamada ao LLM (1 call por flush)
        llm = _get_curator_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        result = await llm.ainvoke(  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            [
                SystemMessage(
                    content=(
                        "Você é o curator de conhecimento do Vectora. "
                        "Sua tarefa é manter o MANIFEST.md do workspace atualizado "
                        "com um resumo claro do que está indexado na base de conhecimento. "
                        "Seja conciso, preciso e em português."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        manifest_content = str(getattr(result, "content", "") or "").strip()
        if not manifest_content:
            return f"workspace {workspace_id}: LLM não retornou conteúdo"

        # Escreve o MANIFEST.md
        from datetime import UTC, datetime

        frontmatter = (
            "---\n"
            f"workspace_id: {ws.id}\n"
            f"name: {ws.name}\n"
            f"cwd: {ws.cwd}\n"
            f"last_updated: {datetime.now(UTC).isoformat()}\n"
            f"manifest_version: {ws.manifest_version + 1}\n"
            "---\n\n"
        )
        manifest_path.write_text(frontmatter + manifest_content, encoding="utf-8")

        # Bump de versão — orchestrator detecta e recarrega contexto
        new_version = workspace_registry.bump_version(workspace_id)
        logger.info(
            "curator: MANIFEST.md atualizado para workspace %s (v%d)",
            workspace_id,
            new_version,
        )
        return f"workspace {workspace_id} curado com sucesso (manifest_version={new_version})"

    except Exception as e:
        logger.exception(
            "curate_workspace_knowledge: falha no workspace %s", workspace_id
        )
        return f"erro: {e}"


async def _sample_recent_docs(workspace_id: str, max_docs: int = 20) -> list[dict]:
    """Amostra documentos indexados do workspace via LanceDB."""
    try:
        import asyncio
        import json

        from src.nodes.rag_subgraph import _list_collections

        collections = await _list_collections()
        if not collections:
            return []

        # Busca amostras de cada coleção sem query específica
        # (para o curator ter uma visão geral, não uma busca direcionada)
        samples: list[dict] = []
        for coll_name in collections:
            try:
                import lancedb

                from src.config.settings import settings

                if settings.lancedb_dir is None:
                    continue
                db = await lancedb.connect_async(str(settings.lancedb_dir))
                table = await db.open_table(coll_name)
                df = await asyncio.to_thread(lambda t=table: t.to_pandas().head(5))  # ty: ignore[unresolved-attribute]
                for _, row in df.iterrows():
                    try:
                        meta = json.loads(row.get("metadata", "{}") or "{}")
                        # Filtra pelo workspace_id
                        if meta.get("workspace_id") != workspace_id:
                            continue
                        samples.append(
                            {
                                "collection": coll_name,
                                "source": meta.get("source", ""),
                                "text": str(row.get("text", ""))[:200],
                            }
                        )
                        if len(samples) >= max_docs:
                            break
                    except Exception:
                        pass
            except Exception:
                logger.debug(
                    "_sample_recent_docs: falha em coleção %s", coll_name, exc_info=True
                )
                continue
            if len(samples) >= max_docs:
                break

        return samples
    except Exception:
        logger.debug("_sample_recent_docs: falha ao amostrar", exc_info=True)
        return []


def _build_curator_prompt(
    workspace_name: str,
    workspace_cwd: str,
    sample_docs: list[dict],
    existing_manifest: str,
) -> str:
    """Monta o prompt para o LLM gerar o MANIFEST.md."""
    doc_lines = [
        f"- [{doc['collection']}] {doc['source']}: {doc['text'][:150]}"
        for doc in sample_docs[:20]
    ]
    docs_block = "\n".join(doc_lines) if doc_lines else "(nenhum doc amostrado)"

    existing_block = ""
    if existing_manifest:
        # Remove frontmatter do manifest existente
        m = existing_manifest
        if m.startswith("---"):
            end = m.find("---", 3)
            if end != -1:
                m = m[end + 3 :].strip()
        existing_block = (
            f"\n\n## Manifest atual (para contexto acumulado)\n\n{m[:1500]}"
        )

    return f"""Workspace: {workspace_name}
Diretório: {workspace_cwd}

## Docs amostrados recentemente indexados

{docs_block}{existing_block}

## Sua tarefa

Com base nos docs acima, gere um MANIFEST.md atualizado para este workspace.
O manifest deve ter:

1. **Parágrafo de introdução** (2-3 frases): o que é este projeto
2. **Seção "Conhecimento indexado"**: o que está indexado (coleções, fontes, temas)
3. **Seção "Tópicos cobertos"**: lista dos principais temas e conceitos

Seja conciso (máx 600 palavras). Escreva apenas o conteúdo Markdown, sem frontmatter.
"""
