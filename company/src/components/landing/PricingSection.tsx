"use client";

import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { Check, Minus, ChevronDown } from "lucide-react";
import { track } from "#/lib/analytics/plausible";

type Currency = "BRL" | "USD";

const PLUS = {
  brl: "R$20",
  usd: "$7",
  period: "/mês",
  badge: "Para times pequenos",
  features: [
    { text: "1 workspace", ok: true },
    { text: "Até 5 membros", ok: true },
    { text: "RAG ilimitado", ok: true },
    { text: "MCP integrations", ok: true },
    { text: "REST API /v1 — 60 req/min", ok: true },
    { text: "SDKs Python/TS", ok: true },
    { text: "Suporte por email (48h)", ok: true },
    { text: "Priority support", ok: false },
    { text: "SSO / SAML", ok: false },
  ],
};

const PRO = {
  brl: "R$55",
  usd: "$20",
  period: "/mês",
  badge: "Para empresas",
  features: [
    { text: "Workspaces ilimitados", ok: true },
    { text: "Membros ilimitados", ok: true },
    { text: "RAG ilimitado", ok: true },
    { text: "MCP integrations", ok: true },
    { text: "REST API /v1 — 600 req/min", ok: true },
    { text: "SDKs Python/TS", ok: true },
    { text: "Webhooks", ok: true },
    { text: "ACP server", ok: true },
    { text: "Priority support (SLA 24h)", ok: true },
    { text: "SSO / SAML (em breve)", ok: true },
  ],
};

const COMPARISON_ROWS = [
  { label: "Storage", plus: "10 GB", pro: "Ilimitado" },
  { label: "Projetos", plus: "5", pro: "Ilimitados" },
  { label: "API Keys", plus: "3", pro: "Ilimitadas" },
  { label: "Webhooks", plus: "—", pro: "✓" },
  { label: "Audit log", plus: "7 dias", pro: "90 dias" },
  { label: "SLA", plus: "48h", pro: "24h" },
];

function FeatureRow({ text, ok }: { text: string; ok: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      {ok ? (
        <Check className="h-4 w-4 shrink-0 text-brand-400" />
      ) : (
        <Minus className="h-4 w-4 shrink-0 text-slate-600" />
      )}
      <span className={ok ? "text-slate-300" : "text-slate-600"}>{text}</span>
    </li>
  );
}

export default function PricingSection() {
  const defaultCurrency: Currency =
    typeof navigator !== "undefined" && navigator.language.includes("pt")
      ? "BRL"
      : "USD";
  const [currency, setCurrency] = useState<Currency>(defaultCurrency);
  const [showComparison, setShowComparison] = useState(false);

  const handlePricing = () => track("pricing_viewed");

  return (
    <section
      id="pricing"
      className="px-4 py-20 sm:px-6 lg:px-8"
      onFocus={handlePricing}
    >
      <div className="mx-auto max-w-5xl">
        <div className="mb-10 text-center">
          <h2 className="mb-3 text-3xl font-semibold text-white sm:text-4xl">
            {m.pricing_heading()}
          </h2>
          <p className="mb-6 text-slate-400">{m.pricing_trial()}</p>

          {/* Currency toggle */}
          <div className="inline-flex rounded-lg border border-brand-700 bg-brand-800/60 p-1">
            {(["BRL", "USD"] as Currency[]).map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${
                  currency === c
                    ? "bg-brand-500 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {c === "BRL" ? "🇧🇷 BRL" : "🌍 USD"}
              </button>
            ))}
          </div>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Plus */}
          <div className="rounded-2xl border border-brand-700 bg-brand-800/30 p-7">
            <div className="mb-1 text-xs font-medium text-slate-500">
              {PLUS.badge}
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-white">
                {currency === "BRL" ? PLUS.brl : PLUS.usd}
              </span>
              <span className="text-slate-400">{PLUS.period}</span>
            </div>
            <ul className="mb-8 space-y-2.5">
              {PLUS.features.map((f) => (
                <FeatureRow key={f.text} {...f} />
              ))}
            </ul>
            <Link
              to="/signup"
              search={{ plan: "plus" }}
              className="block w-full rounded-xl border border-brand-500 py-3 text-center text-sm font-semibold text-brand-300 transition-all hover:bg-brand-500 hover:text-white"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>

          {/* Pro */}
          <div className="rounded-2xl border-2 border-brand-500 bg-brand-500/5 p-7 shadow-lg shadow-brand-500/10">
            <div className="mb-1 inline-flex items-center gap-1.5 text-xs font-medium text-brand-400">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
              {PRO.badge}
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-white">
                {currency === "BRL" ? PRO.brl : PRO.usd}
              </span>
              <span className="text-slate-400">{PRO.period}</span>
            </div>
            <ul className="mb-8 space-y-2.5">
              {PRO.features.map((f) => (
                <FeatureRow key={f.text} {...f} />
              ))}
            </ul>
            <Link
              to="/signup"
              search={{ plan: "pro" }}
              className="block w-full rounded-xl bg-brand-500 py-3 text-center text-sm font-semibold text-white shadow shadow-brand-500/30 transition-all hover:bg-brand-400"
            >
              {m.pricing_cta_trial()}
            </Link>
          </div>
        </div>

        {/* Comparison table toggle */}
        <div className="mt-8 text-center">
          <button
            onClick={() => setShowComparison((v) => !v)}
            className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            {m.pricing_compare()}
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showComparison ? "rotate-180" : ""}`}
            />
          </button>

          {showComparison && (
            <div className="mt-6 overflow-hidden rounded-xl border border-brand-700 fade-up">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-700 bg-brand-800/50">
                    <th className="px-5 py-3 text-left font-medium text-slate-400">
                      Feature
                    </th>
                    <th className="px-5 py-3 text-center font-medium text-slate-300">
                      Plus
                    </th>
                    <th className="px-5 py-3 text-center font-medium text-brand-300">
                      Pro
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON_ROWS.map((row, i) => (
                    <tr
                      key={row.label}
                      className={`border-b border-brand-800 ${i % 2 === 0 ? "bg-brand-900/30" : ""}`}
                    >
                      <td className="px-5 py-3 text-slate-400">{row.label}</td>
                      <td className="px-5 py-3 text-center text-slate-400">
                        {row.plus}
                      </td>
                      <td className="px-5 py-3 text-center text-brand-300 font-medium">
                        {row.pro}
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
