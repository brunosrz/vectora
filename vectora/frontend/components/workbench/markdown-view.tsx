"use client";

/**
 * MarkdownView — render de markdown estilo GitHub (read-only).
 *
 * Reutilizado pelo visualizador embarcado (`file-viewer` para `.md`) e pelo
 * diálogo de preview. Usa react-markdown + remark-gfm (tabelas, task lists,
 * strikethrough) com as classes `prose` do Tailwind Typography.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownView({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none p-4 prose-pre:bg-muted prose-pre:text-foreground prose-code:before:content-none prose-code:after:content-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
