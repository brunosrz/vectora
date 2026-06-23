"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import { getToken, rotateToken } from "#/server/fns/token";
import { Copy, Eye, RefreshCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

interface Props {
  initialRevealed: boolean;
  welcome?: boolean;
}

const QUICKSTART = [
  "Revele e copie seu VECTORA_TOKEN abaixo",
  "pip install vectora",
  "vectora setup  (cole o token quando solicitado)",
  "vectora chat",
];

export default function TokenReveal({ initialRevealed, welcome }: Props) {
  const [revealed, setRevealed] = useState(initialRevealed);
  const [token, setToken] = useState<string | null>(null);

  const revealMutation = useMutation({
    mutationFn: () => getToken(),
    onSuccess: (res) => {
      if (res.revealed) {
        setRevealed(true);
      } else {
        setToken(res.token);
        setRevealed(false);
      }
    },
    onError: () => toast.error(m.error_generic()),
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateToken(),
    onSuccess: (res) => {
      setToken(res.token);
      setRevealed(false);
      toast.success(m.token_rotated());
    },
    onError: () => toast.error(m.error_generic()),
  });

  const handleCopy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token);
    toast.success(m.token_copied());
    setToken(null);
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

        {/* State A: not yet revealed */}
        {!revealed && token === null && (
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

        {/* Token shown once */}
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
                {m.token_show_once_warning()}
              </p>
            </div>
          </div>
        )}

        {/* State B: already revealed */}
        {revealed && token === null && (
          <div className="space-y-4">
            <div className="flex items-start gap-2 rounded-lg border border-accent-amber/20 bg-accent-amber/5 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent-amber" />
              <p className="text-sm text-accent-amber">
                {m.token_already_revealed()}
              </p>
            </div>
            <button
              onClick={() => rotateMutation.mutate()}
              disabled={rotateMutation.isPending}
              className="flex items-center gap-2 rounded-xl border border-border px-5 py-2.5 text-sm font-semibold text-foreground/90 hover:border-primary hover:text-foreground disabled:opacity-50 transition-all"
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
      </div>
    </div>
  );
}
