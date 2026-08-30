/**
 * gha-bot/panel.ts — painel HTML de bot.vectora.company, servido pelo MESMO
 * Worker que já tem as rotas /gha-bot/* (decisão registrada no plano: sem
 * app Vite/deploy próprio). Página única, JS vanilla no cliente, autenticada
 * via cookie `vsession` (Domain=.vectora.company) — sem login próprio, é a
 * mesma sessão da company.
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { m } from "../paraglide/messages";
import { locales, type Locale } from "../paraglide/runtime";

export const ghaBotPanel = new Hono<{ Bindings: Env }>();

/** Resolve o idioma do painel — sem cookie de preferência salvo hoje (página
 * fresca por visita), então lê o primeiro idioma suportado do
 * `Accept-Language`, com override manual via `?lang=` pra facilitar teste.
 * Paraglide roda no Worker (sem `window`/`navigator`), por isso o locale é
 * sempre resolvido aqui e passado explícito em cada `m.*()` — nunca via
 * `getLocale()` implícito. */
export function resolveLocale(req: Request): Locale {
  const url = new URL(req.url);
  const override = url.searchParams.get("lang");
  if (override && (locales as readonly string[]).includes(override)) {
    return override as Locale;
  }
  const header = req.headers.get("Accept-Language") ?? "";
  for (const part of header.split(",")) {
    const tag = part.split(";")[0]?.trim().toLowerCase();
    const lang = tag?.split("-")[0];
    if (lang && (locales as readonly string[]).includes(lang)) {
      return lang as Locale;
    }
  }
  return "en";
}

// Marcador único (não pode aparecer em nenhuma tradução real) usado só pra
// extrair o prefixo antes de {secret} em gha_bot_panel_token_generated, sem
// depender de nenhum caractere específico da string traduzida.
const SECRET_SPLIT_MARKER = "@@SECRET@@";

