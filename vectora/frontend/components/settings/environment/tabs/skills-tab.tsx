"use client";

/**
 * SkillsTab — gerenciador de skills do usuário (Bloco S8).
 *
 * Lista skills instaladas, permite instalar nova (via URL git ou path local) e
 * remover/verificar existentes. Cada skill é uma pasta com SKILL.md no root
 * carregada pelo Deep Agent sob demanda (progressive disclosure).
 */

import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { m } from "@/lib/paraglide/messages";
interface Skill {
  id: string;
  name: string;
  description: string;
  source: string;
  path: string;
  installed_at: string;
  installed_by: string;
}

type VerifyState = { state: "idle" | "loading" | "ok" | "error"; msg: string };

export function SkillsTab() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("");
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verify, setVerify] = useState<Record<string, VerifyState>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/skills");
      const data = await res.json();
      setSkills(Array.isArray(data.skills) ? data.skills : []);
    } catch {
      setError(m.skills_error_load());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleInstall() {
    if (!source.trim()) return;
    setInstalling(true);
    setError(null);
    try {
      const res = await fetch("/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: source.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || m.skills_error_install());
        return;
      }
      setSource("");
      await refresh();
    } catch {
      setError(m.skills_error_install());
    } finally {
      setInstalling(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm(m.skills_confirm_remove())) return;
    await fetch(`/skills/${encodeURIComponent(id)}`, { method: "DELETE" });
    await refresh();
  }

  async function handleVerify(id: string) {
    setVerify((v) => ({ ...v, [id]: { state: "loading", msg: "" } }));
    try {
      const res = await fetch(`/skills/${encodeURIComponent(id)}/verify`, {
        method: "POST",
      });
      const data = await res.json();
      setVerify((v) => ({
        ...v,
        [id]: {
          state: data.ok ? "ok" : "error",
          msg: data.ok ? m.skills_verify_ok() : (data.error ?? ""),
        },
      }));
    } catch {
      setVerify((v) => ({
        ...v,
        [id]: { state: "error", msg: m.skills_error_verify() },
      }));
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          {m.skills_title()}
        </h3>
        <p className="text-xs text-muted-foreground mt-1">
          {m.skills_description()}
        </p>
      </div>

      <div className="space-y-2 rounded-md border border-border/60 p-3">
        <label className="text-xs text-muted-foreground">
          {m.skills_install_label()}
        </label>
        <div className="flex items-center gap-1.5">
          <Input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder={m.skills_install_placeholder()}
            className="h-8 text-xs font-mono"
            autoComplete="off"
            spellCheck={false}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !installing) void handleInstall();
            }}
          />
          <Button
            size="sm"
            onClick={handleInstall}
            disabled={installing || !source.trim()}
            className="h-8"
          >
            {installing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Plus className="w-3.5 h-3.5" />
            )}
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {m.skills_loading()}
        </div>
      ) : skills.length === 0 ? (
        <p className="text-xs text-muted-foreground italic">
          {m.skills_empty()}
        </p>
      ) : (
        <div className="divide-y divide-border/60 rounded-md border border-border/60">
          {skills.map((s) => {
            const v = verify[s.id];
            return (
              <div key={s.id} className="p-3 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-foreground truncate">
                      {s.name}
                    </div>
                    <div className="text-[11px] text-muted-foreground truncate">
                      {s.description}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono truncate mt-0.5">
                      {s.source}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleVerify(s.id)}
                      disabled={v?.state === "loading"}
                      className="h-7 px-2 text-xs"
                    >
                      {v?.state === "loading" ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : v?.state === "ok" ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      ) : v?.state === "error" ? (
                        <XCircle className="w-3 h-3 text-destructive" />
                      ) : (
                        m.skills_verify()
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRemove(s.id)}
                      className="h-7 px-2"
                    >
                      <Trash2 className="w-3 h-3 text-destructive" />
                    </Button>
                  </div>
                </div>
                {v?.msg && (
                  <p
                    className={`text-[11px] ${
                      v.state === "ok" ? "text-emerald-500" : "text-destructive"
                    }`}
                  >
                    {v.msg}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
