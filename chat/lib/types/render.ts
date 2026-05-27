/**
 * Tipos de renderização schema-driven — espelham os metadados das tools Python.
 *
 * O `render_hint` vem do campo `metadata={"render_hint": "..."}` de cada @tool.
 * O frontend usa o hint para decidir qual componente usar — sem hardcode por tool.
 */

/** Como o resultado de uma tool deve ser renderizado. */
export type RenderHint =
  | "diff" // file_edit — unified diff com cores
  | "code_block" // file_read, file_write, fetch_url — código com syntax highlight
  | "terminal_output" // terminal — fundo escuro, monospace
  | "search_results" // web_search, vector_search, search_memory — cards com score/fonte
  | "table" // grep, list_dir, manage_retriever, workspace_list — tabela paginada
  | "queue_progress" // ingest_docs — barra de progresso com contagem
  | "queue_badge" // embedding — badge com queue_id + status
  | "artifact" // create_artifact — card com ícone + link para download
  | "json"; // save_memory, get_memory, delete_memory, fallback universal

/** Categoria de uma tool — agrupa tools afins na UI. */
export type ToolCategory =
  | "filesystem"
  | "web"
  | "rag"
  | "memory"
  | "workspace"
  | "mcp"
  | "artifacts"
  | "general";