function page(appUrl: string, locale: Locale): string {
  const t = {
    lead: m.gha_bot_panel_lead({}, { locale }),
    gateChecking: m.gha_bot_panel_gate_checking({}, { locale }),
    gateLoginRequired: m.gha_bot_panel_gate_login_required({}, { locale }),
    gateLoginButton: m.gha_bot_panel_gate_login_button({}, { locale }),
    gateProRequired: m.gha_bot_panel_gate_pro_required({}, { locale }),
    gateProButton: m.gha_bot_panel_gate_pro_button({}, { locale }),
    settingsTitle: m.gha_bot_panel_settings_title({}, { locale }),
    labelProvider: m.gha_bot_panel_label_provider({}, { locale }),
    labelModel: m.gha_bot_panel_label_model({}, { locale }),
    labelApiKey: m.gha_bot_panel_label_api_key({}, { locale }),
    apiKeyPlaceholder: m.gha_bot_panel_api_key_placeholder({}, { locale }),
    labelReviewStyle: m.gha_bot_panel_label_review_style({}, { locale }),
    reviewStyleLenient: m.gha_bot_panel_review_style_lenient({}, { locale }),
    reviewStyleBalanced: m.gha_bot_panel_review_style_balanced({}, { locale }),
    reviewStyleStrict: m.gha_bot_panel_review_style_strict({}, { locale }),
    saveButton: m.gha_bot_panel_save_button({}, { locale }),
    tokensTitle: m.gha_bot_panel_tokens_title({}, { locale }),
    tableId: m.gha_bot_panel_table_id({}, { locale }),
    tableCreatedAt: m.gha_bot_panel_table_created_at({}, { locale }),
    tableStatus: m.gha_bot_panel_table_status({}, { locale }),
    newTokenButton: m.gha_bot_panel_new_token_button({}, { locale }),
    revokeButton: m.gha_bot_panel_revoke_button({}, { locale }),
    statusActive: m.gha_bot_panel_status_active({}, { locale }),
    statusRevoked: m.gha_bot_panel_status_revoked({}, { locale }),
    noTokens: m.gha_bot_panel_no_tokens({}, { locale }),
    installTitle: m.gha_bot_panel_install_title({}, { locale }),
    installInstructions: m.gha_bot_panel_install_instructions({}, { locale }),
    errorMissingModel: m.gha_bot_panel_error_missing_model({}, { locale }),
    errorMissingKey: m.gha_bot_panel_error_missing_key({}, { locale }),
    saved: m.gha_bot_panel_saved({}, { locale }),
    errorPrefix: m.gha_bot_panel_error_prefix({}, { locale }),
  };
  // Interpolado no server (Paraglide não roda no browser) — o cliente só
  // concatena o secret depois do prefixo, nunca chama m() por conta própria.
  const tokenGeneratedPrefix = m
    .gha_bot_panel_token_generated({ secret: SECRET_SPLIT_MARKER }, { locale })
    .split(SECRET_SPLIT_MARKER)[0] as string;

  return `<!doctype html>
<html lang="${locale}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Vectora Bot</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #0b0d10;
    --surface: #14171b;
    --border: #262b31;
    --text: #e6e8eb;
    --muted: #8a929c;
    --accent: #5b8cff;
    --danger: #e5534b;
    --ok: #3fb950;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font: 15px/1.5 -apple-system, "Segoe UI", Inter, sans-serif;
  }
  main { max-width: 720px; margin: 0 auto; padding: 48px 20px 96px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 0 0 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
  p.lead { color: var(--muted); margin: 0 0 32px; }
  section { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; }
  label { display: block; font-size: 13px; color: var(--muted); margin: 12px 0 4px; }
  label:first-child { margin-top: 0; }
  input, select {
    width: 100%; padding: 9px 10px; background: var(--bg); border: 1px solid var(--border);
    border-radius: 6px; color: var(--text); font-size: 14px;
  }
  button {
    background: var(--accent); color: #fff; border: none; border-radius: 6px;
    padding: 9px 16px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 16px;
  }
  button.secondary { background: transparent; border: 1px solid var(--border); color: var(--text); }
  button.danger { background: transparent; border: 1px solid var(--danger); color: var(--danger); margin-top: 0; }
  button:disabled { opacity: .5; cursor: default; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 4px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; }
  .status { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
  .status.ok { background: rgba(63,185,80,.15); color: var(--ok); }
  .status.revoked { background: rgba(229,83,75,.15); color: var(--danger); }
  pre { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 14px; overflow-x: auto; font-size: 12.5px; }
  .msg { font-size: 13px; margin-top: 10px; }
  .msg.error { color: var(--danger); }
  .msg.ok { color: var(--ok); }
  a { color: var(--accent); }
  #gate { text-align: center; padding: 64px 20px; }
</style>
</head>
<body>
<main>
  <div id="gate" hidden>
    <h1>Vectora Bot</h1>
    <p class="lead" id="gate-text">${t.gateChecking}</p>
    <button id="gate-login" hidden></button>
  </div>

  <div id="app" hidden>
    <h1>Vectora Bot</h1>
    <p class="lead">${t.lead}</p>

    <section>
      <h2>${t.settingsTitle}</h2>
      <label for="provider">${t.labelProvider}</label>
      <select id="provider">
        <option value="anthropic">Anthropic</option>
        <option value="openai">OpenAI</option>
        <option value="google_genai">Google (Gemini)</option>
        <option value="openrouter">OpenRouter</option>
        <option value="ollama">Ollama</option>
      </select>
      <label for="model">${t.labelModel}</label>
      <input id="model" placeholder="ex.: claude-sonnet-5" />
      <label for="apiKey">${t.labelApiKey}</label>
      <input id="apiKey" type="password" placeholder="${t.apiKeyPlaceholder}" />
      <label for="reviewStyle">${t.labelReviewStyle}</label>
      <select id="reviewStyle">
        <option value="lenient">${t.reviewStyleLenient}</option>
        <option value="balanced">${t.reviewStyleBalanced}</option>
        <option value="strict">${t.reviewStyleStrict}</option>
      </select>
      <button id="saveSettings">${t.saveButton}</button>
      <div class="msg" id="settingsMsg"></div>
    </section>

    <section>
      <h2>${t.tokensTitle}</h2>
      <table>
        <thead><tr><th>${t.tableId}</th><th>${t.tableCreatedAt}</th><th>${t.tableStatus}</th><th></th></tr></thead>
        <tbody id="tokensBody"></tbody>
      </table>
      <button id="newToken" class="secondary">${t.newTokenButton}</button>
      <div class="msg" id="tokenMsg"></div>
    </section>

    <section>
      <h2>${t.installTitle}</h2>
      <p class="lead" style="margin-bottom:12px">${t.installInstructions}</p>
      <pre id="workflowYaml"></pre>
    </section>
  </div>
</main>
<script>
(function () {
  const APP_URL = ${JSON.stringify(appUrl)};
  const LOCALE = ${JSON.stringify(locale)};
  const T = ${JSON.stringify({
    noTokens: t.noTokens,
    statusActive: t.statusActive,
    statusRevoked: t.statusRevoked,
    revokeButton: t.revokeButton,
    tokenGeneratedPrefix,
    gateLoginRequired: t.gateLoginRequired,
    gateLoginButton: t.gateLoginButton,
    gateProRequired: t.gateProRequired,
    gateProButton: t.gateProButton,
    errorMissingModel: t.errorMissingModel,
    errorMissingKey: t.errorMissingKey,
    saved: t.saved,
    errorPrefix: t.errorPrefix,
  })};
  const gate = document.getElementById("gate");
  const gateText = document.getElementById("gate-text");
  const gateLogin = document.getElementById("gate-login");
  const app = document.getElementById("app");

  const WORKFLOW_YAML = [
    "name: Vectora",
    "",
    "on:",
    "  pull_request:",
    "    types: [opened, synchronize]",
    "",
    "permissions:",
    "  pull-requests: write",
    "  contents: read",
    "",
    "jobs:",
    "  review:",
    "    runs-on: ubuntu-latest",
    "    environment: vectora-bot",
    "    steps:",
    "      - uses: actions/checkout@v6",
    "        with:",
    "          fetch-depth: 0",
    "",
    "      - uses: vectora-ltda/vectora-review-action@v1",
    "        with:",
    "          token: \${{ secrets.VECTORA_BOT_TOKEN }}",
    "          github-token: \${{ secrets.GITHUB_TOKEN }}",
  ].join("\\n");
  document.getElementById("workflowYaml").textContent = WORKFLOW_YAML;

  async function api(path, init) {
    const res = await fetch(path, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(init && init.headers) },
    });
    if (res.status === 401) throw { unauthorized: true };
    return res;
  }

  function fmtDate(iso) {
    return new Date(iso.replace(" ", "T") + "Z").toLocaleString(LOCALE);
  }

  async function loadTokens() {
    const res = await api("/gha-bot/tokens");
    const tokens = await res.json();
    const body = document.getElementById("tokensBody");
    body.innerHTML = "";
    if (tokens.length === 0) {
      body.innerHTML = '<tr><td colspan="4" style="color:var(--muted)">' + T.noTokens + '</td></tr>';
      return;
    }
    for (const t of tokens) {
      const tr = document.createElement("tr");
      const revoked = Boolean(t.revoked_at);
      tr.innerHTML =
        "<td>" + t.id.slice(0, 8) + "</td>" +
        "<td>" + fmtDate(t.created_at) + "</td>" +
        '<td><span class="status ' + (revoked ? "revoked" : "ok") + '">' + (revoked ? T.statusRevoked : T.statusActive) + "</span></td>" +
        "<td></td>";
      if (!revoked) {
        const btn = document.createElement("button");
        btn.className = "danger";
        btn.textContent = T.revokeButton;
        btn.onclick = async () => {
          btn.disabled = true;
          await api("/gha-bot/tokens/" + t.id + "/revoke", { method: "POST" });
          await loadTokens();
        };
        tr.lastElementChild.appendChild(btn);
      }
      body.appendChild(tr);
    }
  }

  document.getElementById("newToken").onclick = async () => {
    const res = await api("/gha-bot/tokens", { method: "POST", body: "{}" });
    const { secret } = await res.json();
    const msg = document.getElementById("tokenMsg");
    msg.className = "msg ok";
    msg.textContent = T.tokenGeneratedPrefix + secret;
    await loadTokens();
  };

  async function loadSettings() {
    const res = await api("/gha-bot/settings");
    const settings = await res.json();
    if (!settings) return;
    document.getElementById("provider").value = settings.provider;
    document.getElementById("model").value = settings.model;
    document.getElementById("reviewStyle").value = settings.review_style;
  }

  document.getElementById("saveSettings").onclick = async () => {
    const msg = document.getElementById("settingsMsg");
    const provider = document.getElementById("provider").value;
    const model = document.getElementById("model").value.trim();
    const apiKey = document.getElementById("apiKey").value;
    const reviewStyle = document.getElementById("reviewStyle").value;
    if (!model) {
      msg.className = "msg error";
      msg.textContent = T.errorMissingModel;
      return;
    }
    if (!apiKey) {
      msg.className = "msg error";
      msg.textContent = T.errorMissingKey;
      return;
    }
    const res = await api("/gha-bot/settings", {
      method: "PUT",
      body: JSON.stringify({ provider, model, provider_api_key: apiKey, review_style: reviewStyle }),
    });
    if (res.ok) {
      msg.className = "msg ok";
      msg.textContent = T.saved;
      document.getElementById("apiKey").value = "";
    } else {
      const body = await res.json().catch(() => ({}));
      msg.className = "msg error";
      msg.textContent = T.errorPrefix + (body.error || res.status);
    }
  };

  async function init() {
    try {
      const meRes = await api("/auth/me");
      if (!meRes.ok) throw { unauthorized: true };
    } catch (e) {
      gate.hidden = false;
      gateText.textContent = T.gateLoginRequired;
      gateLogin.hidden = false;
      gateLogin.textContent = T.gateLoginButton;
      gateLogin.onclick = () => {
        window.location.href = APP_URL + "/login?redirect=" + encodeURIComponent(window.location.href);
      };
      return;
    }

    const subRes = await api("/billing/subscription").catch(() => null);
    const sub = subRes && subRes.ok ? await subRes.json() : null;
    if (!sub || sub.tier !== "pro" || sub.status !== "active") {
      gate.hidden = false;
      gateText.textContent = T.gateProRequired;
      gateLogin.hidden = false;
      gateLogin.textContent = T.gateProButton;
      gateLogin.onclick = () => {
        window.location.href = APP_URL + "/dashboard/billing";
      };
      return;
    }

    app.hidden = false;
    await Promise.all([loadSettings(), loadTokens()]);
  }

  init();
})();
</script>
</body>
</html>`;
}

ghaBotPanel.get("/", (c) =>
  c.html(page(c.env.APP_URL, resolveLocale(c.req.raw))),
);
