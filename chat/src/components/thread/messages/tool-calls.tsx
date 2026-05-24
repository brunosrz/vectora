/**
 * tool-calls.tsx — renderização de tool calls e resultados.
 *
 * Hierarquia de renderização (D1):
 *   1. ui_component no output JSON (Generative UI Engine) — máxima flexibilidade
 *   2. render_hint do schema (Discovery Layer) — padrão por tipo de tool
 *   3. JSON expandível (fallback universal)
 */

import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  useToolSchema,
  getRenderHint,
  type RenderHint,
} from "@/hooks/useToolSchema";
import {
  FileDiffViewer,
  SearchResultsTable,
  WebResultsCard,
  TerminalBlock,
  QueueProgressCard,
} from "./tool-result-renderers";
import { MarkdownText } from "../markdown-text";
import { SyntaxHighlighter } from "../syntax-highlighter";
import {
  type SearchResult,
  type WebSearchResult,
  type QueueProgress,
  type WorkspaceDescribeResult,
} from "@/types/agent";

// ---------------------------------------------------------------------------
// Generative UI — registra componentes indexados por ui_component string
// ---------------------------------------------------------------------------

const UI_COMPONENTS: Record<
  string,
  React.ComponentType<any> // eslint-disable-line @typescript-eslint/no-explicit-any
