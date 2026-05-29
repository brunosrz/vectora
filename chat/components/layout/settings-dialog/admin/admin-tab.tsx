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
  Cpu,
  Loader2,
  Settings2,
  Shield,
  Trash2,
  Users,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const api = {
  users: {
    list: () => fetch("/api/admin/users").then((r) => r.json()),
    updateRole: (id: string, role: string) =>
      fetch(`/api/admin/users/${id}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      }),
    delete: (id: string) =>
      fetch(`/api/admin/users/${id}`, { method: "DELETE" }),
  },
  tools: {
    list: () => fetch("/api/admin/tools").then((r) => r.json()),
    toggle: (name: string, enabled: boolean) =>
      fetch(`/api/admin/tools/${name}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
  },
  system: () => fetch("/api/admin/system").then((r) => r.json()),
  config: {
    get: () => fetch("/api/admin/config").then((r) => r.json()),
    patch: (body: Partial<ServerConfig>) =>
      fetch("/api/admin/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  },
};

// ---------------------------------------------------------------------------
// Sub-aba: Usuários
// ---------------------------------------------------------------------------

function UsersPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);

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
      <p className="text-xs text-muted-foreground mb-3">
        {users.length} usuário{users.length !== 1 ? "s" : ""} cadastrado
        {users.length !== 1 ? "s" : ""}
      </p>
      {users.map((u) => (
        <div
          key={u.id}
          className="flex items-center gap-3 p-2.5 rounded-lg border bg-card"
        >
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
            className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
            onClick={() => void handleDelete(u.id)}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
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
      });
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
// Componente principal
// ---------------------------------------------------------------------------

type AdminSubTab = "users" | "tools" | "system" | "config";

const SUB_TABS: { id: AdminSubTab; label: string; icon: React.ReactNode }[] = [
  { id: "users", label: "Usuários", icon: <Users className="w-3.5 h-3.5" /> },
  {
    id: "tools",
    label: "Ferramentas",
    icon: <Wrench className="w-3.5 h-3.5" />,
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
        {active === "system" && <SystemPanel />}
        {active === "config" && <ConfigPanel />}
      </div>
    </div>
  );
}
