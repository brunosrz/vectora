"use client";

/**
 * StorageTab — navegação read-only do filesystem.
 *
 * Mostra a árvore completa do workspace sem opções de edição/delete.
 * Clique em arquivo abre em preview (se suportado).
 * Reutiliza tree logic do files-tab.
 */

import { useCallback, useState } from "react";
import { ChevronRight, File, Folder, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

interface StorageTabProps {
  threadId: string;
  onFileSelect?: (path: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: TreeNode[];
  isExpanded?: boolean;
  isLoading?: boolean;
}

export function StorageTab({ threadId, onFileSelect }: StorageTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  const [tree, setTree] = useState<TreeNode | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Carrega árvore de diretórios inicial ao montar
  const loadTree = useCallback(async () => {
    if (!wsId) {
      setError(t("workbench.files.no_workspace"));
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/tree?path=.`,
      );
      if (!res.ok) throw new Error("Failed to load tree");

      const data = (await res.json()) as TreeNode;
      setTree(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("workbench.files.no_workspace"),
      );
    } finally {
      setIsLoading(false);
    }
  }, [wsId, t]);

  // Expande/contrai nó
  const toggleNode = useCallback((path: string) => {
    setTree((prev) => {
      if (!prev) return prev;
      return updateNode(prev, path, (n) => ({
        ...n,
        isExpanded: !n.isExpanded,
      }));
    });
  }, []);

  // Carrega filhos de um diretório (lazy load)
  const loadChildren = useCallback(
    async (dirPath: string) => {
      if (!wsId) return;

      setTree((prev) => {
        if (!prev) return prev;
        return updateNode(prev, dirPath, (n) => ({ ...n, isLoading: true }));
      });

      try {
        const res = await fetch(
          `/workspaces/${encodeURIComponent(wsId)}/tree?path=${encodeURIComponent(dirPath)}`,
        );
        if (!res.ok) throw new Error("Failed to load children");

        const data = (await res.json()) as TreeNode;

        setTree((prev) => {
          if (!prev) return prev;
          return updateNode(prev, dirPath, (n) => ({
            ...n,
            children: data.children,
            isLoading: false,
          }));
        });
      } catch {
        setTree((prev) => {
          if (!prev) return prev;
          return updateNode(prev, dirPath, (n) => ({ ...n, isLoading: false }));
        });
      }
    },
    [wsId],
  );

  const handleNodeClick = (node: TreeNode) => {
    if (node.type === "dir") {
      if (node.isExpanded && node.children?.length === 0) {
        loadChildren(node.path);
      }
      toggleNode(node.path);
    } else {
      onFileSelect?.(node.path);
    }
  };

  if (isLoading && !tree) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-destructive">
        {error}
        <button
          onClick={loadTree}
          className="mt-2 inline-block rounded bg-primary/10 px-2 py-1 text-primary hover:bg-primary/20"
        >
          {t("workbench.files.refresh")}
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto custom-scrollbar px-1 py-2">
        {tree && <TreeNode node={tree} onNodeClick={handleNodeClick} />}
      </div>
    </div>
  );
}

interface TreeNodeProps {
  node: TreeNode;
  depth?: number;
  onNodeClick: (node: TreeNode) => void;
}

function TreeNode({ node, depth = 0, onNodeClick }: TreeNodeProps) {
  return (
    <div>
      <button
        onClick={() => onNodeClick(node)}
        className={cn(
          "w-full flex items-center gap-1 px-2 py-1 text-xs font-medium text-foreground/80 hover:bg-accent transition-colors rounded text-left",
          "hover:text-foreground",
        )}
        style={{ paddingLeft: `${12 + depth * 12}px` }}
      >
        {node.type === "dir" && (
          <ChevronRight
            className={cn(
              "h-3.5 w-3.5 shrink-0 transition-transform",
              node.isExpanded && "rotate-90",
            )}
          />
        )}
        {node.type === "file" && <div className="w-3.5" />}
        {node.type === "dir" ? (
          <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <File className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className="truncate">{node.name}</span>
        {node.isLoading && (
          <Loader2 className="h-3.5 w-3.5 animate-spin ml-auto" />
        )}
      </button>

      {node.isExpanded && node.children && node.children.length > 0 && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              onNodeClick={onNodeClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Helper: atualiza nó na árvore recursivamente
function updateNode(
  tree: TreeNode,
  targetPath: string,
  update: (n: TreeNode) => TreeNode,
): TreeNode {
  if (tree.path === targetPath) {
    return update(tree);
  }
  if (tree.children) {
    return {
      ...tree,
      children: tree.children.map((child) =>
        updateNode(child, targetPath, update),
      ),
    };
  }
  return tree;
}