> = {
  file_diff: ({ diff, file_path }: { diff: string; file_path?: string }) => (
    <FileDiffViewer content={diff} fileName={file_path} />
  ),
  search_table: ({
    results,
    query,
  }: {
    results: SearchResult[];
    query?: string;
  }) => (
    <SearchResultsTable results={results} query={query} />
  ),
  web_results: ({ results }: { results: WebSearchResult[] }) => (
    <WebResultsCard results={results} />
  ),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isComplexValue(value: unknown): boolean {
  return Array.isArray(value) || (typeof value === "object" && value !== null);
}

function detectLanguage(toolName?: string, content?: string): string {
  if (!toolName && !content) return "text";
  const name = toolName?.toLowerCase() ?? "";
  if (name === "file_read" || name === "file_write") {
    // Try to guess from content
    if (content?.trim().startsWith("{") || content?.trim().startsWith("["))
      return "json";
    if (content?.includes("def ") || content?.includes("import "))
      return "python";
    if (content?.includes("function ") || content?.includes("const "))
      return "ts";
  }
  return "text";
}

// ---------------------------------------------------------------------------
// Render-hint dispatcher
// ---------------------------------------------------------------------------

interface DispatchProps {
  toolName?: string;
  hint: RenderHint;
  parsed: unknown;
  raw: string;
}

function DispatchByHint({ toolName, hint, parsed, raw }: DispatchProps) {
  // search_results
  if (hint === "search_results") {
    const results = (
      Array.isArray(parsed)
        ? parsed
        : (parsed as { results?: SearchResult[]; docs?: SearchResult[] })?.results ?? 
          (parsed as { results?: SearchResult[]; docs?: SearchResult[] })?.docs ?? []
    ) as SearchResult[];
    return <SearchResultsTable results={results} />;
  }

  // web_results
  if (hint === "web_results") {
    const results = (
      Array.isArray(parsed)
        ? parsed
        : (parsed as { results?: WebSearchResult[] })?.results ?? []
    ) as WebSearchResult[];
    // fetch_url returns plain text, not an array
    if (typeof parsed === "string") {
      return (
        <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto p-2">
          {parsed}
        </div>
      );
    }
    return <WebResultsCard results={results} />;
  }

  // diff
  if (hint === "diff") {
    const p = parsed as { diff?: string; file?: string; file_path?: string };
    const diff = p?.diff ?? raw;
    const filePath = p?.file ?? p?.file_path;
    // If it's just a success string, show plain text
    if (!diff.includes("\n") || (!diff.includes("+") && !diff.includes("-"))) {
      return <span className="text-sm text-gray-700">{raw}</span>;
    }
    return <FileDiffViewer content={diff} fileName={filePath} />;
  }

  // code_block
  if (hint === "code_block") {
    const lang = detectLanguage(toolName, raw);
    return (
      <div className="rounded-md overflow-hidden bg-gray-900">
        <SyntaxHighlighter language={lang}>{raw}</SyntaxHighlighter>
      </div>
    );
  }

  // terminal_output
  if (hint === "terminal_output") {
    const command = (parsed as { command?: string })?.command;
    return <TerminalBlock content={raw} command={command} />;
  }

  // queue_progress
  if (hint === "queue_progress") {
    const p = parsed as QueueProgress;
    return (
      <QueueProgressCard
        total={p?.total ?? p?.count}
        processed={p?.processed ?? p?.success_count}
        status={p?.status}
        queue_ids={p?.queue_ids}
        message={p?.message}
      />
    );
  }

  // queue_badge
  if (hint === "queue_badge") {
    const p = parsed as QueueProgress;
    return (
      <QueueProgressCard
        queue_id={p?.queue_id ?? p?.id}
        status={p?.status}
        message={p?.message}
      />
    );
  }

  // markdown
  if (hint === "markdown") {
    const p = parsed as WorkspaceDescribeResult;
    const content = p?.manifest ?? p?.summary ?? p?.content ?? raw;
    if (typeof content === "string" && content.trim()) {
      return (
        <div className="text-sm prose prose-sm max-w-none">
          <MarkdownText>{content}</MarkdownText>
        </div>
      );
    }
  }

  // table — render as key/value rows (generic)
  if (hint === "table") {
    const items = (
      Array.isArray(parsed)
        ? parsed
        : (parsed as any)?.workspaces ??
          (parsed as any)?.items ??
          (parsed as any)?.results ??
          null
    ) as Record<string, unknown>[] | null;

    if (Array.isArray(items) && items.length > 0) {
      const headers = Object.keys(items[0]);
      return (
        <div className="overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full text-xs divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {headers.map((h) => (
                  <th
                    key={h}
                    className="px-3 py-2 text-left font-medium text-gray-700 whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  {headers.map((h) => (
                    <td
                      key={h}
                      className="px-3 py-1.5 text-gray-600 max-w-xs truncate"
                    >
                      {String(row[h] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  }

  // json (fallback) — delegate to default JSON renderer
  return null;
}

// ---------------------------------------------------------------------------
// ToolCalls component (arguments display)
// ---------------------------------------------------------------------------

export function ToolCalls({
  toolCalls,
}: {
  toolCalls: AIMessage["tool_calls"];
}) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="space-y-4 w-full max-w-4xl">
      {toolCalls.map((tc, idx) => {
        const args = tc.args as Record<string, unknown>;
        const hasArgs = Object.keys(args).length > 0;
        return (
          <div
            key={idx}
            className="border border-gray-200 rounded-lg overflow-hidden"
          >
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <h3 className="font-medium text-gray-900">
                {tc.name}
                {tc.id && (
                  <code className="ml-2 text-sm bg-gray-100 px-2 py-1 rounded">
                    {tc.id}
                  </code>
                )}
              </h3>
            </div>
            {hasArgs ? (
              <table className="min-w-full divide-y divide-gray-200">
                <tbody className="divide-y divide-gray-200">
                  {Object.entries(args).map(([key, value], argIdx) => (
                    <tr key={argIdx}>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900 whitespace-nowrap">
                        {key}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">
                        {isComplexValue(value) ? (
                          <code className="bg-gray-50 rounded px-2 py-1 font-mono text-sm break-all">
                            {JSON.stringify(value, null, 2)}
                          </code>
                        ) : (
                          String(value)
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <code className="text-sm block p-3">{"{}"}</code>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolResult component — Discovery Layer + Generative UI dispatch
// ---------------------------------------------------------------------------

export function ToolResult({ message }: { message: ToolMessage }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const toolSchema = useToolSchema();

  const toolName = message.name;
  const raw =
    typeof message.content === "string"
      ? message.content
      : JSON.stringify(message.content);

  // Parse JSON output
  let parsed: unknown = null;
  let isJson = false;
  try {
    if (typeof message.content === "string") {
      parsed = JSON.parse(message.content);
      isJson = true;
    }
  } catch {
    parsed = message.content;
  }

  // ── Layer 1: Generative UI (ui_component in JSON output) ──────────────────
  if (
    isJson &&
    parsed !== null &&
    typeof parsed === "object" &&
    !Array.isArray(parsed)
  ) {
    const p = parsed as Record<string, unknown>;
    const uiComponent = p.ui_component as string | undefined;
    if (uiComponent && uiComponent in UI_COMPONENTS) {
      const Component = UI_COMPONENTS[uiComponent];
      const data = (p.data as Record<string, unknown>) ?? p;
      return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <ToolResultHeader name={toolName} callId={message.tool_call_id} />
          <div className="p-3">
            <Component {...data} />
          </div>
        </div>
      );
    }
  }

  // ── Layer 2: Discovery Layer (render_hint from schema) ────────────────────
  const hint = getRenderHint(toolSchema, toolName ?? "");
  if (hint !== "json") {
    const customRender = (
      <DispatchByHint
        toolName={toolName}
        hint={hint}
        parsed={parsed}
        raw={raw}
      />
    );
    if (customRender) {
      return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <ToolResultHeader name={toolName} callId={message.tool_call_id} />
          <div className="p-3">{customRender}</div>
        </div>
      );
    }
  }

  // ── Layer 3: JSON fallback (original behavior) ────────────────────────────
  const contentStr = isJson ? JSON.stringify(parsed, null, 2) : raw;
  const contentLines = contentStr.split("\n");
  const shouldTruncate = contentLines.length > 4 || contentStr.length > 500;
  const displayedContent =
    shouldTruncate && !isExpanded
      ? contentStr.length > 500
        ? contentStr.slice(0, 500) + "..."
        : contentLines.slice(0, 4).join("\n") + "\n..."
      : contentStr;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <ToolResultHeader name={toolName} callId={message.tool_call_id} />
      <motion.div
        className="min-w-full bg-gray-100"
        initial={false}
        animate={{ height: "auto" }}
        transition={{ duration: 0.3 }}
      >
        <div className="p-3">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={isExpanded ? "expanded" : "collapsed"}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
            >
              {isJson && parsed !== null ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <tbody className="divide-y divide-gray-200">
                    {(Array.isArray(parsed)
                      ? isExpanded
                        ? parsed
                        : parsed.slice(0, 5)
                      : Object.entries(parsed as object)
                    ).map((item, argIdx) => {
                      const [key, value] = Array.isArray(parsed)
                        ? [argIdx, item]
                        : [item[0], item[1]];
                      return (
                        <tr key={argIdx}>
                          <td className="px-4 py-2 text-sm font-medium text-gray-900 whitespace-nowrap">
                            {key}
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-500">
                            {isComplexValue(value) ? (
                              <code className="bg-gray-50 rounded px-2 py-1 font-mono text-sm break-all">
                                {JSON.stringify(value, null, 2)}
                              </code>
                            ) : (
                              String(value)
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <code className="text-sm block">{displayedContent}</code>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
        {((shouldTruncate && !isJson) ||
          (isJson &&
            Array.isArray(parsed) &&
            (parsed as unknown[]).length > 5)) && (
          <motion.button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full py-2 flex items-center justify-center border-t-[1px] border-gray-200 text-gray-500 hover:text-gray-600 hover:bg-gray-50 transition-all ease-in-out duration-200 cursor-pointer"
            initial={{ scale: 1 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isExpanded ? <ChevronUp /> : <ChevronDown />}
          </motion.button>
        )}
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared header for tool result cards
// ---------------------------------------------------------------------------

function ToolResultHeader({
  name,
  callId,
}: {
  name?: string;
  callId?: string;
}) {
  return (
    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {name ? (
          <h3 className="font-medium text-gray-900">
            Tool Result:{" "}
            <code className="bg-gray-100 px-2 py-1 rounded">{name}</code>
          </h3>
        ) : (
          <h3 className="font-medium text-gray-900">Tool Result</h3>
        )}
        {callId && (
          <code className="ml-2 text-sm bg-gray-100 px-2 py-1 rounded">
            {callId}
          </code>
        )}
      </div>
    </div>
  );
}
