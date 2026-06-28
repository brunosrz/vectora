"use client";

/**
 * RagSettingsPanel — gear + popover de configuração do RAG na aba de memória.
 *
 * Controla (persistido no backend via /rag/settings): reranker on/off + top_k,
 * providers de rerank/embedding, tipos de arquivo a ingerir. Lista as coleções
 * (/rag/collections) com botão de apagar. Caso de uso paralelo ao Context Graph:
 * usar o RAG para código enquanto o grafo cuida dos markdowns.
 */

import { useCallback, useEffect, useState } from "react";
import { Settings2, Trash2, RefreshCw } from "lucide-react";

import {
  ALL_GRAPH_FILE_TYPES,
  type GraphFileType,
} from "@/lib/stores/context-graph-settings-store";
import { useToastStore } from "@/lib/stores/toast-store";
import { WorkbenchSlidePanel } from "@/components/workbench/workbench-slide-panel";
import { m } from "@/lib/paraglide/messages";

interface RagSettings {
  reranker_enabled: boolean;
  reranker_top_k: number;
  rerank_provider: string;
  embed_provider: string;
  ingest_file_types: string[];
}

interface Collection {
  name: string;
  count: number | null;
}

const DEFAULTS: RagSettings = {
  reranker_enabled: true,
  reranker_top_k: 5,
  rerank_provider: "auto",
  embed_provider: "auto",
  ingest_file_types: [],
};

const PROVIDERS = ["auto", "cohere", "voyage"] as const;

