# Deployment and GitHub Actions

This document describes how to configure and use the Vectora CI/CD pipeline.

## Required Secrets

All secrets live in the **GitHub Environment "Production"** (`Settings → Environments → Production`).
Every job in `runner.yml` declares `environment: Production` — without this, secrets are invisible to the job.

### Infrastructure Secrets (Docker / VPS)

| Secret            | Description                                                                                                                                                                                           |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GHCR_TOKEN`      | Personal Access Token (classic) with `write:packages` + `read:packages`. Create at github.com/settings/tokens. Required because `GITHUB_TOKEN` returns 403 on personal accounts when pushing to GHCR. |
| `VPS_SSH_KEY`     | SSH private key to connect to the VPS (RSA or Ed25519).                                                                                                                                               |
| `VPS_HOST`        | Full VPS hostname. Example: `srv1640150.hstgr.cloud`                                                                                                                                                  |
| `VPS_USER`        | SSH user. Example: `root`                                                                                                                                                                             |
| `VPS_PORT`        | SSH port. Example: `22` (optional — defaults to 22)                                                                                                                                                   |
| `VPS_DEPLOY_PATH` | Path on the VPS where `docker-compose.yml` will be copied. Example: `docker/vectora`                                                                                                                  |

### API Secrets (for tests and runtime)

| Secret               | Description                                 |
| -------------------- | ------------------------------------------- |
| `GOOGLE_API_KEY`     | Google Gemini API key for tests and LLM     |
| `COHERE_API_KEY`     | Cohere API key for embeddings and reranking |
| `TAVILY_API_KEY`     | Tavily API key for web search               |
| `LANGSMITH_API_KEY`  | LangSmith API key for tracing (optional)    |
| `LANGSMITH_ENDPOINT` | LangSmith endpoint (optional)               |
| `LANGSMITH_PROJECT`  | LangSmith project name (optional)           |
| `LANGSMITH_TRACING`  | `true` or `false` (optional)                |
| `LLM_PROVIDER`       | Default provider for tests: `google-genai`  |
| `LOG_LEVEL`          | Log level: `INFO`                           |

> **Note:** These keys are **never** embedded in the PyPI wheel or the Docker image. The VPS must have a `.env` created manually (see section below).

### Generate SSH Key for Deploy

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vectora-deploy -C "vectora-deploy"
# Add the public key to the VPS:
ssh-copy-id -i ~/.ssh/vectora-deploy.pub root@$VPS_HOST
# Copy the private key content to the VPS_SSH_KEY secret:
cat ~/.ssh/vectora-deploy
```

---

## Configuring Secrets

### Via CLI (gh)

```bash
gh secret set GHCR_TOKEN --env Production
gh secret set VPS_SSH_KEY --env Production --body-file ~/.ssh/vectora-deploy
gh secret set VPS_HOST --env Production -b "srv1640150.hstgr.cloud"
gh secret set VPS_USER --env Production -b "root"
gh secret set VPS_DEPLOY_PATH --env Production -b "docker/vectora"
gh secret set GOOGLE_API_KEY --env Production
gh secret set COHERE_API_KEY --env Production
gh secret set TAVILY_API_KEY --env Production
```

### Via GitHub Web

1. Go to: **Settings → Environments → Production → Add secret**
2. Add each secret with its exact name and value

---

## CI/CD Pipeline

### Normal Flow (without `[deploy]`)

Any push to any branch runs:

1. **Setup** — installs dependencies via `uv sync`
2. **Lint** — `ruff check`
3. **Build** — `python -m compileall vectora`
4. **Unit Tests** — `pytest tests/unit/` with coverage upload to Codecov
5. **Stress Tests** — `pytest tests/stress/`
6. **Integration Tests** — `pytest tests/integration/` (continues on error if no real keys)
7. **E2E Tests** — `pytest tests/e2e/` (always passes — `|| true`)
8. **Security** — `safety check`

