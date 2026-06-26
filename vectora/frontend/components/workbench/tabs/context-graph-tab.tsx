"use client";

import { useState } from "react";
import { Loader2, RefreshCw, ExternalLink } from "lucide-react";

import { useContextGraph } from "@/lib/hooks/use-context-graph";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { m } from "@/lib/paraglide/messages";

interface ContextGraphTabProps {
  threadId: string;
  onSendPrompt?: (text: string) => void;
}

export function ContextGraphTab({
  threadId,
  onSendPrompt,
}: ContextGraphTabProps) {
  const workspaceId = useWorkspacesStore((s) => s.active_id);
  const {
    status,
    report,
    loading,
    build,
    update,
    cancel,
    queryAffected,
    getHtmlUrl,
  } = useContextGraph(workspaceId);
  const [showReport, setShowReport] = useState(false);

  const isBuilt = status.status === "done";
  const isRunning = status.status === "running" || status.status === "queued";

  function handleBuild() {
    build();
  }

  function handleQuestion(q: string) {
    onSendPrompt?.(q);
  }

  const godNodeMatches = report?.match(
    /\*\*God nodes[^*]*\*\*[^\n]*\n([\s\S]*?)(?=\n##|\n\*\*|$)/i,
  );
  const godNodes = godNodeMatches
    ? godNodeMatches[1]
        .split("\n")
        .filter((l) => l.trim().startsWith("-"))
        .map((l) => l.replace(/^-\s*/, "").trim())
        .slice(0, 8)
    : [];

  const questionMatches = report?.match(
    /sugeridas?[^\n]*\n([\s\S]*?)(?=\n##|\n\*\*|$)/i,
  );
  const questions = questionMatches
    ? questionMatches[1]
        .split("\n")
        .filter((l) => l.trim().startsWith("-") || l.trim().match(/^\d+\./))
        .map((l) => l.replace(/^[-\d.]\s*/, "").trim())
        .filter(Boolean)
        .slice(0, 5)
    : [];

  const htmlUrl = getHtmlUrl();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Barra de ação */}
      <div className="flex items-center justify-end gap-2 px-3 py-2 border-b border-border/60 shrink-0">
        {isRunning && (
          <button
            onClick={() => void cancel()}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-border/80"
          >
            {m.graph_cancel_button()}
          </button>
        )}
        {isBuilt && !isRunning && (
          <button
            onClick={() => update()}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-border/80 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className="h-3 w-3" />
            {m.graph_update_button()}
          </button>
        )}
        <button
          onClick={handleBuild}
          disabled={isRunning || loading}
          className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              {m.graph_building()}
            </>
          ) : (
            <>
              <RefreshCw className="h-3 w-3" />
              {isBuilt ? m.graph_rebuild_button() : m.graph_build_button()}
            </>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {/* Status: error */}
        {status.status === "error" && (
          <div className="px-3 py-2 text-sm text-destructive">
            {status.error ?? "Erro desconhecido"}
          </div>
        )}

        {/* Status: not built */}
        {!isBuilt && !isRunning && status.status !== "error" && (
          <div className="px-3 py-4 text-sm text-muted-foreground text-center space-y-2">
            <p>{m.graph_not_built()}</p>
            <p className="text-xs">{m.graph_build_description()}</p>
          </div>
        )}

        {/* Status: running */}
        {isRunning && (
          <div className="h-full flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <p>{m.graph_building()}</p>
          </div>
        )}

        {/* Built: stats + god nodes + questions */}
        {isBuilt && (
          <div className="flex flex-col gap-3 px-3 py-3">
            {/* Métricas */}
            <div className="flex gap-4 text-xs text-muted-foreground">
              {status.node_count != null && (
                <span>{status.node_count} nós</span>
              )}
              {status.edge_count != null && (
                <span>{status.edge_count} arestas</span>
              )}
            </div>

            {/* Link para HTML interativo */}
            {htmlUrl && (
              <a
                href={htmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                Ver grafo interativo
              </a>
            )}

            {/* God nodes */}
            {godNodes.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-1.5">
                  {m.graph_god_nodes_title()}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {godNodes.map((node) => (
                    <span key={node} className="flex items-center gap-0.5">
                      <button
                        onClick={() =>
                          handleQuestion(
                            `Explique o nó "${node}" no grafo de contexto`,
                          )
                        }
                        className="text-xs px-2 py-0.5 rounded-l-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {node}
                      </button>
                      <button
                        title={m.graph_affected_button()}
                        onClick={() =>
                          queryAffected(node).then((text) => {
                            if (text) handleQuestion(text);
                          })
                        }
                        className="text-xs px-1.5 py-0.5 rounded-r-full bg-muted hover:bg-primary/20 text-muted-foreground hover:text-primary transition-colors border-l border-border/40"
                      >
                        ↯
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Perguntas sugeridas */}
            {questions.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-1.5">
                  {m.graph_questions_title()}
                </p>
                <ul className="space-y-1.5">
                  {questions.map((q) => (
                    <li key={q}>
                      <button
                        onClick={() => handleQuestion(q)}
                        className="text-xs text-left text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition-colors w-full"
                      >
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Report toggle */}
            {report && (
              <div>
                <button
                  onClick={() => setShowReport((v) => !v)}
                  className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
                >
                  {showReport ? "Ocultar" : m.graph_report_title()}
                </button>
                {showReport && (
                  <pre className="mt-2 text-xs whitespace-pre-wrap text-muted-foreground bg-muted/50 rounded p-2 max-h-64 overflow-y-auto">
                    {report}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer: crédito */}
      <div className="px-3 py-1.5 border-t border-border/60 shrink-0">
        <p className="text-xs text-muted-foreground/60">{m.graph_credit()}</p>
      </div>
    </div>
  );
}
