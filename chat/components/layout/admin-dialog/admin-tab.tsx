"use client";

/**
 * AdminTab — painel de administração (root/admin only).
 *
 * Sub-abas:
 * - Usuários: lista, muda role, deleta
 * - Ferramentas: habilita/desabilita tools globalmente
 * - Sistema: versão, serviços, métricas
 * - Configuração: allow_public_signup, default_model, max_recursion
 */

import {
  Check,
  Copy,
  Cpu,
  FolderLock,
  Loader2,
  Pencil,
  Settings2,
  Shield,
  Trash2,
  UserPlus,
  Users,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  useAdminDialogStore,
  type AdminSubTab,
} from "@/lib/stores/admin-dialog-store";

import { useT } from "@/lib/i18n";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  getAllowedModels,
  getModelDisplayName,
  type ModelOption,
} from "@/lib/config/deployment-config";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface AdminUser {
  id: string;
  email: string;
  role: string;
  created_at: string;
  last_login_at: string | null;
}

interface PendingInvite {
  token_hash: string;
  email: string | null;
  role: string;
  created_by: string | null;
  expires_at: string;
  created_at: string;
}

interface AdminTool {
  name: string;
  description: string;
  category: string;
  destructive: boolean;
  enabled: boolean;
}

interface SystemInfo {
  version: string;
  python_version: string;
  platform: string;
  services: Record<string, string>;
  recent_spans_count: number;
}

