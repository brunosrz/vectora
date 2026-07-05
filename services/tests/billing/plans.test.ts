import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { getPlan, ensureStripePrice } from "../../src/billing/plans";
import { stripeClient } from "../../src/billing/routes";

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockFetch(routes: Record<string, unknown>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const match = Object.entries(routes).find(([prefix]) =>
      url.includes(prefix),
    );
    if (!match) throw new Error(`unmocked fetch: ${url}`);
    return new Response(JSON.stringify(match[1]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

describe("getPlan", () => {
  it("returns the seeded plan by id, and null for an inactive/unknown plan", async () => {
    const plan = await getPlan(env.DB, "3m");
    expect(plan).toMatchObject({ id: "3m", months: 3, price_usd_cents: 2700 });

    expect(await getPlan(env.DB, "does-not-exist")).toBeNull();

    await env.DB.prepare("UPDATE plans SET active = 0 WHERE id = '36m'").run();
    expect(await getPlan(env.DB, "36m")).toBeNull();
  });
});

describe("ensureStripePrice", () => {
  it("creates and persists a Stripe price the first time, then reuses it without calling Stripe again", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.stripe.com/v1/prices/price_test_fake": {
          id: "price_test_fake",
          product: "prod_123",
        },
        "api.stripe.com/v1/prices": { id: "price_new_6m" },
      }),
    );
    const stripe = stripeClient(env);
    const plan = (await getPlan(env.DB, "6m"))!;

    const priceId = await ensureStripePrice(
      stripe,
      env.DB,
      plan,
      "price_test_fake",
    );
    expect(priceId).toBe("price_new_6m");

    const row = await env.DB.prepare(
      "SELECT stripe_price_id FROM plans WHERE id = '6m'",
    ).first<{
      stripe_price_id: string;
    }>();
    expect(row?.stripe_price_id).toBe("price_new_6m");

    const fetchSpy = vi.fn(async () => {
      throw new Error("should not call Stripe again");
    });
    vi.stubGlobal("fetch", fetchSpy);
    const reused = await ensureStripePrice(
      stripe,
      env.DB,
      { ...plan, stripe_price_id: "price_new_6m" },
      "price_test_fake",
    );
    expect(reused).toBe("price_new_6m");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
