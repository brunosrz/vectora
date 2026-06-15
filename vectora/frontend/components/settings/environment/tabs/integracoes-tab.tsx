"use client";

/**
 * IntegracoesTab — cards de integrações externas (Bloco O).
 *
 * O1 — API key: usuário insere chave manualmente; salva via /auth/envs.
 * O2 — OAuth: botão "Conectar" redireciona para o fluxo GitHub OAuth.
 *
 * Cada card mostra:
 * - Nome + descrição da integração
 * - Badge de status (Conectado / Não configurado)
 * - Formulário inline para API keys (masked, revela ao clicar Editar)
 * - Botão "Verificar" para testar a chave imediatamente
 * - Para GitHub: botão "Conectar via OAuth" ou "Desconectar"
 */

import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  GitBranch,
  KeyRound,
  Loader2,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VECTORA_API_URL } from "@/lib/constants/api";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface Integration {
  id: string;
  name: string;
  env_var: string;
  kind: "apikey" | "oauth" | "hybrid";
  description: string;
  docs_url: string;
  icon: string;
  oauth_scopes?: string[];
  connected: boolean;
}

type VerifyState = "idle" | "loading" | "ok" | "error";

function startGitBranchOAuth(): void {
  // Redireciona para o backend que inicia o fluxo OAuth.
  window.location.href = `${VECTORA_API_URL}/auth/github`;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch("/integrations/");
  if (!res.ok) return [];
  const data = await res.json();
  return data.integrations ?? [];
}

