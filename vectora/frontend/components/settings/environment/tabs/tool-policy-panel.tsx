"use client";

/**
 * ToolPolicyPanel — controle do usuário sobre quais tools built-in o agente
 * pode usar em seu nome (Bloco S, S5 self-service).
 *
 * GET /tools/policy → {disabled, available}; PUT salva as desabilitadas.
 * Mudanças entram em vigor no próximo request (S4/S6 invalidam o cache).
 */

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { m } from "@/lib/paraglide/messages";
interface Policy {
  disabled: string[];
  available: string[];
}

export function ToolPolicyPanel() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [disabled, setDisabled] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/tools/policy")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled) return;
        if (d?.available) {
          setPolicy(d);
          setDisabled(new Set(d.disabled ?? []));
        } else {
          setError(m.toolpolicy_error_load());
        }
      })
      .catch(() => setError(m.toolpolicy_error_load()))
      .finally(() => setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = (name: string) => {
    setDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/tools/policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ disabled: [...disabled] }),
      });
      if (!res.ok) {
        setError(m.toolpolicy_error_save());
        return;
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError(m.toolpolicy_error_save());
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!policy) {
    return <p className="text-xs text-destructive">{error}</p>;
  }

  const dirty = (() => {
    const base = new Set(policy.disabled);
    if (base.size !== disabled.size) return true;
    for (const n of disabled) if (!base.has(n)) return true;
    return false;
  })();

  return (
    <div className="space-y-3">
      <div className="space-y-0.5">
        <p className="text-sm font-medium">{m.toolpolicy_title()}</p>
        <p className="text-xs text-muted-foreground">
          {m.toolpolicy_subtitle()}
        </p>
      </div>

      <div className="rounded-lg border bg-card/50 divide-y divide-border/60">
        {policy.available.map((name) => {
          const isEnabled = !disabled.has(name);
          return (
            <div
              key={name}
              className="flex items-center justify-between px-3 py-2"
            >
              <span className="text-xs font-mono">{name}</span>
              <Switch
                checked={isEnabled}
                onCheckedChange={() => toggle(name)}
              />
            </div>
          );
        })}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex items-center gap-2 justify-end">
        {saved && (
          <span className="text-xs text-green-500 inline-flex items-center gap-1">
            <Check className="w-3 h-3" />
            {m.toolpolicy_saved()}
          </span>
        )}
        <Button
          size="sm"
          className="h-7 text-xs"
          onClick={handleSave}
          disabled={saving || !dirty}
        >
          {saving && <Loader2 className="w-3 h-3 animate-spin mr-1.5" />}
          {m.toolpolicy_save()}
        </Button>
      </div>
    </div>
  );
}
