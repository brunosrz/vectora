"use client";

/**
 * IntegracoesTab — cards de integrações externas.
 *
 * O1 — API key: usuário insere chave manualmente.
 * O2–O5 — OAuth: GitHub, GitLab, Google, Slack.
 * Webhook URL: exibida para providers que têm webhook configurado.
 */

import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  GitBranch,
  KeyRound,
  Link2,
  Loader2,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { m } from "@/lib/paraglide/messages";
import { useFeatureFlags } from "@/lib/hooks/use-feature-flags";

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
  parent?: string;
  connected: boolean;
}

type VerifyState = "idle" | "loading" | "ok" | "error";

// Providers que têm suporte a webhook no backend
const WEBHOOK_PROVIDERS = new Set(["github", "gitlab", "slack", "linear"]);
// Providers com fluxo OAuth (além de hybrid = github)
const OAUTH_PROVIDERS = new Set(["github", "gitlab", "google", "slack"]);

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch("/integrations/");
  if (!res.ok) return [];
  const data = (await res.json()) as { integrations?: Integration[] };
  return data.integrations ?? [];
}

type RelayState = "never_connected" | "error" | "connected";

interface RelayStatus {
  connected: boolean;
  state: RelayState;
  token: string | null;
  subdomain: string | null;
  webhook_base: string | null;
  detail: string | null;
}

const RELAY_STATUS_FALLBACK: RelayStatus = {
  connected: false,
  state: "never_connected",
  token: null,
  subdomain: null,
  webhook_base: null,
  detail: null,
};

async function fetchRelayStatus(): Promise<RelayStatus> {
  try {
    const res = await fetch("/relay/status");
    if (!res.ok) return RELAY_STATUS_FALLBACK;
    return (await res.json()) as RelayStatus;
  } catch {
    return RELAY_STATUS_FALLBACK;
  }
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
  const res = await fetch(`/integrations/${id}/verify`, { method: "POST" });
  if (!res.ok) return { ok: false, message: `Erro ${res.status}` };
  return res.json() as Promise<{ ok: boolean; message: string }>;
}

async function disconnectOAuth(provider: string): Promise<void> {
  await fetch(`/auth/${provider}`, { method: "DELETE" });
}

function startOAuth(provider: string): void {
  window.location.href = `/auth/${provider}`;
}

// ---------------------------------------------------------------------------
// Subcomponente: card de integração
// ---------------------------------------------------------------------------