async function saveApiKey(envVar: string, value: string): Promise<void> {
  const res = await fetch("/auth/envs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: envVar, value }),
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function removeApiKey(envVar: string): Promise<void> {
  const res = await fetch(`/auth/envs/${encodeURIComponent(envVar)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function verifyIntegration(
  id: string,
): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`/integrations/${id}/verify`, {
    method: "POST",
  });
  if (!res.ok) return { ok: false, message: `Erro ${res.status}` };
  return res.json();
}

async function disconnectGitBranch(): Promise<void> {
  await fetch("/integrations/github", { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Subcomponente: card de integração
// ---------------------------------------------------------------------------

function IntegrationCard({
  integ,
  onUpdated,
}: {
  integ: Integration;
  onUpdated: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [keyValue, setKeyValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [verifyState, setVerifyState] = useState<VerifyState>("idle");
  const [verifyMsg, setVerifyMsg] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isGitBranch = integ.id === "github";
  // hybrid (ex.: GitHub) aceita tanto token manual quanto OAuth — por isso
  // mostra o campo de chave E o botão OAuth ao mesmo tempo.
  const allowToken = integ.kind === "apikey" || integ.kind === "hybrid";

  const handleSave = async () => {
    if (!keyValue.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await saveApiKey(integ.env_var, keyValue.trim());
      setKeyValue("");
      setExpanded(false);
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    setError(null);
    try {
      await removeApiKey(integ.env_var);
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao remover");
    } finally {
      setRemoving(false);
    }
  };

  const handleVerify = async () => {
    setVerifyState("loading");
    setVerifyMsg("");
    try {
      const result = await verifyIntegration(integ.id);
      setVerifyState(result.ok ? "ok" : "error");
      setVerifyMsg(result.message);
    } catch {
      setVerifyState("error");
      setVerifyMsg("Falha na verificação");
    }
  };

  const handleGitBranchDisconnect = async () => {
    setRemoving(true);
    try {
      await disconnectGitBranch();
      onUpdated();
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="rounded-lg border bg-card">
      {/* Cabeçalho do card */}
      <div className="flex items-center gap-3 p-3">
        {/* Ícone */}
        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
          {isGitBranch ? (
            <GitBranch className="w-4 h-4" />
          ) : (
            <KeyRound className="w-4 h-4 text-muted-foreground" />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{integ.name}</span>
            <Badge
              variant={integ.connected ? "default" : "secondary"}
              className="text-[10px] h-4 px-1.5"
            >
              {integ.connected ? "Conectado" : "Não configurado"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {integ.description}
          </p>
        </div>

        {/* Ações rápidas */}
        <div className="flex items-center gap-1 shrink-0">
          {integ.connected && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={handleVerify}
              disabled={verifyState === "loading"}
            >
              {verifyState === "loading" ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : verifyState === "ok" ? (
                <CheckCircle2 className="w-3 h-3 text-green-500" />
              ) : verifyState === "error" ? (
                <XCircle className="w-3 h-3 text-destructive" />
              ) : (
                "Verificar"
              )}
            </Button>
          )}

          {allowToken && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Mensagem de verificação */}
      {verifyMsg && (
        <div
          className={`mx-3 mb-2 text-xs px-2 py-1 rounded ${verifyState === "ok" ? "bg-green-500/10 text-green-600 dark:text-green-400" : "bg-destructive/10 text-destructive"}`}
        >
          {verifyMsg}
        </div>
      )}

      {/* Expansão para API key (O1) — apikey e hybrid (token manual) */}
      {allowToken && expanded && (
        <div className="px-3 pb-3 space-y-2 border-t pt-3">
          <div className="flex gap-2">
            <Input
              type="password"
              autoComplete="new-password"
              placeholder={`Cole sua ${integ.env_var} aqui`}
              value={keyValue}
              onChange={(e) => setKeyValue(e.target.value)}
              className="h-8 text-xs font-mono"
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleSave();
              }}
            />
            <Button
              size="sm"
              className="h-8 shrink-0"
              onClick={handleSave}
              disabled={saving || !keyValue.trim()}
            >
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : "Salvar"}
            </Button>
          </div>

          <div className="flex items-center justify-between">
            {integ.connected && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
                onClick={handleRemove}
                disabled={removing}
              >
                {removing && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
                Remover chave
              </Button>
            )}
            <a
              href={integ.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground ml-auto"
            >
              Obter chave
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}

      {/* GitHub OAuth (O2) */}
      {isGitBranch && (
        <div className="px-3 pb-3 border-t pt-3 space-y-2">
          {integ.connected ? (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Conexão ativa (OAuth ou token)
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs text-destructive hover:text-destructive"
                onClick={handleGitBranchDisconnect}
                disabled={removing}
              >
                {removing && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
                Desconectar
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Acesso a repos, PRs e issues
              </span>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={startGitBranchOAuth}
              >
                <GitBranch className="w-3 h-3 mr-1.5" />
                Conectar via OAuth
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function IntegracoesTab() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchIntegrations();
      setIntegrations(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  // Detecta oauth_success/oauth_error na URL após callback OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success") || params.get("oauth_error")) {
      // Remove os params da URL sem reload
      const url = new URL(window.location.href);
      url.searchParams.delete("oauth_success");
      url.searchParams.delete("oauth_error");
      window.history.replaceState({}, "", url.toString());
      void load();
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Agrupa: OAuth/híbridos primeiro, depois API keys por ordem de relevância
  const sorted = [
    ...integrations.filter((i) => i.kind === "oauth" || i.kind === "hybrid"),
    ...integrations.filter((i) => i.kind === "apikey"),
  ];

  const connected = sorted.filter((i) => i.connected).length;

  return (
    <div className="space-y-3">
      {/* Sumário */}
      <div className="space-y-0.5">
        <p className="text-sm font-medium">
          {connected > 0
            ? `${connected} integração${connected > 1 ? "s" : ""} ativa${connected > 1 ? "s" : ""}`
            : "Nenhuma integração configurada"}
        </p>
        <p className="text-xs text-muted-foreground">
          Chaves são armazenadas de forma privada e nunca compartilhadas com
          outros usuários.
        </p>
      </div>

      {/* Cards */}
      <div className="space-y-2">
        {sorted.map((integ) => (
          <IntegrationCard key={integ.id} integ={integ} onUpdated={load} />
        ))}
      </div>
    </div>
  );
}
