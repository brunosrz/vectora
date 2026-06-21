"use client";

import { Loader2, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToastStore } from "@/lib/stores/toast-store";
import { m } from "@/lib/paraglide/messages";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface Routine {
  id: string;
  name: string;
  instruction: string;
  cron_expr: string;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchRoutines(): Promise<Routine[]> {
  const res = await fetch("/routines");
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function createRoutine(
  name: string,
  instruction: string,
  cron_expr: string,
): Promise<Routine> {
  const res = await fetch("/routines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, instruction, cron_expr }),
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function toggleRoutine(id: string, enabled: boolean): Promise<void> {
  await fetch(`/routines/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

async function deleteRoutine(id: string): Promise<void> {
  await fetch(`/routines/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function RotinasTab() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [instruction, setInstruction] = useState("");
  const [cronExpr, setCronExpr] = useState("0 9 * * *");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRoutines(await fetchRoutines());
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    if (!name.trim() || !instruction.trim() || !cronExpr.trim()) return;
    setSaving(true);
    try {
      const routine = await createRoutine(
        name.trim(),
        instruction.trim(),
        cronExpr.trim(),
      );
      setRoutines((prev) => [...prev, routine]);
      setShowForm(false);
      setName("");
      setInstruction("");
      setCronExpr("0 9 * * *");
    } catch {
      useToastStore.getState().error(m.routines_create_error());
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (r: Routine) => {
    await toggleRoutine(r.id, !r.enabled);
    setRoutines((prev) =>
      prev.map((x) => (x.id === r.id ? { ...x, enabled: !r.enabled } : x)),
    );
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteRoutine(id);
      setRoutines((prev) => prev.filter((r) => r.id !== id));
    } catch {
      useToastStore.getState().error(m.routines_delete_error());
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs gap-1"
          onClick={() => setShowForm(true)}
          data-testid="routines-new-btn"
        >
          <Plus className="w-3 h-3" />
          {m.routines_new()}
        </Button>
      </div>

      {routines.length === 0 ? (
        <p className="text-xs text-muted-foreground text-center py-6">
          {m.routines_empty()}
        </p>
      ) : (
        <ul className="space-y-2">
          {routines.map((r) => (
            <li
              key={r.id}
              className="border border-border/60 rounded-md p-3 text-xs"
              data-testid="routine-item"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{r.name}</p>
                  <p className="text-muted-foreground font-mono mt-0.5">
                    {r.cron_expr}
                  </p>
                  <p className="text-muted-foreground mt-1 truncate">
                    {r.next_run_at
                      ? `${m.routines_next_run()}: ${r.next_run_at.slice(0, 16)}`
                      : m.routines_never()}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => void handleToggle(r)}
                    className={`w-7 h-4 rounded-full transition-colors ${r.enabled ? "bg-primary" : "bg-muted"}`}
                    aria-checked={r.enabled}
                    role="switch"
                    data-testid="routine-toggle"
                  >
                    <span
                      className={`block w-3 h-3 rounded-full bg-white mx-0.5 transition-transform ${r.enabled ? "translate-x-3" : ""}`}
                    />
                  </button>
                  <button
                    onClick={() => void handleDelete(r.id)}
                    className="p-0.5 text-muted-foreground hover:text-destructive"
                    data-testid="routine-delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-sm" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>{m.routines_new()}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs mb-1 block">
                {m.routines_name_label()}
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-7 text-xs"
                data-testid="routine-name-input"
              />
            </div>
            <div>
              <label className="text-xs mb-1 block">
                {m.routines_instruction_label()}
              </label>
              <Textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                className="text-xs min-h-[60px]"
                data-testid="routine-instruction-input"
              />
            </div>
            <div>
              <label className="text-xs mb-1 block">
                {m.routines_cron_label()}
              </label>
              <Input
                value={cronExpr}
                onChange={(e) => setCronExpr(e.target.value)}
                className="h-7 text-xs font-mono"
                data-testid="routine-cron-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm(false)}
              className="h-7 text-xs"
            >
              {m.routines_cancel()}
            </Button>
            <Button
              size="sm"
              disabled={saving}
              onClick={() => void handleCreate()}
              className="h-7 text-xs"
              data-testid="routine-save-btn"
            >
              {saving ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                m.routines_save()
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
