/**
 * API Constants — Vectora
 *
 * Após o Bloco D (migração para Vite SPA + FastAPI servindo `chat/dist/`),
 * o frontend roda **no mesmo origin** do backend em produção. Em dev, o
 * Vite proxy (`server.proxy` em `vite.config.ts`) intercepta as rotas
 * `/auth`, `/vectora.chat.v1`, `/admin`, etc. e as redireciona para
 * `http://127.0.0.1:8080`.
 *
 * Por isso `VECTORA_API_URL = ""` em ambos os modos — todas as chamadas
 * usam paths relativos. Override apenas para casos especiais (testes,
 * dev com backend em outro host).
 */

export const VECTORA_API_URL: string =
  (typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_VECTORA_API_URL) ||
  "";

// ---------------------------------------------------------------------------
// Backward-compat: componentes que ainda referenciam LANGGRAPH_API_URL
// receberão o novo URL do Vectora. Remover estes aliases após a migração.
// ---------------------------------------------------------------------------

/** @deprecated Use VECTORA_API_URL */
export const LANGGRAPH_API_URL = VECTORA_API_URL;

/** @deprecated LangSmith removido — não expõe chave de API no browser */
export const LANGSMITH_API_KEY: string | undefined = undefined;
