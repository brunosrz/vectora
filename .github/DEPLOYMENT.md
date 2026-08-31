# Deployment & GitHub Actions

Pipeline definido em [`workflows/runner.yml`](workflows/runner.yml). O setup de
Python/uv é centralizado na composite action
[`actions/setup-uv`](actions/setup-uv/action.yml).

## Visão geral do pipeline

Todo push/PR roda, em ordem:

1. **Lint & Format** — `ruff check src tests` + `ruff format --check`.
2. **Security** — `bandit` + `pip-audit` (best-effort, não bloqueia).
3. **Build Verification** — `compileall src` + build da SPA `chat` (Vite).
4. **Unit / Stress Tests** — `pytest` com coverage (Codecov).
5. **Integration + E2E** — só em `master` e tags `v*` (precisam de chaves reais).
6. **Docker Build & Push** — imagem para `ghcr.io/<repo>`.
7. **Release Native** — só em tags `v*`: Nuitka onefile + instaladores Electron
   (Win/macOS/Linux) via matrix, publicados nas releases privadas.

> Distribuição: a imagem Docker + o [`docker-compose.yml`](../docker-compose.yml)
> da raiz são o caminho self-hosted; os instaladores nativos (desktop) vão para
> o repositório de releases privado consumido pelo update-server.

### Quando a imagem Docker é publicada

- **`push` em `master`** → tag `latest` + `sha-<commit>`.
- **tag `v*`** → tag da versão + `sha-<commit>`.
- **Pull Requests** → apenas build de verificação (sem push).

```bash
docker compose up -d        # usa ghcr.io/vectora-ltda/vectora:latest
# http://localhost:8080
```

## Python 3.13 (não 3.14, por ora)

`PYTHON_VERSION: "3.13"` no workflow casa com o `requires-python` do projeto,
com o `.python-version` da raiz e com a CPython que o `uv` resolve localmente.
O Nuitka 4.1.x (usado no `release-native`) **só suporta oficialmente até 3.13**
— 3.14 vira oficial no Nuitka 4.2. Subir antes disso quebra o build nativo.

## Secrets necessários

Configurados em **Settings → Secrets and variables → Actions**.

| Secret                                                       | Usado em       | Descrição                                                     |
| ------------------------------------------------------------ | -------------- | ------------------------------------------------------------- |
| `GHCR_TOKEN`                                                 | docker-build   | PAT com `write:packages` (fallback: `GITHUB_TOKEN`).          |
| `VECTORA_RELEASES_TOKEN`                                     | release-native | Token p/ publicar instaladores em `vectora-releases`.         |
| `WIN_CERTIFICATE_BASE64` / `WIN_CERTIFICATE_PASSWORD`        | release-native | Assinatura Windows (opcional — sem isso, build não assinado). |
| `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` / `APPLE_TEAM_ID` | release-native | Notarização macOS (opcional).                                 |
| `GOOGLE_API_KEY` / `COHERE_API_KEY` / `TAVILY_API_KEY`       | tests          | Chaves para integration/e2e (opcionais nos unit).             |
| `LLM_PROVIDER` / `LOG_LEVEL`                                 | tests          | Config dos testes (defaults: `google-genai` / `INFO`).        |

## Rollback (self-hosted Docker)

```bash
docker pull ghcr.io/vectora-ltda/vectora:sha-<commit-anterior>
# Aponte o docker-compose.yml para a tag específica e suba de novo.
docker compose up -d
```

Lista de tags: `docker image ls ghcr.io/vectora-ltda/vectora`.

---

**Removido nesta revisão:** jobs de deploy via SSH/VPS, publicação no PyPI e no
NPM. A distribuição agora é **imagem Docker (GHCR) + instaladores nativos**.
Atualizações do desktop são geridas pelo [`services`](../services/) (era
`update-server/`, unificado com o `relay/` — renomeado `gateway/` — nesta fase).
