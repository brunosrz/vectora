"use client";

/**
 * SkillsSection — gerencia skills instaladas (backend/workspace/skills.py,
 * GET/POST /skills, DELETE /skills/:id, POST /skills/:id/verify).
 * Reaproveita o componente SkillsTab, usando seu callback onSkillsChange
 * pra manter o badge "(N)" do accordion em dia sem duplicar o fetch.
 *
 * Abaixo dela, "Catálogo" lista skills curadas do registry remoto
 * (GET /skills/catalog, distinto de GET /skills que lista as instaladas) —
 * instalar uma reaproveita POST /skills {source} (mesmo endpoint do form
 * manual do SkillsTab).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Download,
  Loader2,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { SkillsTab } from "@/components/settings/environment/tabs/skills-tab";
import { m } from "@/lib/paraglide/messages";

interface CatalogSkill {
  id: string;
  name: string;
  description: string;
  source: string;
}

async function fetchCatalog(): Promise<CatalogSkill[]> {
  const res = await fetch("/skills/catalog");
  if (!res.ok) return [];
  const data = (await res.json()) as { entries?: CatalogSkill[] };
  return data.entries ?? [];
}

function CatalogCard({ skill }: { skill: CatalogSkill }) {
  const [busy, setBusy] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInstall = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: skill.source }),
      });
      if (!res.ok) {
        setError(m.library_skills_catalog_error_install());
        return;
      }
      setInstalled(true);
    } catch {
      setError(m.library_skills_catalog_error_install());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
          <Sparkles className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium truncate block">
            {skill.name}
          </span>
          <p className="text-xs text-muted-foreground truncate">
            {skill.description}
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
          ) : (
            <>
              <Download className="w-3 h-3 mr-1.5" />
              {m.library_skills_catalog_install()}
            </>
          )}
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function SkillsCatalog() {
  const [open, setOpen] = useState(true);
  const [entries, setEntries] = useState<CatalogSkill[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await fetchCatalog());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  const content = useMemo(() => {
    if (loading) {
      return (
        <div className="flex justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
      );
    }
    if (entries.length === 0) {
      return (
        <p className="text-xs text-muted-foreground text-center py-2">
          {m.library_skills_catalog_empty()}
        </p>
      );
    }
    return (
      <div className="space-y-2 py-1">
        {entries.map((skill) => (
          <CatalogCard key={skill.id} skill={skill} />
        ))}
      </div>
    );
  }, [entries, loading]);

  return (
    <div className="pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {open ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
        {m.library_skills_catalog_toggle()}
      </button>
      {open && content}
    </div>
  );
}

export function SkillsSection({
  onCountChange,
}: {
  query: string;
  onCountChange: (count: number) => void;
}) {
  return (
    <div className="space-y-1">
      <SkillsTab onSkillsChange={onCountChange} />
      <SkillsCatalog />
    </div>
  );
}
