"use client";

import { useState } from "react";
import { Loader2, RefreshCw, ExternalLink, X } from "lucide-react";

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
    resume,
    cancel,
    queryAffected,
    getHtmlUrl,
  } = useContextGraph(workspaceId);
  const [showReport, setShowReport] = useState(false);

  const isBuilt = status.status === "done";
  const isRunning = status.status === "running" || status.status === "queued";
  const isPaused = status.status === "paused";

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
          onClick={isRunning ? () => void cancel() : handleBuild}
          disabled={!isRunning && loading}
          data-testid="graph-build-btn"
          className={
            isRunning
              ? "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-border/80"
              : "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          }
        >
          {isRunning ? (
            <>
              <X className="h-3 w-3" />
              {m.graph_cancel_button()}
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

        {/* Status: paused (quota esgotada em todos os providers) */}
        {isPaused && (
          <div
            data-testid="graph-paused"
            className="px-3 py-4 text-sm text-center space-y-3"
          >
            <p className="text-amber-500">{m.graph_paused()}</p>
            {status.step != null && status.step_total != null && (
              <div className="space-y-1">
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-amber-500 transition-all"
                    style={{
                      width: `${Math.round((status.step / status.step_total) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {status.step}/{status.step_total}
                </p>
              </div>
            )}
            {status.error && (
              <p className="text-xs text-muted-foreground">{status.error}</p>
            )}
            <button
              onClick={() => resume()}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 mx-auto"
            >
              <RefreshCw className="h-3 w-3" />
              {m.graph_continue_button()}
            </button>
          </div>
        )}

        {/* Status: not built */}
        {!isBuilt && !isRunning && !isPaused && status.status !== "error" && (
          <div className="px-3 py-4 text-sm text-muted-foreground text-center space-y-2">
            <p>{m.graph_not_built()}</p>
            <p className="text-xs">{m.graph_build_description()}</p>
          </div>
        )}

        {/* Status: running */}
        {isRunning && (
          <div className="flex flex-col gap-3 px-3 py-4">
            {/* Spinner + label */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>{status.step_label ?? m.graph_building()}</span>
            </div>

            {/* Barra de progresso por etapa */}
            {status.step != null && status.step_total != null && (
              <div className="space-y-1">
                <div className="h-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary/70 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.round((status.step / status.step_total) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground/50 text-right">
                  {status.step}/{status.step_total}
                </p>
              </div>
            )}

            {/* Contador de arquivos */}
            {status.files_total != null && status.files_total > 0 && (
              <p className="text-xs text-muted-foreground/60">
                {m.graph_files_progress({
                  done: status.files_done ?? 0,
                  total: status.files_total,
                })}
              </p>
            )}

            {/* Lista de arquivos */}
            {status.files_list && status.files_list.length > 0 && (
              <div className="max-h-40 overflow-y-auto space-y-0.5">
                {status.files_list.slice(0, 50).map((file, i) => {
                  const done = i < (status.files_done ?? 0);
                  return (
                    <div
                      key={i}
                      className={`text-[10px] flex items-center gap-1.5 transition-opacity ${
                        done
                          ? "text-muted-foreground"
                          : "text-muted-foreground/30"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          done ? "bg-primary/70" : "bg-muted-foreground/20"
                        }`}
                      />
                      <span className="truncate">{file}</span>
                    </div>
                  );
                })}
              </div>
            )}
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
