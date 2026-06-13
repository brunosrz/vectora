"use client";

import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { Check, Minus, ChevronDown } from "lucide-react";
import { track } from "#/lib/analytics/plausible";

type Currency = "BRL" | "USD";

// Tudo que é texto humano vem dos messages (paraglide) — nada hardcoded.
const PLUS = {
  brl: "R$20",
  usd: "$7",
  badge: m.pricing_plus_badge,
  features: [
    { text: m.pricing_feat_workspace1, ok: true },
    { text: m.pricing_feat_members5, ok: true },
    { text: m.pricing_feat_rag_unlimited, ok: true },
    { text: m.pricing_feat_mcp, ok: true },
    { text: m.pricing_feat_api60, ok: true },
    { text: m.pricing_feat_sdks, ok: true },
    { text: m.pricing_feat_email_support, ok: true },
    { text: m.pricing_feat_priority_support, ok: false },
    { text: m.pricing_feat_sso, ok: false },
  ],
};

const PRO = {
  brl: "R$55",
  usd: "$20",
  badge: m.pricing_pro_badge,
  features: [
    { text: m.pricing_feat_workspaces_unlimited, ok: true },
    { text: m.pricing_feat_members_unlimited, ok: true },
    { text: m.pricing_feat_rag_unlimited, ok: true },
    { text: m.pricing_feat_mcp, ok: true },
    { text: m.pricing_feat_api600, ok: true },
    { text: m.pricing_feat_sdks, ok: true },
    { text: m.pricing_feat_webhooks, ok: true },
    { text: m.pricing_feat_acp, ok: true },
    { text: m.pricing_feat_priority_sla, ok: true },
    { text: m.pricing_feat_sso_soon, ok: true },
  ],
};

const COMPARISON_ROWS = [
  {
    label: m.pricing_cmp_storage,
    plus: () => "10 GB",
    pro: m.pricing_cmp_unlimited,
  },
  {
    label: m.pricing_cmp_projects,
    plus: () => "5",
    pro: m.pricing_cmp_unlimited,
  },
  {
    label: m.pricing_cmp_api_keys,
    plus: () => "3",
    pro: m.pricing_cmp_unlimited,
  },
  { label: m.pricing_feat_webhooks, plus: () => "—", pro: () => "✓" },
  {
    label: m.pricing_cmp_audit,
    plus: m.pricing_cmp_days7,
    pro: m.pricing_cmp_days90,
  },
  { label: m.pricing_cmp_sla, plus: () => "48h", pro: () => "24h" },
];

function FeatureRow({ text, ok }: { text: () => string; ok: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      {ok ? (
        <Check className="h-4 w-4 shrink-0 text-primary" />
      ) : (
        <Minus className="h-4 w-4 shrink-0 text-muted-foreground/80" />
      )}
      <span className={ok ? "text-foreground/90" : "text-muted-foreground/80"}>
        {text()}
      </span>
    </li>
  );
}

export default function PricingSection() {
  // Padrão USD para todos; só vira BRL após hidratar SE o navegador indicar
  // Brasil (pt-BR). Iniciar fixo em "USD" evita hydration mismatch — o SSR
  // não tem `navigator`, então o estado inicial precisa ser igual nos dois lados.
  const [currency, setCurrency] = useState<Currency>("USD");
  const [showComparison, setShowComparison] = useState(false);

  useEffect(() => {
    if (navigator.language.toLowerCase().startsWith("pt")) setCurrency("BRL");
  }, []);

  const handlePricing = () => track("pricing_viewed");

  return (
    <section
      id="pricing"
      className="px-4 py-10 sm:px-6 sm:py-14 lg:px-8"
      onFocus={handlePricing}
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-10 text-center">
          <h2 className="mb-3 text-2xl font-semibold text-foreground sm:text-3xl">
            {m.pricing_heading()}
          </h2>
          <p className="mb-6 text-muted-foreground">{m.pricing_trial()}</p>

          {/* Currency toggle */}
          <div className="inline-flex rounded-lg border border-border bg-card/60 p-1">
            {(["BRL", "USD"] as Currency[]).map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${
                  currency === c
                    ? "bg-primary text-primary-foreground shadow"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {c === "BRL"
                  ? `🇧🇷 ${m.pricing_toggle_brl()}`
                  : `🌍 ${m.pricing_toggle_usd()}`}
              </button>
            ))}
          </div>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Plus */}
          <div className="rounded-2xl border border-border bg-card/30 p-7">
            <div className="mb-1 text-xs font-medium text-muted-foreground">
              {PLUS.badge()}
            </div>
            <div className="mb-6">
              <span className="text-3xl font-bold text-foreground">
                {currency === "BRL" ? PLUS.brl : PLUS.usd}
              </span>
              <span className="text-muted-foreground">
                {m.pricing_per_month()}
              </span>
            </div>
            <ul className="mb-8 space-y-2.5">
              {PLUS.features.map((f) => (
                <FeatureRow key={f.text()} {...f} />
              ))}
            </ul>
            <Link
              to="/signup"
              search={{ plan: "plus" }}
              className="block w-full rounded-xl border border-primary py-3 text-center text-sm font-semibold text-primary transition-all hover:bg-primary hover:text-primary-foreground"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>

          {/* Pro */}
          <div className="rounded-2xl border-2 border-primary bg-primary/5 p-7 shadow-lg shadow-primary/10">
            <div className="mb-1 inline-flex items-center gap-1.5 text-xs font-medium text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              {PRO.badge()}
            </div>
            <div className="mb-6">
              <span className="text-3xl font-bold text-foreground">
                {currency === "BRL" ? PRO.brl : PRO.usd}
              </span>
              <span className="text-muted-foreground">
                {m.pricing_per_month()}
              </span>
            </div>
            <ul className="mb-8 space-y-2.5">
              {PRO.features.map((f) => (
                <FeatureRow key={f.text()} {...f} />
              ))}
            </ul>
            <Link
              to="/signup"
              search={{ plan: "pro" }}
              className="block w-full rounded-xl bg-primary py-3 text-center text-sm font-semibold text-primary-foreground shadow shadow-primary/30 transition-all hover:bg-primary/90"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>
        </div>

        {/* Comparison table toggle */}
        <div className="mt-8 text-center">
          <button
            onClick={() => setShowComparison((v) => !v)}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {m.pricing_compare()}
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showComparison ? "rotate-180" : ""}`}
            />
          </button>

          {showComparison && (
            <div className="mt-6 overflow-hidden rounded-xl border border-border fade-up">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-card/50">
                    <th className="px-5 py-3 text-left font-medium text-muted-foreground">
                      {m.pricing_cmp_feature()}
                    </th>
                    <th className="px-5 py-3 text-center font-medium text-foreground/90">
                      Plus
                    </th>
                    <th className="px-5 py-3 text-center font-medium text-primary">
                      Pro
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON_ROWS.map((row, i) => (
                    <tr
                      key={row.label()}
                      className={`border-b border-border ${i % 2 === 0 ? "bg-background/30" : ""}`}
                    >
                      <td className="px-5 py-3 text-muted-foreground">
                        {row.label()}
                      </td>
                      <td className="px-5 py-3 text-center text-muted-foreground">
                        {row.plus()}
                      </td>
                      <td className="px-5 py-3 text-center text-primary font-medium">
                        {row.pro()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
