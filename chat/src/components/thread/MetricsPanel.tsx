"use client";

/**
 * MetricsPanel — painel de observabilidade em tempo real.
 *
 * Lê ui_metrics do state do LangGraph (D1.5) e exibe:
 * - Último nó + latência
 * - Tokens totais da sessão
 * - RAG hits / misses
 * - Tool calls por tipo
 * - Workspace ativo
 */

import { useStreamContext } from "@/providers/Stream";
import { type UIMetrics } from "@/types/agent";

function MetricRow({
  label,
  value,
  unit,
  highlight,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  highlight?: boolean;
}) {
  if (value == null) return null;
  return (
    <div className="flex items-center justify-between gap-2 py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-500 truncate">{label}</span>
      <span
        className={`text-xs font-medium tabular-nums shrink-0 ${
          highlight ? "text-orange-600" : "text-gray-800"
        }`}
      >
        {value}
        {unit && (
          <span className="text-gray-400 font-normal ml-0.5">{unit}</span>
        )}
      </span>
    </div>
  );
}

export function MetricsPanel() {
  const { values } = useStreamContext();
  const metrics = values?.ui_metrics as UIMetrics | undefined;

  const ragHits = metrics?.rag_hits ?? 0;
  const ragMisses = metrics?.rag_misses ?? 0;
  const ragTotal = ragHits + ragMisses;
  const hitRate = ragTotal > 0 ? Math.round((ragHits / ragTotal) * 100) : null;

  const toolCallCount = Object.values(metrics?.tool_calls ?? {}).reduce(
    (s, n) => s + n,
    0,
  );

  return (
    <div className="w-full text-sm">
      <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
          Métricas
        </span>
      </div>

      <div className="px-3 py-1">
        {/* Nó ativo */}
        <MetricRow
          label="Último nó"
          value={metrics?.last_node ?? "–"}
          highlight={!!metrics?.last_node}
        />
        <MetricRow
          label="Latência"
          value={
            metrics?.last_node_ms != null
              ? metrics.last_node_ms.toFixed(0)
              : null
          }
          unit="ms"
        />

        {/* Tokens */}
        <MetricRow
          label="Tokens"
          value={
            metrics?.total_tokens_session != null
              ? metrics.total_tokens_session.toLocaleString()
              : null
          }
        />

        {/* RAG */}
        <MetricRow
          label="RAG hit rate"
          value={hitRate != null ? `${hitRate}%` : null}
        />
        <MetricRow label="RAG hits" value={ragHits > 0 ? ragHits : null} />
        <MetricRow
          label="RAG misses"
          value={ragMisses > 0 ? ragMisses : null}
        />

        {/* Tools */}
        {toolCallCount > 0 && (
          <MetricRow label="Tool calls" value={toolCallCount} />
        )}

        {/* Workspace */}
        {metrics?.workspace_id && (
          <MetricRow label="Workspace" value={metrics.workspace_id} />
        )}
      </div>

      {/* Top tools breakdown */}
      {metrics?.tool_calls && toolCallCount > 0 && (
        <div className="px-3 pb-2 mt-1">
          <p className="text-xs text-gray-400 mb-1">Ferramentas usadas:</p>
          {Object.entries(metrics.tool_calls)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([name, count]) => (
              <div key={name} className="flex items-center gap-2 py-0.5">
                <span className="text-xs text-gray-600 truncate flex-1">
                  {name}
                </span>
                <span className="text-xs text-gray-500 tabular-nums">
                  ×{count}
                </span>
              </div>
            ))}
        </div>
      )}

      {!metrics && (
        <div className="px-3 py-4 text-xs text-gray-400 text-center">
          Aguardando dados…
          <br />
          <span className="opacity-60">
            Inicie uma conversa para ver métricas.
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * MetricsBadges — versão compacta para mobile (barra no topo).
 */
export function MetricsBadges() {
  const { values } = useStreamContext();
  const metrics = values?.ui_metrics as UIMetrics | undefined;

  if (!metrics) return null;

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 text-xs text-gray-500 bg-gray-50 border-b border-gray-100">
      {metrics.last_node && (
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
          {metrics.last_node}
          {metrics.last_node_ms != null && (
            <span className="text-gray-400">
              {metrics.last_node_ms.toFixed(0)}ms
            </span>
          )}
        </span>
      )}
      {metrics.total_tokens_session != null && (
        <span>{metrics.total_tokens_session.toLocaleString()} tokens</span>
      )}
      {metrics.workspace_id && (
        <span className="text-gray-400">{metrics.workspace_id}</span>
      )}
    </div>
  );
}
