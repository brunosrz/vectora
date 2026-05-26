/**
 * API Constants — Vectora
 *
 * URL base para o backend Vectora (FastAPI, porta 8080 por default).
 * Configurar via NEXT_PUBLIC_VECTORA_API_URL no .env.local.
 */

function getVectoraApiUrl(): string {
  return (
    process.env.NEXT_PUBLIC_VECTORA_API_URL ||
    (process.env.NODE_ENV === "development" ? "http://localhost:8080" : "")
  )
}

export const VECTORA_API_URL = getVectoraApiUrl()

// ---------------------------------------------------------------------------
// Backward-compat: componentes que ainda referenciam LANGGRAPH_API_URL
// receberão o novo URL do Vectora. Remover estes aliases após a migração.
// ---------------------------------------------------------------------------

/** @deprecated Use VECTORA_API_URL */
export const LANGGRAPH_API_URL = VECTORA_API_URL

/** @deprecated LangSmith removido — não expõe chave de API no browser */
export const LANGSMITH_API_KEY: string | undefined = undefined
