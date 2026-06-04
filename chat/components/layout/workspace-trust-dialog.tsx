"use client";

/**
 * WorkspaceTrustDialog (Q6)
 *
 * Fluxo de "trust folder": directory browser para escolher uma pasta,
 * confirmação explícita de confiança (explica os guard rails de escopo) e
 * checkbox para inicializar git se a pasta ainda não for um repositório.
 *
 * Ao confiar, registra a pasta como workspace ativo via store.create().
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  Cloud,
  CornerDownLeft,
  Folder,
  GitBranch,
  HardDrive,
  Loader2,
  Monitor,
  Server,
  Upload,
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DRIVES_PSEUDO_PATH,
  useWorkspacesStore,
  type BrowseResult,
  type CodespaceSummary,
} from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";

type Tab = "local" | "ssh" | "codespace";

interface WorkspaceTrustDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** `trust`: adiciona pasta como workspace confiável (default).
   *  `ingest`: usa o directory browser apenas para escolher a pasta e
   *  encaminha o caminho para o chat indexar via tool ingest_docs. */
  mode?: "trust" | "ingest";
  /** Callback opcional disparado no confirmar — recebe o path absoluto. */
  onConfirmPath?: (path: string) => void;
  /** Pré-navega para esse caminho ao abrir (F.3.5 — quick access). */
  initialPath?: string;
}

