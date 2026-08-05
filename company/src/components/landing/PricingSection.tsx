"use client";

import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { Check } from "lucide-react";
import { track } from "#/lib/analytics/plausible";

type Currency = "BRL" | "USD";

const FREE = {
  brl: "R$0",
  usd: "$0",
  badge: m.pricing_free_badge,
  features: [
    m.pricing_feat_local_tools,
    m.pricing_feat_rag_unlimited,
    m.pricing_feat_no_account,
  ],
};

const PRO = {
  brl: "R$24",
  usd: "$9",
  badge: m.pricing_pro_badge,
  features: [
    m.pricing_feat_everything_free,
    m.pricing_feat_chat_web,
    m.pricing_feat_invites_unlimited,
    m.pricing_feat_sso,
    m.pricing_feat_storage_scalable,
    m.pricing_feat_webhooks,
    m.pricing_feat_priority_sla,
  ],
};

function FeatureRow({ text }: { text: () => string }) {
  return (
    <li className="flex items-center gap-2 text-[14px]">
      <Check className="h-4 w-4 shrink-0 text-primary" />
      <span className="text-foreground/90">{text()}</span>
    </li>
  );
}

export default function PricingSection() {
  const [currency, setCurrency] = useState<Currency>("USD");

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
          {/* Free */}
          <div className="flex flex-col justify-between rounded-3xl border border-border bg-card/30 p-7">
            <div className="flex flex-col gap-6">
              {/* Badge */}
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                <span className="text-[12px] font-medium text-muted-foreground">
                  {FREE.badge()}
                </span>
              </div>

              {/* Price */}
              <div className="flex items-baseline gap-1">
                <span className="text-[30px] font-medium leading-[36px] text-foreground">
                  {currency === "BRL" ? FREE.brl : FREE.usd}
                </span>
              </div>

              {/* Features */}
              <ul className="flex flex-col gap-1.5">
                {FREE.features.map((text) => (
                  <FeatureRow key={text()} text={text} />
                ))}
              </ul>
            </div>

            <Link
              to="/downloads"
              className="mt-8 block w-full rounded-2xl bg-[#18191C] py-3 text-center text-[14px] font-semibold text-primary shadow-[0px_1px_3px_rgba(24,25,28,0.3),0px_1px_2px_-1px_rgba(24,25,28,0.3)] transition-opacity hover:opacity-90"
            >
              {m.pricing_cta_download()}
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
                {PRO.features.map((text) => (
                  <FeatureRow key={text()} text={text} />
                ))}
              </ul>
            </div>

            <Link
              to="/signup"
              className="mt-8 block w-full rounded-2xl bg-primary py-3 text-center text-[14px] font-semibold text-[#18191C] shadow-[0px_1px_3px_rgba(121,184,255,0.3),0px_1px_2px_-1px_rgba(121,184,255,0.3)] transition-opacity hover:opacity-90"
            >
              {m.pricing_cta_subscribe_pro()}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
