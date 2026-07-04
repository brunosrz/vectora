"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import { getToken, rotateToken } from "#/server/fns/token";
import { Copy, Eye, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

interface Props {
  initialAvailable: boolean;
  welcome?: boolean;
}

export default function TokenReveal({ initialAvailable, welcome }: Props) {
  const QUICKSTART = [
    m.token_quickstart_step1(),
    m.token_quickstart_step2(),
    m.token_quickstart_step3(),
    m.token_quickstart_step4(),
  ];
  const [available, setAvailable] = useState(initialAvailable);
  const [token, setToken] = useState<string | null>(null);

  const revealMutation = useMutation({
    mutationFn: () => getToken(),
    onSuccess: (res) => setToken(res.token),
    onError: () => toast.error(m.error_generic()),
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateToken(),
    onSuccess: (res) => {
      setToken(res.token);
      setAvailable(true);
      toast.success(m.token_rotated());
    },
    onError: () => toast.error(m.error_generic()),
  });

  const handleCopy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token);
    toast.success(m.token_copied());
  };

  return (
    <div className="max-w-2xl">
      {welcome && (
        <div className="mb-6 rounded-xl border border-border bg-card/30 p-5">
          <p className="mb-3 font-semibold text-foreground">
            {m.token_quickstart_heading()}
          </p>
          <ol className="space-y-1.5">
            {QUICKSTART.map((step, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 text-sm text-muted-foreground"
              >
                <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-bold">
                  {i + 1}
                </span>
                <code className="font-mono text-foreground/90">{step}</code>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="rounded-xl border border-border bg-card/30 p-6">
        <h2 className="mb-1 text-lg font-semibold text-foreground">
          {m.token_heading()}
        </h2>
        <p className="mb-5 text-sm text-muted-foreground">{m.token_desc()}</p>

        {/* Sem token recuperável ainda (conta legada) — precisa rotacionar
            uma vez pra ter um token recuperável daqui pra frente. */}
        {!available && token === null && (
          <div className="space-y-4">
            <div className="flex items-start gap-2 rounded-lg border border-accent-amber/20 bg-accent-amber/5 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent-amber" />
              <p className="text-sm text-accent-amber">
                {m.token_not_available()}
              </p>
            </div>
            <button
              onClick={() => rotateMutation.mutate()}
              disabled={rotateMutation.isPending}
              className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 hover:bg-primary/90 disabled:opacity-50 transition-all"
            >
              <RefreshCw
                className={`h-4 w-4 ${rotateMutation.isPending ? "animate-spin" : ""}`}
              />
              {rotateMutation.isPending
                ? m.form_submitting()
                : m.token_rotate_cta()}
            </button>
          </div>
        )}

        {/* Token disponível mas ainda não buscado nesta sessão */}
        {available && token === null && (
          <button
            onClick={() => revealMutation.mutate()}
            disabled={revealMutation.isPending}
            className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            <Eye className="h-4 w-4" />
            {revealMutation.isPending
              ? m.form_submitting()
              : m.token_reveal_cta()}
          </button>
        )}

        {/* Token revelado — recuperável a qualquer momento, não é show-once */}
        {token !== null && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 rounded-xl border border-primary/30 bg-background px-4 py-3">
              <code className="flex-1 break-all font-mono text-sm text-primary">
                {token}
              </code>
              <button
                onClick={handleCopy}
                className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-card hover:text-foreground transition-colors"
                title={m.token_copy_cta()}
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-accent-amber/20 bg-accent-amber/5 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent-amber" />
              <p className="text-xs text-accent-amber">
                {m.token_keep_secret_warning()}
              </p>
            </div>
            <button
              onClick={() => rotateMutation.mutate()}
              disabled={rotateMutation.isPending}
              className="flex items-center gap-2 rounded-lg px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${rotateMutation.isPending ? "animate-spin" : ""}`}
              />
              {rotateMutation.isPending
                ? m.form_submitting()
                : m.token_rotate_cta()}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
