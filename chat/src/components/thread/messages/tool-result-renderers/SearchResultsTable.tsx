"use client";

/**
 * SearchResultsTable — renderiza resultados de vector_search.
 *
 * Usado para `render_hint: "search_results"`.
 * Aceita array de objetos com text, metadata (source, collection, workspace_id)
 * e relevance_score.
 */

import { type SearchResult } from "@/types/agent";

interface SearchResultsTableProps {
  results: SearchResult[];
  query?: string;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 tabular-nums">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function SearchResultsTable({
  results,
  query,
}: SearchResultsTableProps) {
  if (!results || results.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-3">
        Nenhum documento relevante encontrado.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-gray-200 overflow-hidden text-sm">
      {query && (
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs text-gray-500">
          Query: <span className="font-medium text-gray-700">{query}</span>
          <span className="ml-2 text-gray-400">
            — {results.length} resultado(s)
          </span>
        </div>
      )}
      <div className="divide-y divide-gray-100">
        {results.map((r, idx) => {
          const text = r.text ?? r.page_content ?? "";
          const src = r.metadata?.source ?? "–";
          const collection = r.metadata?.collection ?? r.metadata?.origin ?? "";
          const score = r.relevance_score ?? r.score ?? 0;
          const isWeb = r.metadata?.origin === "web_search";

          return (
            <div
              key={idx}
              className="px-3 py-2 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  {isWeb ? (
                    <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded shrink-0">
                      web
                    </span>
                  ) : collection ? (
                    <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded shrink-0">
                      {collection}
                    </span>
                  ) : null}
                  <span className="text-xs text-gray-500 truncate" title={src}>
                    {src}
                  </span>
                </div>
                <ScoreBar score={score} />
              </div>
              <p className="text-xs text-gray-700 line-clamp-2 leading-relaxed">
                {text.slice(0, 200)}
                {text.length > 200 && "…"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
