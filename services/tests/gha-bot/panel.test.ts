import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { ghaBotPanel, resolveLocale } from "../../src/gha-bot/panel";

describe("gha-bot panel", () => {
  it("serves the panel HTML shell at GET /", async () => {
    const res = await ghaBotPanel.request("/", {}, env);
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toContain("text/html");
    const html = await res.text();
    expect(html).toContain("Vectora Bot");
    expect(html).toContain("/gha-bot/tokens");
  });

  it("renders in Portuguese when Accept-Language asks for pt", async () => {
    const res = await ghaBotPanel.request(
      "/",
      { headers: { "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8" } },
      env,
    );
    const html = await res.text();
    expect(html).toContain('lang="pt"');
    expect(html).toContain("Configuração");
  });

  it("renders in Spanish via the ?lang= override, ignoring Accept-Language", async () => {
    const res = await ghaBotPanel.request(
      "/?lang=es",
      { headers: { "Accept-Language": "pt-BR" } },
      env,
    );
    const html = await res.text();
    expect(html).toContain('lang="es"');
    expect(html).toContain("Configuración");
  });
});

describe("resolveLocale", () => {
  it("resolves pt/es from Accept-Language, falling back to en — erro/borda", () => {
    expect(
      resolveLocale(
        new Request("https://x.test", {
          headers: { "Accept-Language": "pt-BR,pt;q=0.9" },
        }),
      ),
    ).toBe("pt");
    expect(
      resolveLocale(
        new Request("https://x.test", {
          headers: { "Accept-Language": "es-ES" },
        }),
      ),
    ).toBe("es");
    // Sem header, header vazio, ou idioma não suportado (fr) — sempre "en".
    expect(resolveLocale(new Request("https://x.test"))).toBe("en");
    expect(
      resolveLocale(
        new Request("https://x.test", { headers: { "Accept-Language": "" } }),
      ),
    ).toBe("en");
    expect(
      resolveLocale(
        new Request("https://x.test", {
          headers: { "Accept-Language": "fr-FR" },
        }),
      ),
    ).toBe("en");
    // ?lang= inválido (não suportado) é ignorado, cai pro Accept-Language.
    expect(
      resolveLocale(
        new Request("https://x.test/?lang=fr", {
          headers: { "Accept-Language": "pt-BR" },
        }),
      ),
    ).toBe("pt");
  });
});