function IntegrationCard({
  integ,
  onUpdated,
  relayWebhookBase,
  enableFeaturesBeta,
}: {
  integ: Integration;
  onUpdated: () => void;
  relayWebhookBase: string | null;
  enableFeaturesBeta: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [keyValue, setKeyValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [verifyState, setVerifyState] = useState<VerifyState>("idle");
  const [verifyMsg, setVerifyMsg] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [webhookCopied, setWebhookCopied] = useState(false);

  const isOAuthProvider = OAUTH_PROVIDERS.has(integ.id);
  const isChildOAuth = !!integ.parent; // google-drive, gmail dependem de google
  const allowToken = integ.kind === "apikey" || integ.kind === "hybrid";
  const hasWebhook = WEBHOOK_PROVIDERS.has(integ.id);

  // URL de webhook — usa relay (*.vectora.chat) quando conectado,
  // ou a origem do site em produção (self-hosted com domínio próprio).
  const webhookUrl = relayWebhookBase
    ? `${relayWebhookBase}/webhook/${integ.id}`
    : typeof window !== "undefined"
      ? `${window.location.origin}/webhook/${integ.id}`
      : `/webhook/${integ.id}`;

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

  const handleOAuthDisconnect = async () => {
    setRemoving(true);
    try {
      const provider = integ.parent ?? integ.id;
      await disconnectOAuth(provider);
      onUpdated();
    } finally {
      setRemoving(false);
    }
  };

  const handleCopyWebhook = async () => {
    await navigator.clipboard.writeText(webhookUrl);
    setWebhookCopied(true);
    setTimeout(() => setWebhookCopied(false), 2000);
  };

  // Providers filho (google-drive, gmail) herdam conexão do pai — não mostram
  // card próprio com botão de OAuth; apenas mostram status herdado.
  if (isChildOAuth) {
    return (
      <div className="rounded-lg border bg-card/50">
        <div className="flex items-center gap-3 p-3">
          <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
            <Link2 className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{integ.name}</span>
              <Badge
                variant={integ.connected ? "default" : "secondary"}
                className="text-[10px] h-4 px-1.5"
              >
                {integ.connected
                  ? m.integrations_connected()
                  : m.integrations_disconnected()}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground truncate">
              {integ.description}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      {/* Cabeçalho */}
      <div className="flex items-center gap-3 p-3">
        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
          {isOAuthProvider ? (
            <GitBranch className="w-4 h-4" />
          ) : (
            <KeyRound className="w-4 h-4 text-muted-foreground" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{integ.name}</span>
            <Badge
              variant={integ.connected ? "default" : "secondary"}
              className="text-[10px] h-4 px-1.5"
            >
              {integ.connected
                ? m.integrations_connected()
                : m.integrations_disconnected()}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {integ.description}
          </p>
        </div>

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
                m.integrations_verify()
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
          className={`mx-3 mb-2 text-xs px-2 py-1 rounded ${
            verifyState === "ok"
              ? "bg-green-500/10 text-green-600 dark:text-green-400"
              : "bg-destructive/10 text-destructive"
          }`}
        >
          {verifyMsg}
        </div>
      )}

      {/* Expansão para API key */}
      {allowToken && expanded && (
        <div className="px-3 pb-3 space-y-2 border-t pt-3">
          <div className="flex gap-2">
            <Input
              type="password"
              autoComplete="new-password"
              placeholder={m.integrations_api_key_placeholder()}
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
              {saving ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                m.integrations_save_key()
              )}
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
                {m.integrations_remove_key()}
              </Button>
            )}
            <a
              href={integ.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground ml-auto"
            >
              {m.integrations_get_key()}
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}

      {/* OAuth section — apenas quando feature beta habilitada */}
      {isOAuthProvider && enableFeaturesBeta && (
        <div className="px-3 pb-3 border-t pt-3 space-y-2">
          {integ.connected ? (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Conexão ativa (OAuth)
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs text-destructive hover:text-destructive"
                onClick={handleOAuthDisconnect}
                disabled={removing}
              >
                {removing && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
                {m.integrations_disconnect()}
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {integ.description}
              </span>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={() => startOAuth(integ.id)}
              >
                <GitBranch className="w-3 h-3 mr-1.5" />
                {m.integrations_connect_oauth()}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Webhook URL — para providers com webhook configurado */}
      {hasWebhook && integ.connected && (
        <div className="px-3 pb-3 border-t pt-3 space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">
            {m.integrations_webhook_url()}
          </p>
          <div className="flex gap-1.5">
            <code className="flex-1 text-xs bg-muted px-2 py-1 rounded font-mono truncate">
              {webhookUrl}
            </code>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 shrink-0"
              onClick={handleCopyWebhook}
              title={m.integrations_webhook_copy()}
            >
              {webhookCopied ? (
                <CheckCircle2 className="w-3 h-3 text-green-500" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Categorias
// ---------------------------------------------------------------------------

const CATEGORIES: { label: string; ids: string[] }[] = [
  { label: "Git", ids: ["github", "gitlab"] },
  {
    label: "IA",
    ids: ["openai", "anthropic", "cohere", "tavily"],
  },
  {
    label: "Google",
    ids: ["google", "google-drive", "gmail"],
  },
  { label: "Comunicação", ids: ["slack"] },
  { label: "Produtividade", ids: ["linear", "jira", "notion"] },
  { label: "Email", ids: ["resend", "sendgrid", "mailgun"] },
];

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function IntegracoesTab() {
  const { enableFeaturesBeta } = useFeatureFlags();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [relay, setRelay] = useState<RelayStatus>(RELAY_STATUS_FALLBACK);

  const load = async () => {
    setLoading(true);
    try {
      const [data, relayStatus] = await Promise.all([
        fetchIntegrations(),
        fetchRelayStatus(),
      ]);
      setIntegrations(data);
      setRelay(relayStatus);
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
    if (params.get("oauth_success") ?? params.get("oauth_error")) {
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

  const byId = Object.fromEntries(integrations.map((i) => [i.id, i]));
  const connected = integrations.filter((i) => i.connected).length;

  return (
    <div className="space-y-4">
      {/* Sumário */}
      <div className="space-y-0.5">
        <p className="text-sm font-medium">
          {connected > 0
            ? `${connected} integração${connected > 1 ? "s" : ""} ativa${connected > 1 ? "s" : ""}`
            : m.integrations_none_active()}
        </p>
        <p className="text-xs text-muted-foreground">
          {m.integrations_keys_private()}
        </p>
      </div>

      {/* Banner relay — visível apenas quando OAuth/relay está habilitado.
          3 estados distintos (não só conectado/desconectado): nunca
          conectou (neutro, nada errado — normal antes da 1ª integração),
          erro real (relay fora do ar/mal configurado, com detalhe), e
          conectado. Antes, os dois primeiros mostravam a mesma mensagem
          "Relay disconnected", sem o usuário conseguir saber se precisava
          agir ou se era só o estado inicial esperado. */}
      {enableFeaturesBeta && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs space-y-0.5 ${
            relay.state === "connected"
              ? "border-green-500/30 bg-green-500/5"
              : relay.state === "error"
                ? "border-destructive/30 bg-destructive/5"
                : "border-border bg-muted/30"
          }`}
        >
          <div className="flex items-center justify-between">
            <p
              className={`font-medium ${
                relay.state === "connected"
                  ? "text-green-600 dark:text-green-400"
                  : relay.state === "error"
                    ? "text-destructive"
                    : "text-muted-foreground"
              }`}
            >
              {relay.state === "connected"
                ? m.relay_connected()
                : relay.state === "error"
                  ? m.relay_error()
                  : m.relay_never_connected()}
            </p>
            {relay.subdomain && (
              <span className="font-mono text-[10px] text-muted-foreground">
                {relay.subdomain}
              </span>
            )}
          </div>
          {relay.state === "connected" && relay.webhook_base && (
            <p className="text-muted-foreground">
              {m.relay_webhook_hint()}{" "}
              <span className="font-mono">
                {relay.webhook_base}/webhook/&#123;provider&#125;
              </span>
            </p>
          )}
          {relay.state === "error" && (
            <p className="text-destructive/80">
              {relay.detail ?? m.relay_error_retry()}
            </p>
          )}
          {relay.state === "never_connected" && (
            <p className="text-muted-foreground">{m.relay_no_token()}</p>
          )}
        </div>
      )}

      {/* Cards por categoria */}
      {CATEGORIES.map((cat) => {
        const items = cat.ids.flatMap((id) => (byId[id] ? [byId[id]] : []));
        if (items.length === 0) return null;
        return (
          <div key={cat.label} className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {cat.label}
            </p>
            {items.map((integ) => (
              <IntegrationCard
                key={integ.id}
                integ={integ}
                onUpdated={load}
                relayWebhookBase={relay.webhook_base}
                enableFeaturesBeta={enableFeaturesBeta}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