### Automatic Deploy (with `[deploy]`)

When the commit title contains `[deploy]`, additional jobs run after the tests:

```bash
git commit -m "feat: new feature [deploy]"
git push
```

Full pipeline:

1. All test jobs above
2. **Docker Build & Push** — builds image and pushes to `ghcr.io/brunosrz/vectora:latest`
3. **Deploy to VPS** — copies `docker-compose.yml` via SCP + SSH to update the container
4. **Publish to PyPI** — publishes `vectora-agent` to PyPI via Trusted Publishing (OIDC)

---

## PyPI — Trusted Publishing (one-time setup)

The pipeline uses **Trusted Publishing** (no stored token or password). Requires one-time configuration:

1. Go to: [pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/)
2. Click **"Add a new pending publisher"**
3. Fill in:
   - **PyPI Project Name:** `vectora-agent`
   - **Owner:** `brunosrz`
   - **Repository name:** `vectora`
   - **Workflow name:** `runner.yml`
   - **Environment name:** `Production`

After this setup, any push with `[deploy]` publishes automatically to PyPI without additional tokens.

> **PyPI name:** `vectora-agent` (the name `vectora` is already taken on PyPI by another project).
> The package imports normally as `import vectora` and the CLIs remain `vectora`, `vectora-mcp`.

---

## VPS Structure

The deploy copies `docker-compose.yml` to `/$VPS_DEPLOY_PATH/` and runs `docker compose up`.

Expected structure on the VPS after the first deploy:

```
/docker/vectora/          ← VPS_DEPLOY_PATH
├── docker-compose.yml    ← copied by the pipeline via SCP
└── .env                  ← created MANUALLY (never by the pipeline)
```

### Create `.env` on the VPS (once, manually)

```bash
ssh root@$VPS_HOST
cat > /docker/vectora/.env << 'EOF'
GOOGLE_API_KEY=your_key_here
COHERE_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
LOG_LEVEL=INFO
MCP_TRANSPORT=sse
MCP_PORT=8000
EOF
```

> These keys never pass through GitHub Actions — only you and the container know them.

---

## Post-Deploy Verification

```bash
# View container logs
ssh root@$VPS_HOST "docker logs vectora-vectora-1 --tail 50"

# Check running containers
ssh root@$VPS_HOST "docker compose -f /docker/vectora/docker-compose.yml ps"

# Manual health check
ssh root@$VPS_HOST "docker exec vectora-vectora-1 python -c 'import vectora; print(\"OK\")'"
```

---

## Manual Rollback

```bash
ssh root@$VPS_HOST << 'EOF'
cd /docker/vectora
docker compose down
docker pull ghcr.io/brunosrz/vectora:sha-<previous-commit>
# Edit docker-compose.yml to use the specific tag
docker compose up -d
EOF
```

To list available tags: `docker image ls ghcr.io/brunosrz/vectora`

---

## Troubleshooting

### Docker push returns 403

- Confirm `GHCR_TOKEN` is in the "Production" environment (capital P)
- The `docker-build` job must have `environment: Production`
- `GITHUB_TOKEN` **does not work** for push on personal accounts — always use `GHCR_TOKEN`

### SSH deploy fails with "Could not resolve hostname"

- Confirm `VPS_HOST` contains the full hostname: `srv1640150.hstgr.cloud`
- Must not contain `https://` or `/` — only the bare hostname

### Deploy fails with "No such file or directory"

- `VPS_DEPLOY_PATH` must be a relative path without a leading `/`. Example: `docker/vectora`
- The pipeline adds `/` automatically when creating the directory (`mkdir -p /$DEPLOY_PATH`)

### PyPI returns "user not allowed"

- Trusted Publishing has not been configured on pypi.org yet (see section above)
- Confirm the project name on PyPI is exactly `vectora-agent`

---

**Last updated:** 2026-05-20
