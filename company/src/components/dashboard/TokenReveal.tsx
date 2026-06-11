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
        <div className="mb-6 rounded-xl border border-brand-700 bg-brand-800/30 p-5">
          <p className="mb-3 font-semibold text-white">
            {m.token_quickstart_heading()}
          </p>
          <ol className="space-y-1.5">
            {QUICKSTART.map((step, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 text-sm text-slate-400"
              >
                <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-xs font-bold">
                  {i + 1}
                </span>
                <code className="font-mono text-slate-300">{step}</code>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="rounded-xl border border-brand-700 bg-brand-800/30 p-6">
        <h2 className="mb-1 text-lg font-semibold text-white">
          {m.token_heading()}
        </h2>
        <p className="mb-5 text-sm text-slate-400">{m.token_desc()}</p>

        {/* State A: not yet revealed */}
        {!revealed && token === null && (
          <button
            onClick={() => revealMutation.mutate()}
            disabled={revealMutation.isPending}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white shadow shadow-brand-500/25 hover:bg-brand-400 disabled:opacity-50 transition-all"
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
            <div className="flex items-center gap-2 rounded-xl border border-brand-500/30 bg-brand-950 px-4 py-3">
              <code className="flex-1 break-all font-mono text-sm text-brand-300">
                {token}
              </code>
              <button
                onClick={handleCopy}
                className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-brand-800 hover:text-white transition-colors"
                title={m.token_copy_cta()}
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <p className="text-xs text-amber-300">
                {m.token_show_once_warning()}
              </p>
            </div>
          </div>
        )}

        {/* State B: already revealed */}
        {revealed && token === null && (
          <div className="space-y-4">
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <p className="text-sm text-amber-300">
                {m.token_already_revealed()}
              </p>
            </div>
            <button
              onClick={() => rotateMutation.mutate()}
              disabled={rotateMutation.isPending}
              className="flex items-center gap-2 rounded-xl border border-brand-700 px-5 py-2.5 text-sm font-semibold text-slate-300 hover:border-brand-500 hover:text-white disabled:opacity-50 transition-all"
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
