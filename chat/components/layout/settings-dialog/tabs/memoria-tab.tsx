"use client";

/**
 * MemoriaTab — lista e gerencia memórias persistentes do usuário (Bloco N).
 *
 * Funcionalidades:
 * - Lista todas as memórias do usuário (fetch GET /api/memory)
 * - Adiciona memória manualmente (POST /api/memory)
 * - Edita conteúdo de uma memória inline (PUT /api/memory/:key)
 * - Deleta uma memória específica (DELETE /api/memory/:key)
 * - Limpa todas as memórias (DELETE /api/memory) com confirmação
 */

import { Brain, Edit2, Loader2, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface MemoryItem {
  key: string;
  content: string;
  metadata: Record<string, unknown>;
  updated_at: string;
}

interface ListMemoriesResponse {
  memories: MemoryItem[];
  total: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchMemories(
  limit = 50,
  offset = 0,
): Promise<ListMemoriesResponse> {
  const res = await fetch(`/api/memory/?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function updateMemory(key: string, content: string): Promise<void> {
  const res = await fetch(`/api/memory/${encodeURIComponent(key)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function deleteMemory(key: string): Promise<void> {
  const res = await fetch(`/api/memory/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function clearAllMemories(): Promise<void> {
  const res = await fetch(`/api/memory/`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function createMemory(key: string, content: string): Promise<void> {
  const res = await fetch(`/api/memory/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, content }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(
      (data as { detail?: string }).detail ?? `Erro ${res.status}`,
    );
  }
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function MemoriaTab() {
  const t = useT();

  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estado de edição
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  // Estado de exclusão
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [clearing, setClearing] = useState(false);

  // Estado de criação
  const [addOpen, setAddOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newContent, setNewContent] = useState("");
  const [adding, setAdding] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMemories();
      setMemories(data.memories);
      setTotal(data.total);
    } catch {
      setError(t("memory.error_load"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleEditStart = (mem: MemoryItem) => {
    setEditingKey(mem.key);
    setEditContent(mem.content);
  };

  const handleEditSave = async () => {
    if (!editingKey) return;
    setSaving(true);
    try {
      await updateMemory(editingKey, editContent);
      setMemories((prev) =>
        prev.map((m) =>
          m.key === editingKey ? { ...m, content: editContent } : m,
        ),
      );
      setEditingKey(null);
    } catch {
      setError(t("memory.error_save"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    setDeletingKey(key);
    try {
      await deleteMemory(key);
      setMemories((prev) => prev.filter((m) => m.key !== key));
      setTotal((prev) => prev - 1);
    } catch {
      setError(t("memory.error_delete"));
    } finally {
      setDeletingKey(null);
    }
  };

  const handleAddMemory = async () => {
    if (!newKey.trim() || !newContent.trim()) return;
    setAdding(true);
    try {
      await createMemory(newKey.trim(), newContent.trim());
      await load();
      setAddOpen(false);
      setNewKey("");
      setNewContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("memory.error_create"));
    } finally {
      setAdding(false);
    }
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await clearAllMemories();
      setMemories([]);
      setTotal(0);
      setClearConfirmOpen(false);
    } catch {
      setError(t("memory.error_clear"));
    } finally {
      setClearing(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const headerTitle =
    total > 0
      ? t(total === 1 ? "memory.count_one" : "memory.count_many", { n: total })
      : t("memory.empty_title");

  return (
    <div className="space-y-4">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <p className="text-sm font-medium">{headerTitle}</p>
          <p className="text-xs text-muted-foreground">
            {t("memory.subtitle")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAddOpen(true)}>
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            {t("memory.add")}
          </Button>
          {memories.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:text-destructive dark:hover:text-destructive"
              onClick={() => setClearConfirmOpen(true)}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              {t("memory.clear_all")}
            </Button>
          )}
        </div>
      </div>

      {/* Erro */}
      {error && (
        <p className="text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-md">
          {error}
        </p>
      )}

      {/* Empty state */}
      {memories.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
          <Brain className="w-10 h-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">
            {t("memory.empty_hint")}
          </p>
          <p className="text-xs text-muted-foreground/70 max-w-[260px]">
            {t("memory.empty_hint2")}
          </p>
        </div>
      )}

      {/* Lista de memórias */}
      <div className="space-y-2">
        {memories.map((mem) => (
          <div
            key={mem.key}
            className="rounded-lg border bg-card p-3 space-y-2"
          >
            {/* Key + data */}
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-mono text-muted-foreground truncate">
                {mem.key}
              </span>
              {mem.updated_at && (
                <span className="text-[10px] text-muted-foreground/60 shrink-0">
                  {new Date(mem.updated_at).toLocaleDateString("pt-BR")}
                </span>
              )}
            </div>

            {/* Conteúdo ou editor inline */}
            {editingKey === mem.key ? (
              <div className="space-y-2">
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="text-sm min-h-[80px] resize-none"
                  autoFocus
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleEditSave}
                    disabled={saving}
                    className="h-7 text-xs"
                  >
                    {saving && (
                      <Loader2 className="w-3 h-3 animate-spin mr-1" />
                    )}
                    {t("memory.save")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditingKey(null)}
                    disabled={saving}
                    className="h-7 text-xs"
                  >
                    {t("memory.cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-foreground/90 line-clamp-3">
                {mem.content}
              </p>
            )}

            {/* Ações */}
            {editingKey !== mem.key && (
              <div className="flex gap-1.5 pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs text-muted-foreground"
                  onClick={() => handleEditStart(mem)}
                >
                  <Edit2 className="w-3 h-3 mr-1" />
                  {t("memory.edit")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
                  onClick={() => handleDelete(mem.key)}
                  disabled={deletingKey === mem.key}
                >
                  {deletingKey === mem.key ? (
                    <Loader2 className="w-3 h-3 animate-spin mr-1" />
                  ) : (
                    <Trash2 className="w-3 h-3 mr-1" />
                  )}
                  {t("memory.delete")}
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Dialog — adicionar memória */}
      <Dialog
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open);
          if (!open) {
            setNewKey("");
            setNewContent("");
            setError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("memory.add_title")}</DialogTitle>
            <DialogDescription>{t("memory.add_desc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-1">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                {t("memory.add_key_label")}
              </label>
              <Input
                placeholder={t("memory.add_key_placeholder")}
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="text-sm"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                {t("memory.add_content_label")}
              </label>
              <Textarea
                placeholder={t("memory.add_content_placeholder")}
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                className="text-sm min-h-[80px] resize-none"
              />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAddOpen(false)}
              disabled={adding}
            >
              {t("memory.cancel")}
            </Button>
            <Button
              onClick={handleAddMemory}
              disabled={adding || !newKey.trim() || !newContent.trim()}
            >
              {adding && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("memory.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog de confirmação — limpar tudo */}
      <Dialog open={clearConfirmOpen} onOpenChange={setClearConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("memory.clear_title")}</DialogTitle>
            <DialogDescription>{t("memory.clear_desc")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setClearConfirmOpen(false)}
              disabled={clearing}
            >
              {t("memory.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={handleClearAll}
              disabled={clearing}
            >
              {clearing && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("memory.clear_all")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
