/**
 * gha-bot/panel.ts — painel HTML de bot.vectora.company, servido pelo MESMO
 * Worker que já tem as rotas /gha-bot/* (decisão registrada no plano: sem
 * app Vite/deploy próprio). Página única, JS vanilla no cliente, autenticada
 * via cookie `vsession` (Domain=.vectora.company) — sem login próprio, é a
 * mesma sessão da company.
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";

export const ghaBotPanel = new Hono<{ Bindings: Env }>();

function page(appUrl: string): string {
  return `<!doctype html>
<html lang="pt-BR">
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
    <p class="lead" id="gate-text">Verificando sessão...</p>
    <button id="gate-login" hidden>Entrar na Vectora</button>
  </div>

  <div id="app" hidden>
    <h1>Vectora Bot</h1>
    <p class="lead">Revisão automática de pull requests no GitHub Actions.</p>

    <section>
      <h2>Configuração</h2>
      <label for="provider">Provider</label>
      <select id="provider">
        <option value="anthropic">Anthropic</option>
        <option value="openai">OpenAI</option>
        <option value="google_genai">Google (Gemini)</option>
        <option value="openrouter">OpenRouter</option>
        <option value="ollama">Ollama</option>
      </select>
      <label for="model">Modelo</label>
      <input id="model" placeholder="ex.: claude-sonnet-5" />
      <label for="apiKey">Chave de API do provider</label>
      <input id="apiKey" type="password" placeholder="Deixe em branco para manter a chave atual" />
      <label for="reviewStyle">Estilo de revisão</label>
      <select id="reviewStyle">
        <option value="lenient">Leniente</option>
        <option value="balanced">Balanceado</option>
        <option value="strict">Rigoroso</option>
      </select>
      <button id="saveSettings">Salvar</button>
      <div class="msg" id="settingsMsg"></div>
    </section>

    <section>
      <h2>Tokens do GitHub Actions</h2>
      <table>
        <thead><tr><th>ID</th><th>Criado em</th><th>Status</th><th></th></tr></thead>
        <tbody id="tokensBody"></tbody>
      </table>
      <button id="newToken" class="secondary">Gerar novo token</button>
      <div class="msg" id="tokenMsg"></div>
    </section>

    <section>
      <h2>Instalação</h2>
      <p class="lead" style="margin-bottom:12px">
        1. No repositório, crie um <strong>Environment</strong> chamado
        <code>vectora-bot</code> (Settings → Environments) e registre o token
        gerado acima como secret <code>VECTORA_BOT_TOKEN</code> desse
        environment.<br />
        2. Cole o workflow abaixo em <code>.github/workflows/vectora.yml</code>.
      </p>
      <pre id="workflowYaml"></pre>
    </section>
  </div>
</main>
<script>
(function () {
  const APP_URL = ${JSON.stringify(appUrl)};
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
    return new Date(iso.replace(" ", "T") + "Z").toLocaleString("pt-BR");
  }

  async function loadTokens() {
    const res = await api("/gha-bot/tokens");
    const tokens = await res.json();
    const body = document.getElementById("tokensBody");
    body.innerHTML = "";
    if (tokens.length === 0) {
      body.innerHTML = '<tr><td colspan="4" style="color:var(--muted)">Nenhum token ainda.</td></tr>';
      return;
    }
    for (const t of tokens) {
      const tr = document.createElement("tr");
      const revoked = Boolean(t.revoked_at);
      tr.innerHTML =
        "<td>" + t.id.slice(0, 8) + "</td>" +
        "<td>" + fmtDate(t.created_at) + "</td>" +
        '<td><span class="status ' + (revoked ? "revoked" : "ok") + '">' + (revoked ? "revogado" : "ativo") + "</span></td>" +
        "<td></td>";
      if (!revoked) {
        const btn = document.createElement("button");
        btn.className = "danger";
        btn.textContent = "Revogar";
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
    msg.textContent = "Token gerado — copie agora, não será mostrado de novo: " + secret;
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
      msg.textContent = "Informe o modelo.";
      return;
    }
    if (!apiKey) {
      msg.className = "msg error";
      msg.textContent = "Informe a chave de API (a atual não é reenviada por segurança).";
      return;
    }
    const res = await api("/gha-bot/settings", {
      method: "PUT",
      body: JSON.stringify({ provider, model, provider_api_key: apiKey, review_style: reviewStyle }),
    });
    if (res.ok) {
      msg.className = "msg ok";
      msg.textContent = "Salvo.";
      document.getElementById("apiKey").value = "";
    } else {
      const body = await res.json().catch(() => ({}));
      msg.className = "msg error";
      msg.textContent = "Erro: " + (body.error || res.status);
    }
  };

  async function init() {
    try {
      const meRes = await api("/auth/me");
      if (!meRes.ok) throw { unauthorized: true };
    } catch (e) {
      gate.hidden = false;
      gateText.textContent = "Você precisa estar logado na Vectora para acessar o painel do bot.";
      gateLogin.hidden = false;
      gateLogin.onclick = () => {
        window.location.href = APP_URL + "/login?redirect=" + encodeURIComponent(window.location.href);
      };
      return;
    }

    const subRes = await api("/billing/subscription").catch(() => null);
    const sub = subRes && subRes.ok ? await subRes.json() : null;
    if (!sub || sub.tier !== "pro" || sub.status !== "active") {
      gate.hidden = false;
      gateText.textContent = "O Vectora Bot exige o plano Pro.";
      gateLogin.hidden = false;
      gateLogin.textContent = "Assinar Pro";
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

ghaBotPanel.get("/", (c) => c.html(page(c.env.APP_URL)));