export function WorkspaceTrustDialog({
  open,
  onOpenChange,
  mode = "trust",
  onConfirmPath,
  initialPath,
}: WorkspaceTrustDialogProps) {
  const t = useT();
  const create = useWorkspacesStore((s) => s.create);
  const createRemote = useWorkspacesStore((s) => s.createRemote);
  const listSshKeys = useWorkspacesStore((s) => s.listSshKeys);
  const uploadSshKey = useWorkspacesStore((s) => s.uploadSshKey);
  const testSsh = useWorkspacesStore((s) => s.testSsh);
  const listCodespaces = useWorkspacesStore((s) => s.listCodespaces);

  const [tab, setTab] = useState<Tab>("local");
  const [listing, setListing] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [gitInit, setGitInit] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  // SSH state
  const [sshHost, setSshHost] = useState("");
  const [sshPath, setSshPath] = useState("");
  const [sshKeys, setSshKeys] = useState<string[]>([]);
  const [sshKeyId, setSshKeyId] = useState<string>("");
  const [sshTesting, setSshTesting] = useState(false);
  const [sshTestResult, setSshTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  // Codespace state
  const [codespaces, setCodespaces] = useState<CodespaceSummary[]>([]);
  const [codespaceLoading, setCodespaceLoading] = useState(false);
  const [codespaceAvailable, setCodespaceAvailable] = useState(true);
  const [codespaceMessage, setCodespaceMessage] = useState("");
  // Evita resetar o input enquanto o usuário digita um path novo —
  // só sincroniza quando a navegação (clique/Enter) muda o listing.path.
  const lastLoadedPathRef = useRef<string | null>(null);

  /** Fetch direto: precisamos distinguir 403 (fora de safe-root) de
   *  outros erros para mostrar mensagem inline. O `browse` do store
   *  achata erros em `null` e perde essa informação. */
  const load = useCallback(async (path?: string) => {
    setLoading(true);
    setError(null);
    try {
      const q = path ? `?path=${encodeURIComponent(path)}` : "";
      const res = await fetch(`/workspaces/browse${q}`, {
        credentials: "include",
      });
      if (res.status === 403) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Caminho fora das pastas seguras.");
        return;
      }
      if (!res.ok) {
        setError(`Erro ao listar (${res.status}).`);
        return;
      }
      // Se o proxy retornou index.html (backend offline), o content-type é
      // text/html e o JSON.parse falharia — detectar antes de tentar.
      const ct = res.headers.get("content-type") ?? "";
      if (!ct.includes("application/json")) {
        setError(
          "Servidor indisponível. Inicie o backend e reabra este diálogo.",
        );
        return;
      }
      const data = (await res.json()) as BrowseResult;
      setListing(data);
      lastLoadedPathRef.current = data.path;
      setPathInput(data.path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha de rede.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setListing(null);
      setGitInit(true);
      setError(null);
      setPathInput(initialPath ?? "");
      lastLoadedPathRef.current = null;
      setTab("local");
      setSshHost("");
      setSshPath("");
      setSshKeyId("");
      setSshTestResult(null);
      setCodespaces([]);
      void load(initialPath || undefined);
    }
  }, [open, load, initialPath]);

  // G.2.6 — carrega SSH keys e codespaces ao trocar de tab.
  useEffect(() => {
    if (!open) return;
    if (tab === "ssh") {
      void (async () => {
        const keys = await listSshKeys();
        setSshKeys(keys);
      })();
    } else if (tab === "codespace") {
      setCodespaceLoading(true);
      void (async () => {
        const data = await listCodespaces();
        setCodespaces(data.codespaces);
        setCodespaceAvailable(data.available);
        setCodespaceMessage(data.message);
        setCodespaceLoading(false);
      })();
    }
  }, [open, tab, listSshKeys, listCodespaces]);

  const handleGo = () => {
    const target = pathInput.trim();
    if (!target || target === lastLoadedPathRef.current) return;
    void load(target);
  };

  const handleUploadKey = async (file: File) => {
    const keyId = await uploadSshKey(file);
    if (keyId) {
      const keys = await listSshKeys();
      setSshKeys(keys);
      setSshKeyId(keyId);
    }
  };

  const handleTestSsh = async () => {
    if (!sshHost.trim()) return;
    setSshTesting(true);
    setSshTestResult(null);
    const result = await testSsh(sshHost.trim(), sshKeyId || null);
    setSshTesting(false);
    setSshTestResult(result);
  };

  const handleConfirmSsh = async () => {
    if (!sshHost.trim()) return;
    setSubmitting(true);
    const ws = await createRemote({
      transport: "ssh",
      remote_host: sshHost.trim(),
      remote_path: sshPath.trim() || undefined,
      ssh_key_id: sshKeyId || null,
    });
    setSubmitting(false);
    if (ws) onOpenChange(false);
  };

  const handleConfirmCodespace = async (cs: CodespaceSummary) => {
    setSubmitting(true);
    const ws = await createRemote({
      transport: "codespace",
      codespace_name: cs.name,
      name: cs.repository || cs.name,
    });
    setSubmitting(false);
    if (ws) onOpenChange(false);
  };

  const handleConfirm = async () => {
    if (!listing) return;
    if (mode === "ingest") {
      onConfirmPath?.(listing.path);
      onOpenChange(false);
      return;
    }
    setSubmitting(true);
    const ws = await create(listing.path, { trust: true, git_init: gitInit });
    setSubmitting(false);
    if (ws) onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {mode === "ingest"
              ? t("workspace.ingest_title")
              : t("workspace.trust_title")}
          </DialogTitle>
          <DialogDescription>
            {mode === "ingest"
              ? t("workspace.ingest_desc")
              : t("workspace.trust_desc")}
          </DialogDescription>
        </DialogHeader>

        {/* G.2.6 — tabs Local / SSH / Codespace.
            mode="ingest" mantém só Local: ingest é fluxo local-only. */}
        {mode === "trust" && (
          <div className="flex gap-1 border-b border-border/60 pb-1">
            <button
              type="button"
              onClick={() => setTab("local")}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                tab === "local"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Monitor className="w-3.5 h-3.5" /> {t("workspace.tab_local")}
            </button>
            <button
              type="button"
              onClick={() => setTab("ssh")}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                tab === "ssh"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Server className="w-3.5 h-3.5" /> SSH
            </button>
            <button
              type="button"
              onClick={() => setTab("codespace")}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                tab === "codespace"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Cloud className="w-3.5 h-3.5" /> Codespace
            </button>
          </div>
        )}

        {tab === "local" && (
          <>
            {/* Path editável — Enter ou botão "Ir" navega para o destino.
            Backend recusa (403) se o usuário comum sair das pastas seguras. */}
            <div className="flex items-center gap-1.5">
              <Input
                value={pathInput}
                onChange={(e) => setPathInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleGo();
                  }
                }}
                placeholder={t("workspace.path_placeholder")}
                spellCheck={false}
                className="h-8 text-xs font-mono"
                disabled={loading}
              />
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-8 px-2"
                onClick={handleGo}
                disabled={loading || !pathInput.trim()}
                title={t("workspace.go")}
              >
                <CornerDownLeft className="w-3.5 h-3.5" />
              </Button>
            </div>

            {error && (
              <div className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
                {error}
              </div>
            )}

            {/* Directory browser */}
            <ScrollArea className="h-64 rounded-md border border-border">
              <div className="p-1">
                {listing?.parent && (
                  <button
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent text-left transition-colors"
                    onClick={() => load(listing.parent!)}
                    disabled={loading}
                  >
                    <ChevronLeft className="w-4 h-4 shrink-0 text-muted-foreground" />
                    {t("workspace.browse_up")}
                  </button>
                )}

                {/* Atalho explícito para a tela de discos, oculto quando já
                    está nela. Útil quando o usuário pulou direto para uma
                    pasta via texto e quer ver outras unidades. */}
                {listing && !listing.at_drives_root && (
                  <button
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent text-left transition-colors text-muted-foreground"
                    onClick={() => load(DRIVES_PSEUDO_PATH)}
                    disabled={loading}
                  >
                    <HardDrive className="w-4 h-4 shrink-0" />
                    {t("workspace.browse_drives")}
                  </button>
                )}

                {listing && listing.entries.length === 0 && (
                  <p className="px-3 py-4 text-sm text-muted-foreground text-center">
                    {t("workspace.browse_empty")}
                  </p>
                )}

                {listing?.entries.map((entry) => {
                  const isDrive = entry.kind === "drive";
                  const Icon = isDrive ? HardDrive : Folder;
                  return (
                    <button
                      key={entry.path}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent text-left transition-colors"
                      onClick={() => load(entry.path)}
                      disabled={loading}
                    >
                      <Icon
                        className={`w-4 h-4 shrink-0 ${isDrive ? "text-sky-500" : "text-muted-foreground"}`}
                      />
                      <span className="truncate font-medium">{entry.name}</span>
                      {entry.label && (
                        <span className="truncate text-xs text-muted-foreground">
                          {entry.label}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </ScrollArea>

            {mode === "trust" && (
              <label className="flex items-center gap-2 text-sm text-foreground/80 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={gitInit}
                  onChange={(e) => setGitInit(e.target.checked)}
                  className="rounded border-border"
                />
                <GitBranch className="w-4 h-4 shrink-0 text-muted-foreground" />
                {t("workspace.git_init_label")}
              </label>
            )}
          </>
        )}

        {tab === "ssh" && (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                {t("workspace.ssh_host")}
              </label>
              <Input
                value={sshHost}
                onChange={(e) => setSshHost(e.target.value)}
                placeholder="user@host:22"
                className="h-8 text-xs font-mono"
                spellCheck={false}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                {t("workspace.ssh_path")}
              </label>
              <Input
                value={sshPath}
                onChange={(e) => setSshPath(e.target.value)}
                placeholder="/home/user/projects/app"
                className="h-8 text-xs font-mono"
                spellCheck={false}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                {t("workspace.ssh_key")}
              </label>
              <div className="flex items-center gap-1.5">
                <Select
                  value={sshKeyId || "__none__"}
                  onValueChange={(v) => setSshKeyId(v === "__none__" ? "" : v)}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue
                      placeholder={t("workspace.ssh_key_placeholder")}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">
                      {t("workspace.ssh_key_none")}
                    </SelectItem>
                    {sshKeys.map((id) => (
                      <SelectItem key={id} value={id}>
                        {id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <label className="inline-flex items-center gap-1 px-2 h-8 rounded-md border border-border/60 text-xs cursor-pointer hover:bg-muted/50">
                  <Upload className="w-3.5 h-3.5" />
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void handleUploadKey(f);
                    }}
                  />
                </label>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={handleTestSsh}
                disabled={sshTesting || !sshHost.trim()}
                className="h-8"
              >
                {sshTesting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  t("workspace.ssh_test")
                )}
              </Button>
              {sshTestResult && (
                <span
                  className={`text-xs ${
                    sshTestResult.ok ? "text-emerald-500" : "text-destructive"
                  }`}
                >
                  {sshTestResult.ok
                    ? t("workspace.ssh_ok")
                    : sshTestResult.message}
                </span>
              )}
            </div>
          </div>
        )}

        {tab === "codespace" && (
          <div className="space-y-3">
            {codespaceLoading ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {t("workspace.codespaces_loading")}
              </div>
            ) : !codespaceAvailable ? (
              <div className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
                {codespaceMessage || t("workspace.codespaces_unavailable")}
              </div>
            ) : codespaces.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                {t("workspace.codespaces_empty")}
              </p>
            ) : (
              <ScrollArea className="h-64 rounded-md border border-border">
                <div className="p-1 divide-y divide-border/60">
                  {codespaces.map((cs) => (
                    <button
                      key={cs.name}
                      onClick={() => void handleConfirmCodespace(cs)}
                      disabled={submitting}
                      className="w-full text-left px-3 py-2 hover:bg-accent transition-colors"
                    >
                      <div className="text-sm font-medium text-foreground truncate">
                        {cs.repository || cs.name}
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono truncate">
                        {cs.name} · {cs.state}
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("workspace.cancel")}
          </Button>
          {tab === "local" && (
            <Button onClick={handleConfirm} disabled={!listing || submitting}>
              {mode === "ingest"
                ? t("workspace.ingest_confirm")
                : t("workspace.trust_confirm")}
            </Button>
          )}
          {tab === "ssh" && (
            <Button
              onClick={handleConfirmSsh}
              disabled={submitting || !sshHost.trim()}
            >
              {t("workspace.ssh_confirm")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
