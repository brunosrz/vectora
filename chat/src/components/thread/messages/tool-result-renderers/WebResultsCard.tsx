"use client";

/**
 * WebResultsCard — renderiza resultados de web_search e fetch_url.
 *
 * Usado para `render_hint: "web_results"`.
 * Aceita array de resultados Tavily: {url, title, content, raw_content}.
 */

import { type WebSearchResult } from "@/types/agent";

interface WebResultsCardProps {
  results: WebSearchResult[];
}

function FaviconImg({ url }: { url: string }) {
  let domain = "";
  try {
    domain = new URL(url).hostname;
  } catch {
    return null;
  }
  return (
    /* eslint-disable-next-line */
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
      alt=""
      width={16}
      height={16}
      className="shrink-0 mt-0.5"
    />
  );
}

export function WebResultsCard({ results }: WebResultsCardProps) {
  if (!results || results.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-3">
        Nenhum resultado de busca encontrado.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-gray-200 dark:border-gray-800 overflow-hidden text-sm divide-y divide-gray-100 dark:divide-gray-800 bg-white dark:bg-gray-900/50">
      {results.map((r, idx) => {
        const snippet = r.content ?? r.raw_content ?? "";
        const displayUrl = r.url ?? "";

        return (
          <div
            key={idx}
            className="px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-start gap-2">
              {displayUrl && <FaviconImg url={displayUrl} />}
              <div className="min-w-0 flex-1">
                {r.title && (
                  <div className="font-medium text-gray-900 dark:text-gray-100 truncate text-xs mb-0.5">
                    {r.title}
                  </div>
                )}
                {displayUrl && (
                  <a
                    href={displayUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline truncate block"
                  >
                    {displayUrl}
                  </a>
                )}
                {snippet && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2 leading-relaxed">
                    {snippet.slice(0, 250)}
                    {snippet.length > 250 && "…"}
                  </p>
                )}
              </div>
              {typeof r.score === "number" && (
                <span className="text-xs text-gray-400 shrink-0 tabular-nums">
                  {r.score.toFixed(2)}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