export function RagSettingsPanel() {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState<RagSettings>(DEFAULTS);
  const [collections, setCollections] = useState<Collection[]>([]);

  const loadCollections = useCallback(async () => {
    try {
      const res = await fetch("/rag/collections");
      if (!res.ok) return;
      const data = (await res.json()) as { collections?: Collection[] };
      setCollections(Array.isArray(data.collections) ? data.collections : []);
    } catch {
      /* sem rede: lista vazia */
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/rag/settings");
        if (res.ok && alive) {
          const data = (await res.json()) as Partial<RagSettings>;
          setSettings({ ...DEFAULTS, ...data });
        }
      } catch {
        /* mantém defaults */
      }
    })();
    void loadCollections();
    return () => {
      alive = false;
    };
  }, [open, loadCollections]);

  const patch = useCallback(async (changes: Partial<RagSettings>) => {
    setSettings((s) => ({ ...s, ...changes }));
    try {
      const res = await fetch("/rag/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(changes),
      });
      if (res.ok) {
        const data = (await res.json()) as RagSettings;
        setSettings({ ...DEFAULTS, ...data });
      }
    } catch {
      /* offline: mantém o estado otimista */
    }
  }, []);

  const deleteCollection = useCallback(async (name: string) => {
    if (!window.confirm(m.rag_collection_delete_confirm({ name }))) return;
    try {
      const res = await fetch(`/rag/collections/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setCollections((c) => c.filter((x) => x.name !== name));
      } else {
        useToastStore.getState().error(m.rag_collection_delete());
      }
    } catch {
      useToastStore.getState().error(m.rag_collection_delete());
    }
  }, []);

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={m.rag_settings_title()}
        title={m.rag_settings_title()}
        aria-expanded={open}
        data-testid="rag-settings-btn"
        className="flex items-center justify-center h-6 w-6 rounded text-muted-foreground hover:text-foreground hover:bg-muted/50"
      >
        <Settings2 className="h-3.5 w-3.5" />
      </button>

      <WorkbenchSlidePanel
        open={open}
        onClose={() => setOpen(false)}
        title={m.rag_settings_title()}
        testId="rag-settings-panel"
      >
        <div className="space-y-3 text-xs">
          {/* Reranker on/off + top_k */}
          <label className="flex items-center justify-between gap-2 cursor-pointer select-none">
            <span className="text-foreground">{m.rag_reranker_enabled()}</span>
            <input
              type="checkbox"
              checked={settings.reranker_enabled}
              onChange={(e) =>
                void patch({ reranker_enabled: e.target.checked })
              }
              className="accent-[var(--color-primary)]"
            />
          </label>
          <p className="-mt-1.5 text-[10px] text-muted-foreground">
            {m.rag_reranker_help()}
          </p>
          <label className="flex items-center justify-between gap-2">
            <span className="text-foreground">{m.rag_reranker_top_k()}</span>
            <input
              type="number"
              min={1}
              max={50}
              value={settings.reranker_top_k}
              disabled={!settings.reranker_enabled}
              onChange={(e) =>
                void patch({
                  reranker_top_k: Math.max(1, Number(e.target.value) || 1),
                })
              }
              className="w-16 bg-background border border-border/60 rounded px-1.5 py-0.5 text-right disabled:opacity-40"
            />
          </label>

          {/* Providers */}
          <label className="flex items-center justify-between gap-2">
            <span className="text-foreground">{m.rag_rerank_provider()}</span>
            <ProviderSelect
              value={settings.rerank_provider}
              onChange={(v) => void patch({ rerank_provider: v })}
            />
          </label>
          <label className="flex items-center justify-between gap-2">
            <span className="text-foreground">{m.rag_embed_provider()}</span>
            <ProviderSelect
              value={settings.embed_provider}
              onChange={(v) => void patch({ embed_provider: v })}
            />
          </label>

          {/* Tipos de arquivo a ingerir */}
          <div>
            <p className="font-medium text-foreground">
              {m.graph_settings_filetypes()}
            </p>
            <div className="mt-1 space-y-1">
              {ALL_GRAPH_FILE_TYPES.map((t: GraphFileType) => (
                <label
                  key={t}
                  className="flex items-center gap-2 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={
                      settings.ingest_file_types.length === 0 ||
                      settings.ingest_file_types.includes(t)
                    }
                    onChange={() => {
                      const cur =
                        settings.ingest_file_types.length === 0
                          ? [...ALL_GRAPH_FILE_TYPES]
                          : settings.ingest_file_types;
                      const next = cur.includes(t)
                        ? cur.filter((x) => x !== t)
                        : [...cur, t];
                      void patch({ ingest_file_types: next });
                    }}
                    className="accent-[var(--color-primary)]"
                  />
                  <span className="text-foreground">
                    {t === "code"
                      ? m.graph_filetype_code()
                      : t === "document"
                        ? m.graph_filetype_document()
                        : m.graph_filetype_paper()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Coleções */}
          <div className="border-t border-border/60 pt-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-foreground">
                {m.rag_collections_title()}
              </p>
              <button
                onClick={() => void loadCollections()}
                aria-label="reload"
                className="text-muted-foreground hover:text-foreground"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            </div>
            {collections.length === 0 ? (
              <p className="mt-1 text-[10px] text-muted-foreground">
                {m.rag_collections_empty()}
              </p>
            ) : (
              <ul className="mt-1 space-y-1">
                {collections.map((c) => (
                  <li
                    key={c.name}
                    className="flex items-center justify-between gap-2 rounded border border-border/60 px-2 py-1"
                  >
                    <span className="min-w-0 truncate text-foreground">
                      {c.name}
                      {c.count != null && (
                        <span className="ml-1 text-[10px] text-muted-foreground">
                          {m.rag_collection_count({ n: c.count })}
                        </span>
                      )}
                    </span>
                    <button
                      onClick={() => void deleteCollection(c.name)}
                      aria-label={m.rag_collection_delete()}
                      title={m.rag_collection_delete()}
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </WorkbenchSlidePanel>
    </>
  );
}

function ProviderSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-background border border-border/60 rounded px-1.5 py-0.5 text-foreground"
    >
      {PROVIDERS.map((p) => (
        <option key={p} value={p}>
          {p === "auto"
            ? m.rag_provider_auto()
            : p === "cohere"
              ? m.rag_provider_cohere()
              : m.rag_provider_voyage()}
        </option>
      ))}
    </select>
  );
}
