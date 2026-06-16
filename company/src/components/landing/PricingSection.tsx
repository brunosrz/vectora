"use client";

import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { Check, Minus, ChevronDown } from "lucide-react";
import { track } from "#/lib/analytics/plausible";

type Currency = "BRL" | "USD";

const PLUS = {
  brl: "R$20",
  usd: "$7",
  badge: m.pricing_plus_badge,
  features: [
    { text: m.pricing_feat_workspace5, ok: true },
    { text: m.pricing_feat_members5, ok: true },
    { text: m.pricing_feat_rag_unlimited, ok: true },
    { text: m.pricing_feat_mcp, ok: true },
    { text: m.pricing_feat_sdks, ok: true },
    { text: m.pricing_feat_mcp_acp, ok: true },
    { text: m.pricing_feat_support_sla, ok: true },
    { text: m.pricing_feat_sso, ok: true },
  ],
};

const PRO = {
  brl: "R$55",
  usd: "$20",
  badge: m.pricing_pro_badge,
  features: [
    { text: m.pricing_feat_everything_plus, ok: true },
    { text: m.pricing_feat_workspaces_unlimited, ok: true },
    { text: m.pricing_feat_members_unlimited, ok: true },
    { text: m.pricing_feat_rest_api, ok: true },
    { text: m.pricing_feat_webhooks, ok: true },
    { text: m.pricing_feat_priority_sla, ok: true },
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
    <li className="flex items-center gap-2 text-[14px]">
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
  const [currency, setCurrency] = useState<Currency>("USD");
  const [showComparison, setShowComparison] = useState(false);

  useEffect(() => {
    if (navigator.language.toLowerCase().startsWith("pt")) setCurrency("BRL");
  }, []);

  return (
    <section
      id="pricing"
      className="px-4 py-[23px] sm:px-6"
      onFocus={() => track("pricing_viewed")}
    >
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-8">
        {/* Heading */}
        <div className="flex flex-col items-center gap-3">
          <h2 className="text-center text-[28px] font-semibold leading-[36px] text-foreground">
            {m.pricing_heading()}
          </h2>
          <p className="text-center text-base leading-6 text-muted-foreground">
            {m.pricing_trial()}
          </p>

          {/* Currency toggle */}
          <div className="flex h-[33px] items-center overflow-hidden rounded-xl border border-border bg-card/60 p-px">
            {(["BRL", "USD"] as Currency[]).map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`flex h-8 w-20 items-center justify-center rounded-lg text-[14px] font-medium transition-all ${
                  currency === c
                    ? "bg-primary text-primary-foreground"
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
        <div className="grid w-full grid-cols-1 gap-6 md:grid-cols-2">
          {/* Plus */}
          <div className="flex flex-col justify-between rounded-3xl border border-border bg-card/30 p-7">
            <div className="flex flex-col gap-6">
              {/* Badge */}
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                <span className="text-[12px] font-medium text-muted-foreground">
                  {PLUS.badge()}
                </span>
              </div>

              {/* Price */}
              <div className="flex items-baseline gap-1">
                <span className="text-[30px] font-medium leading-[36px] text-foreground">
                  {currency === "BRL" ? PLUS.brl : PLUS.usd}
                </span>
                <span className="text-muted-foreground">
                  {m.pricing_per_month()}
                </span>
              </div>

              {/* Features */}
              <ul className="flex flex-col gap-1.5">
                {PLUS.features.map((f) => (
                  <FeatureRow key={f.text()} {...f} />
                ))}
              </ul>
            </div>

            <Link
              to="/signup"
              search={{ plan: "plus" }}
              className="mt-8 block w-full rounded-2xl bg-[#18191C] py-3 text-center text-[14px] font-semibold text-primary shadow-[0px_1px_3px_rgba(24,25,28,0.3),0px_1px_2px_-1px_rgba(24,25,28,0.3)] transition-opacity hover:opacity-90"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>

          {/* Pro */}
          <div className="flex flex-col justify-between rounded-3xl border-2 border-border bg-primary/5 p-7 shadow-[0px_10px_15px_-3px_rgba(121,184,255,0.1),0px_4px_6px_-4px_rgba(121,184,255,0.1)]">
            <div className="flex flex-col gap-6">
              {/* Badge */}
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                <span className="text-[12px] font-medium text-primary">
                  {PRO.badge()}
                </span>
              </div>

              {/* Price */}
              <div className="flex items-baseline gap-1">
                <span className="text-[30px] font-medium leading-[36px] text-primary">
                  {currency === "BRL" ? PRO.brl : PRO.usd}
                </span>
                <span className="text-muted-foreground">
                  {m.pricing_per_month()}
                </span>
              </div>

              {/* Features */}
              <ul className="flex flex-col gap-1.5">
                {PRO.features.map((f) => (
                  <FeatureRow key={f.text()} {...f} />
                ))}
              </ul>
            </div>

            <Link
              to="/signup"
              search={{ plan: "pro" }}
              className="mt-8 block w-full rounded-2xl bg-primary py-3 text-center text-[14px] font-semibold text-[#18191C] shadow-[0px_1px_3px_rgba(121,184,255,0.3),0px_1px_2px_-1px_rgba(121,184,255,0.3)] transition-opacity hover:opacity-90"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>
        </div>

        {/* Comparison toggle */}
        <div className="flex flex-col items-center gap-6">
          <button
            onClick={() => setShowComparison((v) => !v)}
            className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {m.pricing_compare()}
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showComparison ? "rotate-180" : ""}`}
            />
          </button>

          {showComparison && (
            <div className="w-full overflow-hidden rounded-xl border border-border fade-up">
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
                      <td className="px-5 py-3 text-center font-medium text-primary">
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