interface ServerConfig {
  default_model: string;
  max_recursion: number;
  allow_public_signup: boolean;
  db_dsn: string;
  vectora_token_masked: string;
  vectora_token_configured: boolean;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const api = {
  users: {
    list: () => fetch("/admin/users").then((r) => r.json()),
    updateRole: (id: string, role: string) =>
      fetch(`/admin/users/${id}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      }),
    delete: (id: string) => fetch(`/admin/users/${id}`, { method: "DELETE" }),
  },
  tools: {
    list: () => fetch("/admin/tools").then((r) => r.json()),
    toggle: (name: string, enabled: boolean) =>
      fetch(`/admin/tools/${name}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
  },
  invites: {
    list: () => fetch("/admin/invites").then((r) => r.json()),
    create: (body: { role: string; email?: string; ttl_hours: number }) =>
      fetch("/admin/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then((r) => r.json()),
    revoke: (tokenHash: string) =>
      fetch(`/admin/invites/${tokenHash}`, { method: "DELETE" }),
  },
  system: () => fetch("/admin/system").then((r) => r.json()),
  config: {
    get: () => fetch("/admin/config").then((r) => r.json()),
    patch: (body: Partial<ServerConfig> & { vectora_token?: string }) =>
      fetch("/admin/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  },
};

// ---------------------------------------------------------------------------
// Sub-aba: Usuários
// ---------------------------------------------------------------------------

function InvitesSection() {
  const t = useT();
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState("member");
  const [email, setEmail] = useState("");
  const [ttl, setTtl] = useState(24);
  const [creating, setCreating] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await api.invites.list();
      setInvites(data.invites ?? []);
    } catch {
      // silencioso
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    setLink(null);
    try {
      const data = await api.invites.create({
        role,
        email: email.trim() || undefined,
        ttl_hours: ttl,
      });
      if (data?.url) {
        setLink(data.url);
        await load();
      } else {
        setError(t("invite.error_create"));
      }
    } catch {
      setError(t("invite.error_create"));
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = async (tokenHash: string) => {
    await api.invites.revoke(tokenHash);
    setInvites((prev) => prev.filter((i) => i.token_hash !== tokenHash));
  };

  return (
    <div className="rounded-lg border bg-card/50 p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium flex items-center gap-1.5">
          <UserPlus className="w-3.5 h-3.5 text-muted-foreground" />
          {t("invite.title")}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={() => {
            setOpen((o) => !o);
            setLink(null);
            setError(null);
          }}
        >
          {t("invite.title")}
        </Button>
      </div>

      {open && (
        <div className="space-y-2 border-t pt-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground">
                {t("invite.role_label")}
              </label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger className="h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">admin</SelectItem>
                  <SelectItem value="member">member</SelectItem>
                  <SelectItem value="viewer">viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1 col-span-1">
              <label className="text-[10px] text-muted-foreground">
                {t("invite.ttl_label")}
              </label>
              <Input
                type="number"
                value={ttl}
                onChange={(e) => setTtl(parseInt(e.target.value) || 24)}
                className="h-7 text-xs"
                min={1}
                max={720}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground">
                {t("invite.email_label")}
              </label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-7 text-xs"
                placeholder="—"
              />
            </div>
          </div>

          <Button
            size="sm"
            className="h-7 text-xs"
            onClick={handleCreate}
            disabled={creating}
          >
            {creating ? (
              <Loader2 className="w-3 h-3 animate-spin mr-1.5" />
            ) : null}
            {t("invite.create")}
          </Button>

          {error && <p className="text-xs text-destructive">{error}</p>}

          {link && (
            <div className="flex items-center gap-1.5 rounded-md border bg-background p-1.5">
              <span className="text-[10px] font-mono truncate flex-1">
                {link}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 shrink-0"
                onClick={handleCopy}
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Convites pendentes */}
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
          {t("invite.pending")}
        </p>
        {invites.length === 0 ? (
          <p className="text-xs text-muted-foreground">{t("invite.none")}</p>
        ) : (
          invites.map((inv) => (
            <div
              key={inv.token_hash}
              className="flex items-center gap-2 px-2 py-1.5 rounded-md border text-xs"
            >
              <Badge variant="secondary" className="text-[9px] h-4">
                {inv.role}
              </Badge>
              <span className="flex-1 truncate text-muted-foreground">
                {inv.email || "—"} · {t("invite.expires")}{" "}
                {new Date(inv.expires_at).toLocaleString("pt-BR")}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                onClick={() => void handleRevoke(inv.token_hash)}
                title={t("invite.revoke")}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function UserToolsRow({ userId }: { userId: string }) {
  const t = useT();
  const [available, setAvailable] = useState<string[]>([]);
  const [disabled, setDisabled] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/admin/users/${userId}/tools`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || !d) return;
        setAvailable(d.available ?? []);
        setDisabled(new Set(d.disabled ?? []));
      })
      .finally(() => setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [userId]);

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
    try {
      await fetch(`/admin/users/${userId}/tools`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ disabled: [...disabled] }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="px-3 py-2">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card/50 -mt-1 p-3 space-y-2">
      <div className="max-h-48 overflow-y-auto divide-y divide-border/60 rounded-md border">
        {available.map((name) => (
          <div
            key={name}
            className="flex items-center justify-between px-2.5 py-1.5"
          >
            <span className="text-[11px] font-mono">{name}</span>
            <Switch
              checked={!disabled.has(name)}
              onCheckedChange={() => toggle(name)}
            />
          </div>
        ))}
      </div>
      <div className="flex items-center justify-end gap-2">
        {saved && (
          <span className="text-[10px] text-green-500">
            {t("toolpolicy.saved")}
          </span>
        )}
        <Button
          size="sm"
          className="h-7 text-xs"
          onClick={handleSave}
          disabled={saving}
        >
          {saving && <Loader2 className="w-3 h-3 animate-spin mr-1.5" />}
          {t("toolpolicy.save")}
        </Button>
      </div>
    </div>
  );
}

function UsersPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [openTools, setOpenTools] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.users.list();
      setUsers(data.users ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleRoleChange = async (userId: string, role: string) => {
    setUpdating(userId);
    try {
      await api.users.updateRole(userId, role);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role } : u)),
      );
    } finally {
      setUpdating(null);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Deletar este usuário? Esta ação é irreversível.")) return;
    await api.users.delete(userId);
    setUsers((prev) => prev.filter((u) => u.id !== userId));
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <InvitesSection />
      <p className="text-xs text-muted-foreground mb-3">
        {users.length} usuário{users.length !== 1 ? "s" : ""} cadastrado
        {users.length !== 1 ? "s" : ""}
      </p>
      {users.map((u) => (
        <div key={u.id} className="space-y-1">
          <div className="flex items-center gap-3 p-2.5 rounded-lg border bg-card">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{u.email}</p>
              <p className="text-[10px] text-muted-foreground">
                desde {new Date(u.created_at).toLocaleDateString("pt-BR")}
                {u.last_login_at &&
                  ` · último acesso ${new Date(u.last_login_at).toLocaleDateString("pt-BR")}`}
              </p>
            </div>

            <Select
              value={u.role}
              onValueChange={(role) => void handleRoleChange(u.id, role)}
              disabled={updating === u.id}
            >
              <SelectTrigger className="h-7 w-24 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="root">root</SelectItem>
                <SelectItem value="admin">admin</SelectItem>
                <SelectItem value="member">member</SelectItem>
                <SelectItem value="viewer">viewer</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
              onClick={() => setOpenTools(openTools === u.id ? null : u.id)}
              title="Tools"
            >
              <Wrench className="w-3.5 h-3.5" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
              onClick={() => void handleDelete(u.id)}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
          {openTools === u.id && <UserToolsRow userId={u.id} />}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-aba: Ferramentas
// ---------------------------------------------------------------------------

function ToolsPanel() {
  const [tools, setTools] = useState<AdminTool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.tools
      .list()
      .then((d) => setTools(d.tools ?? []))
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    await api.tools.toggle(name, enabled);
    setTools((prev) =>
      prev.map((t) => (t.name === name ? { ...t, enabled } : t)),
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {tools.map((t) => (
        <div
          key={t.name}
          className="flex items-center gap-3 p-2.5 rounded-lg border bg-card"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono font-medium">{t.name}</span>
              {t.destructive && (
                <Badge variant="destructive" className="text-[9px] h-3.5 px-1">
                  destrutiva
                </Badge>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground truncate">
              {t.description}
            </p>
          </div>
          <Switch
            checked={t.enabled}
            onCheckedChange={(v) => void handleToggle(t.name, v)}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-aba: Sistema
// ---------------------------------------------------------------------------

function SystemPanel() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .system()
      .then(setInfo)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!info) return null;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {[
          ["Versão", info.version],
          ["Plataforma", info.platform],
          ["Python", info.python_version.split(" ")[0]],
          ["Spans recentes", String(info.recent_spans_count)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border bg-card p-2.5">
            <p className="text-[10px] text-muted-foreground">{label}</p>
            <p className="text-xs font-medium truncate">{value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-1">
        <p className="text-xs font-medium">Serviços</p>
        {Object.entries(info.services).map(([svc, status]) => (
          <div
            key={svc}
            className="flex items-center justify-between px-2.5 py-1.5 rounded-md border"
          >
            <span className="text-xs">{svc}</span>
            <Badge
              variant={status === "ok" ? "default" : "destructive"}
              className="text-[10px] h-4"
            >
              {status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-aba: Configuração
// ---------------------------------------------------------------------------

function ConfigPanel() {
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  // Input controlado para VECTORA_TOKEN: o backend nunca devolve o token
  // em claro, então mantemos um buffer local. Vazio = não-alterar.
  const [tokenInput, setTokenInput] = useState("");
  const [showToken, setShowToken] = useState(false);

  useEffect(() => {
    api.config
      .get()
      .then(setConfig)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await api.config.patch({
        allow_public_signup: config.allow_public_signup,
        default_model: config.default_model,
        max_recursion: config.max_recursion,
        ...(tokenInput.trim() ? { vectora_token: tokenInput.trim() } : {}),
      });
      // Re-fetch para refletir o masked atualizado.
      if (tokenInput.trim()) {
        const fresh = await api.config.get();
        setConfig(fresh);
        setTokenInput("");
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5 pb-3 border-b">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">VECTORA_TOKEN</p>
          {config.vectora_token_configured ? (
            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
              configurado
            </span>
          ) : (
            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-orange-500/15 text-orange-700 dark:text-orange-300 border border-orange-500/30">
              ausente
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Token de licença do produto. Obtenha em{" "}
          <a
            href="https://vectora.company/dashboard"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            vectora.company/dashboard
          </a>
          .
        </p>
        {config.vectora_token_configured && (
          <p className="text-xs text-muted-foreground font-mono">
            atual: {config.vectora_token_masked}
          </p>
        )}
        <div className="flex gap-1.5">
          <Input
            type={showToken ? "text" : "password"}
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder={
              config.vectora_token_configured
                ? "Digite para substituir…"
                : "vct_…"
            }
            className="h-8 text-xs font-mono flex-1"
            autoComplete="off"
          />
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 px-2"
            onClick={() => setShowToken((v) => !v)}
            aria-label={showToken ? "Ocultar token" : "Mostrar token"}
          >
            {showToken ? "Ocultar" : "Mostrar"}
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">Signup público</p>
          <p className="text-xs text-muted-foreground">
            Permite novos usuários se cadastrarem sem convite
          </p>
        </div>
        <Switch
          checked={config.allow_public_signup}
          onCheckedChange={(v) =>
            setConfig((prev) => prev && { ...prev, allow_public_signup: v })
          }
        />
      </div>

      <div className="space-y-1.5">
        <p className="text-sm font-medium">Modelo padrão</p>
        <Select
          value={config.default_model}
          onValueChange={(v) =>
            setConfig((prev) => prev && { ...prev, default_model: v })
          }
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="ex: gemini-2.5-flash" />
          </SelectTrigger>
          <SelectContent>
            {getAllowedModels().map((modelId) => (
              <SelectItem key={modelId} value={modelId}>
                {getModelDisplayName(modelId as ModelOption)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <p className="text-sm font-medium">Limite de recursão</p>
        <Input
          type="number"
          value={config.max_recursion}
          onChange={(e) =>
            setConfig(
              (prev) =>
                prev && {
                  ...prev,
                  max_recursion: parseInt(e.target.value) || 50,
                },
            )
          }
          className="h-8 text-xs w-24"
          min={5}
          max={200}
        />
      </div>

      <Button size="sm" onClick={handleSave} disabled={saving}>
        {saving ? <Loader2 className="w-3 h-3 animate-spin mr-1.5" /> : null}
        {saved ? "Salvo!" : "Salvar alterações"}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// F.3.3 — Pastas Seguras (SafeRoot)
// ---------------------------------------------------------------------------

interface SafeRootRow {
  id: string;
  path: string;
  label: string;
  builtin: boolean;
  created_at: string;
  created_by: string;
}

function SafeRootsPanel() {
  const [roots, setRoots] = useState<SafeRootRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [newPath, setNewPath] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [removeConfirmId, setRemoveConfirmId] = useState<string | null>(null);

  const reload = async () => {
    setLoading(true);
    try {
      const res = await fetch("/admin/safe-roots");
      if (res.ok) {
        const data = await res.json();
        setRoots(data.roots ?? []);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, []);

  const handleAdd = async () => {
    if (!newPath.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await fetch("/admin/safe-roots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: newPath.trim(),
          label: newLabel.trim(),
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? `Falha (${res.status})`);
      } else {
        setNewPath("");
        setNewLabel("");
        await reload();
      }
    } finally {
      setCreating(false);
    }
  };

  const handleSaveLabel = async (id: string) => {
    if (!editLabel.trim()) {
      setEditingId(null);
      return;
    }
    await fetch(`/admin/safe-roots/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: editLabel.trim() }),
    });
    setEditingId(null);
    await reload();
  };

  const handleRemove = (id: string) => {
    setRemoveConfirmId(id);
  };

  const handleRemoveConfirmed = async () => {
    if (!removeConfirmId) return;
    const id = removeConfirmId;
    setRemoveConfirmId(null);
    await fetch(`/admin/safe-roots/${id}`, { method: "DELETE" });
    await reload();
  };

  return (
    <div className="space-y-4">
      <div className="text-xs text-muted-foreground">
        Usuários comuns só podem criar workspaces dentro destas pastas. A
        entrada builtin (Documents/vectora) não pode ser removida.
      </div>

      {/* Adicionar nova */}
      <div className="rounded-md border border-border/60 p-3 space-y-2">
        <div className="text-xs font-medium text-foreground">
          Adicionar pasta segura
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <Input
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="/caminho/absoluto/da/pasta"
            className="font-mono text-xs"
          />
          <Input
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Rótulo (opcional)"
            className="text-xs sm:w-48"
          />
          <Button
            size="sm"
            onClick={handleAdd}
            disabled={creating || !newPath.trim()}
          >
            {creating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              "Adicionar"
            )}
          </Button>
        </div>
        {error && <div className="text-xs text-destructive">{error}</div>}
      </div>

      {/* Lista */}
      {loading ? (
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Carregando…
        </div>
      ) : roots.length === 0 ? (
        <div className="text-xs text-muted-foreground">
          Nenhuma pasta configurada.
        </div>
      ) : (
        <div className="rounded-md border border-border/60 divide-y divide-border/60">
          {roots.map((r) => (
            <div
              key={r.id}
              className="flex items-center gap-2 px-3 py-2 text-xs"
            >
              <FolderLock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                {editingId === r.id ? (
                  <Input
                    value={editLabel}
                    onChange={(e) => setEditLabel(e.target.value)}
                    onBlur={() => handleSaveLabel(r.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleSaveLabel(r.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    autoFocus
                    className="h-6 text-xs"
                  />
                ) : (
                  <div className="font-medium text-foreground flex items-center gap-1.5">
                    {r.label}
                    {r.builtin && (
                      <Badge variant="secondary" className="text-[10px] py-0">
                        builtin
                      </Badge>
                    )}
                  </div>
                )}
                <div className="font-mono text-[10px] text-muted-foreground truncate">
                  {r.path}
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setEditingId(r.id);
                  setEditLabel(r.label);
                }}
                title="Renomear"
              >
                <Pencil className="w-3.5 h-3.5" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleRemove(r.id)}
                disabled={r.builtin}
                title={
                  r.builtin ? "Pasta builtin não pode ser removida" : "Remover"
                }
                className="text-destructive hover:text-destructive disabled:opacity-30"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Confirmação de remoção de safe-root (Radix Dialog — C.12) */}
      <ConfirmDialog
        open={removeConfirmId !== null}
        title="Remover pasta segura?"
        description="Workspaces existentes não são afetados."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleRemoveConfirmed}
        onCancel={() => setRemoveConfirmId(null)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

const SUB_TABS: { id: AdminSubTab; label: string; icon: React.ReactNode }[] = [
  { id: "users", label: "Usuários", icon: <Users className="w-3.5 h-3.5" /> },
  {
    id: "tools",
    label: "Ferramentas",
    icon: <Wrench className="w-3.5 h-3.5" />,
  },
  {
    id: "safe-roots",
    label: "Pastas Seguras",
    icon: <FolderLock className="w-3.5 h-3.5" />,
  },
  {
    id: "system",
    label: "Sistema",
    icon: <Cpu className="w-3.5 h-3.5" />,
  },
  {
    id: "config",
    label: "Config",
    icon: <Settings2 className="w-3.5 h-3.5" />,
  },
];

export function AdminTab() {
  const [active, setActive] = useState<AdminSubTab>("users");

  // Deep-link: outros lugares (license-banner, etc.) usam
  // `useAdminDialogStore.openAt("config")`. Quando o store recebe `subTab`,
  // sincronizamos com o `active` local e limpamos o slot para que
  // re-aberturas do dialog não voltem para a mesma sub-aba.
  const subTab = useAdminDialogStore((s) => s.subTab);
  const setSubTab = useAdminDialogStore((s) => s.setSubTab);
  useEffect(() => {
    if (subTab) {
      setActive(subTab);
      setSubTab(undefined);
    }
  }, [subTab, setSubTab]);

  return (
    <div className="space-y-4">
      {/* Header com badge de aviso */}
      <div className="flex items-center gap-2">
        <Shield className="w-4 h-4 text-amber-500" />
        <span className="text-xs text-muted-foreground">
          Painel de administração — apenas root e admin
        </span>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 border-b pb-0">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-t-md border-b-2 transition-colors ${active === tab.id ? "border-foreground text-foreground font-medium" : "border-transparent text-muted-foreground hover:text-foreground"}`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Conteúdo */}
      <div className="min-h-[200px]">
        {active === "users" && <UsersPanel />}
        {active === "tools" && <ToolsPanel />}
        {active === "safe-roots" && <SafeRootsPanel />}
        {active === "system" && <SystemPanel />}
        {active === "config" && <ConfigPanel />}
      </div>
    </div>
  );
}
