"use client";

/**
 * EnvsTab — tabela de variáveis de ambiente personalizadas do usuário.
 * Cada variável sobrescreve o env do sistema apenas para as requests deste usuário.
 *
 * Backend: GET/POST /auth/envs + DELETE /auth/envs/:key.
 * Valores chegam mascarados na resposta — nunca expostos ao cliente.
 */

import { KeyRound, Loader2, Plus, Trash2 } from "lucide-react";
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
import { useT } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// Tipos + API helpers
// ---------------------------------------------------------------------------

interface EnvsResponse {
  envs: Record<string, string>; // valores mascarados ("••••••••")
  keys: string[];
}

async function fetchEnvs(): Promise<EnvsResponse> {
  const res = await fetch("/auth/envs");
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function setEnv(key: string, value: string): Promise<void> {
  const res = await fetch("/auth/envs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value }),
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function deleteEnv(key: string): Promise<void> {
  const res = await fetch(`/auth/envs/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function EnvsTab() {
  const t = useT();

  const [envs, setEnvs] = useState<Record<string, string>>({});
  const [keys, setKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [saving, setSaving] = useState(false);

  const [deletingKey, setDeletingKey] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEnvs();
      setEnvs(data.envs ?? {});
      setKeys(data.keys ?? []);
    } catch {
      setError(t("envs.error_load"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleAdd = async () => {
    if (!newKey.trim() || !newValue.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await setEnv(newKey.trim(), newValue);
      await load();
      setAddOpen(false);
      setNewKey("");
      setNewValue("");
    } catch {
      setError(t("envs.error_save"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    setDeletingKey(key);
    setError(null);
    try {
      await deleteEnv(key);
      setKeys((prev) => prev.filter((k) => k !== key));
      setEnvs((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    } catch {
      setError(t("envs.error_delete"));
    } finally {
      setDeletingKey(null);
    }
  };

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
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-0.5">
          <p className="text-sm font-medium">{t("envs.title")}</p>
          <p className="text-xs text-muted-foreground max-w-[320px]">
            {t("envs.subtitle")}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0"
          onClick={() => setAddOpen(true)}
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          {t("envs.add")}
        </Button>
      </div>

      {/* Erro */}
      {error && (
        <p className="text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-md">
          {error}
        </p>
      )}

      {/* Empty state */}
      {keys.length === 0 && (
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
          <KeyRound className="w-10 h-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">{t("envs.empty")}</p>
        </div>
      )}

      {/* Lista */}
      <div className="space-y-2">
        {keys.map((key) => (
          <div
            key={key}
            className="flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2.5"
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-mono font-medium truncate">
                {key}
              </div>
              <div className="text-xs text-muted-foreground font-mono">
                {envs[key] ?? "••••••••"}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive shrink-0"
              onClick={() => handleDelete(key)}
              disabled={deletingKey === key}
            >
              {deletingKey === key ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Trash2 className="w-3.5 h-3.5" />
              )}
            </Button>
          </div>
        ))}
      </div>

      {/* Dialog — adicionar variável */}
      <Dialog
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open);
          if (!open) {
            setNewKey("");
            setNewValue("");
            setError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("envs.add_title")}</DialogTitle>
            <DialogDescription>{t("envs.add_desc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-1">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                {t("envs.key_label")}
              </label>
              <Input
                placeholder={t("envs.key_placeholder")}
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="text-sm font-mono"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                {t("envs.value_label")}
              </label>
              <Input
                type="password"
                placeholder={t("envs.value_placeholder")}
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="text-sm font-mono"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAddOpen(false)}
              disabled={saving}
            >
              {t("envs.cancel")}
            </Button>
            <Button
              onClick={handleAdd}
              disabled={saving || !newKey.trim() || !newValue.trim()}
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("envs.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
