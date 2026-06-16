"use client";

/**
 * MarkdownPreviewDialog — visualiza arquivos .md em modal.
 *
 * Usa react-markdown + remark-gfm para suporte a tabelas, strikethrough, etc.
 */

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface MarkdownPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filePath?: string;
  content?: string;
}

export function MarkdownPreviewDialog({
  open,
  onOpenChange,
  filePath,
  content: initialContent,
}: MarkdownPreviewDialogProps) {
  const [content, setContent] = useState<string | null>(initialContent ?? null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!open || !filePath || initialContent) return;

    setIsLoading(true);
    fetch(filePath)
      .then((res) => res.text())
      .then(setContent)
      .catch(() => setContent("Failed to load markdown"))
      .finally(() => setIsLoading(false));
  }, [open, filePath, initialContent]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="truncate">
            {filePath || "Markdown Preview"}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-auto custom-scrollbar prose dark:prose-invert max-w-none">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <span className="text-muted-foreground">Loading...</span>
            </div>
          ) : content ? (
            <div className="p-4 bg-background text-sm">
              {/* TODO: renderizar com react-markdown + remark-gfm */}
              <pre className="whitespace-pre-wrap">{content}</pre>
            </div>
          ) : (
            <div className="p-4 text-muted-foreground">No content</div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
