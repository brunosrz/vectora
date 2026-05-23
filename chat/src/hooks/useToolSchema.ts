/**
 * useToolSchema — Discovery Layer (D1.1)
 *
 * Retorna um mapa { toolName → ToolMeta } com o render_hint de cada tool.
 *
 * Estratégia de três camadas:
 *   1. Schema estático embutido — funciona sem servidor externo (default)
 *   2. Endpoint /api/tools/schema do Next.js (proxies para o MCP server)
 *      — atualiza o schema dinamicamente se o MCP server estiver rodando
 *   3. Fallback silencioso para o schema estático em caso de erro de rede
 */

"use client";

import { useEffect, useState } from "react";

export type RenderHint =
  | "search_results"
  | "web_results"
  | "diff"
  | "code_block"
  | "terminal_output"
  | "queue_progress"
  | "queue_badge"
  | "table"
  | "markdown"
  | "json"; // fallback

export interface ToolMeta {
  name: string;
  description: string;
  render_hint: RenderHint;
  args_schema: Record<string, unknown>;
}

export type ToolSchemaMap = Record<string, ToolMeta>;

// ─── Schema estático — mirrors das tools Python com render_hint ──────────────
// Garante que a Discovery Layer funcione mesmo sem o MCP server rodando.
// Atualizar aqui quando novas tools forem adicionadas em vectora/tools/*.py

const STATIC_SCHEMA: ToolSchemaMap = {
  // tools/rag.py
  embedding: {
    name: "embedding",
    description: "Indexa documento no LanceDB",
    render_hint: "queue_badge",
    args_schema: {},
  },
  vector_search: {
    name: "vector_search",
    description: "Busca semântica vetorial",
    render_hint: "search_results",
    args_schema: {},
  },
  ingest_docs: {
    name: "ingest_docs",
    description: "Indexa pasta de documentos em batch",
    render_hint: "queue_progress",
    args_schema: {},
  },
  manage_retriever: {
    name: "manage_retriever",
    description: "Lista/remove docs do RAG",
    render_hint: "table",
    args_schema: {},
  },

  // tools/web.py
  web_search: {
    name: "web_search",
    description: "Busca web via Tavily",
    render_hint: "web_results",
    args_schema: {},
  },
  fetch_url: {
    name: "fetch_url",
    description: "Extrai conteúdo de URL",
    render_hint: "web_results",
    args_schema: {},
  },

  // tools/fs.py
  file_read: {
    name: "file_read",
    description: "Lê arquivo de texto",
    render_hint: "code_block",
    args_schema: {},
  },
  file_edit: {
    name: "file_edit",
    description: "Edita arquivo por substituição",
    render_hint: "diff",
    args_schema: {},
  },
  file_write: {
    name: "file_write",
    description: "Cria ou sobrescreve arquivo",
    render_hint: "code_block",
    args_schema: {},
  },
  grep: {
    name: "grep",
    description: "Busca regex em arquivos",
    render_hint: "code_block",
    args_schema: {},
  },
  list_dir: {
    name: "list_dir",
    description: "Lista arquivos em diretório",
    render_hint: "code_block",
    args_schema: {},
  },
  terminal: {
    name: "terminal",
    description: "Executa comando shell",
    render_hint: "terminal_output",
    args_schema: {},
  },
  create_artifact: {
    name: "create_artifact",
    description: "Persiste documento estruturado",
    render_hint: "code_block",
    args_schema: {},
  },

  // tools/workspace.py
  workspace_describe: {
    name: "workspace_describe",
    description: "Descreve workspace ativo",
    render_hint: "markdown",
    args_schema: {},
  },
  workspace_list: {
    name: "workspace_list",
    description: "Lista workspaces registrados",
    render_hint: "table",
    args_schema: {},
  },
  bucket_summary: {
    name: "bucket_summary",
    description: "Resumo de bucket do workspace",
    render_hint: "markdown",
    args_schema: {},
  },

  // tools/memory.py
  save_memory: {
    name: "save_memory",
    description: "Persiste memória episódica",
    render_hint: "json",
    args_schema: {},
  },
  get_memory: {
    name: "get_memory",
    description: "Recupera memória episódica",
    render_hint: "json",
    args_schema: {},
  },
  delete_memory: {
    name: "delete_memory",
    description: "Remove memória",
    render_hint: "json",
    args_schema: {},
  },

  // tools/mcp.py
  call_mcp_tool: {
    name: "call_mcp_tool",
    description: "Chama tool de servidor MCP externo",
    render_hint: "json",
    args_schema: {},
  },
};

const CACHE_TTL_MS = 60_000;

// Cache em módulo — inicializado com schema estático, sobrescrito pelo servidor
let _cachedSchema: ToolSchemaMap = { ...STATIC_SCHEMA };
let _lastFetch = 0;

async function fetchToolSchema(): Promise<ToolSchemaMap> {
  const now = Date.now();
  if (now - _lastFetch < CACHE_TTL_MS) {
    return _cachedSchema;
  }

  try {
    // Tenta via proxy Next.js (server-side, sem CORS)
    const res = await fetch("/api/tools/schema", {
      headers: { "Content-Type": "application/json" },
    });

    if (res.ok) {
      const data = await res.json();
      const tools: ToolMeta[] = data.tools ?? [];
      if (tools.length > 0) {
        // Mescla: schema do servidor sobrescreve o estático
        _cachedSchema = {
          ...STATIC_SCHEMA,
          ...Object.fromEntries(tools.map((t) => [t.name, t])),
        };
      }
      _lastFetch = now;
    }
  } catch {
    // Silently fallback — usa schema estático
    _lastFetch = now; // evita retry imediato
  }

  return _cachedSchema;
}

export function useToolSchema(): ToolSchemaMap {
  const [schema, setSchema] = useState<ToolSchemaMap>(_cachedSchema);

  useEffect(() => {
    let cancelled = false;

    fetchToolSchema().then((s) => {
      if (!cancelled) setSchema(s);
    });

    const interval = setInterval(() => {
      _lastFetch = 0; // invalida cache
      fetchToolSchema().then((s) => {
        if (!cancelled) setSchema(s);
      });
    }, CACHE_TTL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return schema;
}

/** Retorna o render_hint de uma tool, ou "json" como fallback */
export function getRenderHint(
  schema: ToolSchemaMap,
  toolName: string,
): RenderHint {
  return schema[toolName]?.render_hint ?? "json";
}
