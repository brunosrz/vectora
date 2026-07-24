"use client";

/**
 * MemorySection — Memory Library: GET /rag-library/catalog,
 * POST /rag-library/install. Buckets RAG pré-vetorizados publicados pela
 * comunidade — download sempre grátis, sem gate de tier.
 *
 * "Publicar" não tem UI ainda: exige um `session_token` de conta
 * vectora.company que o backend local não tem como obter hoje (não existe
 * fluxo de login desktop↔company) — nota explicando isso em vez de um botão
 * que falha sempre.
 */

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Database, Download, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { m } from "@/lib/paraglide/messages";
import { useLibraryStore, type MemoryBucket } from "@/lib/stores/library-store";

async function installBucket(
  bucketId: string,
): Promise<{ status: string; error?: string }> {
  const res = await fetch("/rag-library/install", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bucket_id: bucketId }),
  });
  return res.json();
}

function BucketCard({
  bucket,
  currentEmbedModel,
}: {
  bucket: MemoryBucket;
  currentEmbedModel: string | null;
}) {
  const [busy, setBusy] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const incompatible =
    !!currentEmbedModel &&
    !!bucket.embed_model &&
    bucket.embed_model !== currentEmbedModel;

  const handleInstall = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await installBucket(bucket.id);
      if (result.status === "error") {
        setError(result.error ?? m.library_memory_error_install());
        return;
      }
      setInstalled(true);
    } catch {
      setError(m.library_memory_error_install());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
          <Database className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{bucket.name}</span>
            {bucket.verified && (
              <Badge
                variant="secondary"
                className="text-[10px] h-4 px-1.5 gap-1"
              >
                <CheckCircle2 className="w-2.5 h-2.5" />
                {m.library_memory_verified_badge()}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {bucket.description}
          </p>
          <p className="text-[10px] text-muted-foreground/80">
            {m.library_memory_embed_model({ model: bucket.embed_model })}
            {" · "}
            {m.library_memory_downloads({ count: bucket.downloads_count })}
          </p>
        </div>
        <Button
          variant={installed ? "outline" : "default"}
          size="sm"
          className="h-7 text-xs shrink-0"
          onClick={handleInstall}
          disabled={busy || installed}
        >
          {busy ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : installed ? (
            <>
              <CheckCircle2 className="w-3 h-3 mr-1.5" />
              {m.library_memory_installed()}
            </>
          ) : (
            <>
              <Download className="w-3 h-3 mr-1.5" />
              {m.library_memory_install()}
            </>
          )}
        </Button>
      </div>
      {incompatible && !installed && (
        <p className="text-[10px] text-amber-500">
          {m.library_memory_incompatible({ model: bucket.embed_model })}
        </p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

export function MemorySection({
  query,
  onCountChange,
  currentEmbedModel = null,
}: {
  query: string;
  onCountChange: (count: number) => void;
  currentEmbedModel?: string | null;
}) {
  const buckets = useLibraryStore((s) => s.memoryItems);
  const loading = useLibraryStore((s) => s.memoryLoading);
  const ensureMemoryLoaded = useLibraryStore((s) => s.ensureMemoryLoaded);

  useEffect(() => {
    void ensureMemoryLoaded();
  }, [ensureMemoryLoaded]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return buckets;
    return buckets.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.description.toLowerCase().includes(q),
    );
  }, [buckets, query]);

  useEffect(() => {
    onCountChange(filtered.length);
  }, [filtered.length, onCountChange]);

  if (loading) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-2 py-1">
      {filtered.length === 0 ? (
        <p className="py-4 text-xs text-muted-foreground text-center">
          {m.library_empty_memory()}
        </p>
      ) : (
        filtered.map((bucket) => (
          <BucketCard
            key={bucket.id}
            bucket={bucket}
            currentEmbedModel={currentEmbedModel}
          />
        ))
      )}
      <p className="text-[10px] text-muted-foreground/70 pt-1">
        {m.library_memory_publish_note()}
      </p>
    </div>
  );
}
