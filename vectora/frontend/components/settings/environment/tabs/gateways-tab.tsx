"use client";

/**
 * GatewaysTab — modelos de LLM locais/dinâmicos (hoje: Ollama).
 *
 * Descoberta via GET /gateways/ollama/models (consulta {base_url}/api/tags
 * do host configurado — nunca digitação livre de nome de modelo, evita erro
 * de digitação virar falha silenciosa no chat). Modelos registrados via
 * POST /gateways/ollama/registered aparecem no ModelSelector do composer
 * (GET /models/providers agrega o catálogo estático com os registrados).
 */

import { Loader2, Plus, RefreshCw, Server, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { m } from "@/lib/paraglide/messages";

interface OllamaModelInfo {
  name: string;
  size: number | null;
  modified_at: string | null;
}

interface RegisteredModel {
  id: string;
  tag: string;
  created_at: string;
}

async function discoverModels(): Promise<{
  reachable: boolean;
  models: OllamaModelInfo[];
}> {
  const res = await fetch("/gateways/ollama/models");
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function fetchRegistered(): Promise<RegisteredModel[]> {
  const res = await fetch("/gateways/ollama/registered");
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

async function registerModel(tag: string): Promise<void> {
  const res = await fetch("/gateways/ollama/registered", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag }),
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

async function unregisterModel(id: string): Promise<void> {
  const res = await fetch(`/gateways/ollama/registered/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
}

export function GatewaysTab() {
  const [registered, setRegistered] = useState<RegisteredModel[]>([]);
  const [loadingRegistered, setLoadingRegistered] = useState(true);
  const [discovered, setDiscovered] = useState<OllamaModelInfo[] | null>(null);
  const [reachable, setReachable] = useState<boolean | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [registeringTag, setRegisteringTag] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRegistered = useCallback(async () => {
    setLoadingRegistered(true);
    try {
      setRegistered(await fetchRegistered());
    } catch {
      setError(m.gateways_error_load());
    } finally {
      setLoadingRegistered(false);
    }
  }, []);

  useEffect(() => {
    void loadRegistered();
  }, [loadRegistered]);

  const handleDiscover = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const data = await discoverModels();
      setReachable(data.reachable);
      setDiscovered(data.models);
    } catch {
      setReachable(false);
      setDiscovered([]);
      setError(m.gateways_error_discover());
    } finally {
      setDiscovering(false);
    }
  };

  const handleRegister = async (tag: string) => {
    setRegisteringTag(tag);
    setError(null);
    try {
      await registerModel(tag);
      await loadRegistered();
    } catch {
      setError(m.gateways_error_register());
    } finally {
      setRegisteringTag(null);
    }
  };

  const handleRemove = async (id: string) => {
    setRemovingId(id);
    setError(null);
    try {
      await unregisterModel(id);
      setRegistered((prev) => prev.filter((model) => model.id !== id));
    } catch {
      setError(m.gateways_error_remove());
    } finally {
      setRemovingId(null);
    }
  };

  const registeredTags = new Set(registered.map((model) => model.tag));

  return (
    <div className="space-y-4">
      <div className="space-y-0.5">
        <p className="text-sm font-medium flex items-center gap-1.5">
          <Server className="w-3.5 h-3.5 text-muted-foreground" />
          {m.gateways_ollama_title()}
        </p>
        <p className="text-xs text-muted-foreground max-w-[360px]">
          {m.gateways_ollama_subtitle()}
        </p>
      </div>

      {error && (
        <p className="text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-md">
          {error}
        </p>
      )}

      {/* Descoberta */}
      <div className="space-y-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => void handleDiscover()}
          disabled={discovering}
        >
          {discovering ? (
            <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          )}
          {m.gateways_detect_models()}
        </Button>

        {reachable === false && (
          <p className="text-xs text-muted-foreground">
            {m.gateways_ollama_unreachable()}
          </p>
        )}

        {discovered && discovered.length > 0 && (
          <div className="space-y-1.5">
            {discovered.map((model) => {
              const already = registeredTags.has(model.name);
              return (
                <div
                  key={model.name}
                  className="flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2"
                >
                  <span className="text-sm font-mono truncate">
                    {model.name}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs shrink-0"
                    onClick={() => void handleRegister(model.name)}
                    disabled={already || registeringTag === model.name}
                  >
                    {registeringTag === model.name ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : already ? (
                      m.gateways_already_registered()
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5 mr-1" />
                        {m.gateways_register()}
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Registrados */}
      <div className="space-y-2 pt-2 border-t">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {m.gateways_registered_title()}
        </p>
        {loadingRegistered ? (
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        ) : registered.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            {m.gateways_registered_empty()}
          </p>
        ) : (
          <div className="space-y-1.5">
            {registered.map((model) => (
              <div
                key={model.id}
                className="flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2"
              >
                <span className="text-sm font-mono truncate">{model.tag}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive shrink-0"
                  onClick={() => void handleRemove(model.id)}
                  disabled={removingId === model.id}
                >
                  {removingId === model.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
