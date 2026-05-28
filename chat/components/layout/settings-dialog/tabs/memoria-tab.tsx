"use client";

/**
 * MemoriaTab — lista e gerencia memórias persistentes do usuário (Bloco N).
 *
 * Funcionalidades:
 * - Lista todas as memórias do usuário (fetch GET /api/memory)
 * - Edita conteúdo de uma memória inline (PUT /api/memory/:key)
 * - Deleta uma memória específica (DELETE /api/memory/:key)
 * - Limpa todas as memórias (DELETE /api/memory) com confirmação
 */

import { Brain, Edit2, Loader2, Trash2 } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";

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

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function MemoriaTab() {
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

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMemories();
      setMemories(data.memories);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao carregar memórias",
      );
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao deletar");
    } finally {
      setDeletingKey(null);
    }
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await clearAllMemories();
      setMemories([]);
      setTotal(0);
      setClearConfirmOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao limpar memórias");
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

  return (
    <div className="space-y-4">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <p className="text-sm font-medium">
            {total > 0
              ? `${total} memória${total > 1 ? "s" : ""}`
              : "Nenhuma memória salva"}
          </p>
          <p className="text-xs text-muted-foreground">
            O que o Vectora aprendeu sobre você nessas conversas
          </p>
        </div>
        {memories.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setClearConfirmOpen(true)}
          >
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            Limpar tudo
          </Button>
        )}
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
            O Vectora ainda não salvou memórias sobre você
          </p>
          <p className="text-xs text-muted-foreground/70 max-w-[260px]">
            Ao longo das conversas, o agente salva informações relevantes para
            personalizar futuras respostas.
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
                    Salvar
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditingKey(null)}
                    disabled={saving}
                    className="h-7 text-xs"
                  >
                    Cancelar
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
                  Editar
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
                  Deletar
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Dialog de confirmação — limpar tudo */}
      <Dialog open={clearConfirmOpen} onOpenChange={setClearConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Limpar todas as memórias?</DialogTitle>
            <DialogDescription>
              Esta ação é irreversível. O Vectora não se lembrará de nada que
              aprendeu sobre você nas conversas anteriores.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setClearConfirmOpen(false)}
              disabled={clearing}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleClearAll}
              disabled={clearing}
            >
              {clearing && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Limpar tudo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
