"use client";

/**
 * MarkdownPreviewDialog — visualiza arquivos .md em modal, render GitHub.
 */

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MarkdownView } from "@/components/workbench/markdown-view";
import { useT } from "@/lib/i18n";

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
  const t = useT();
  const [content, setContent] = useState<string | null>(initialContent ?? null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!open || !filePath || initialContent) return;

    setIsLoading(true);
    fetch(filePath)
      .then((res) => res.text())
      .then(setContent)
      .catch(() => setContent(null))
      .finally(() => setIsLoading(false));
  }, [open, filePath, initialContent]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="truncate">
            {filePath || t("workbench.preview_md.title")}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-auto custom-scrollbar">
          {isLoading ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground">
              {t("workbench.preview_md.loading")}
            </div>
          ) : content ? (
            <MarkdownView content={content} />
          ) : (
            <div className="p-4 text-muted-foreground">
              {t("workbench.preview_md.empty")}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
