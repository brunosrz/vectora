# Vectora — build targets
#
# Pré-requisitos:
#   gen-proto:  buf CLI  (https://buf.build/docs/installation)
#   build-chat: Node.js + pnpm  (https://pnpm.io/installation)
#
# Uso:
#   make gen-proto    # gera stubs Python + TypeScript a partir do .proto
#   make build-chat   # build Next.js >> vectora/chat_static/ (standalone)
#   make dev          # atalho: inicia backend (8080) + frontend dev (3000)
#   make clean-static # remove vectora/chat_static/
#
SHELL = "C:/Program Files/Git/usr/bin/bash.exe"
BASH  = "C:/Program Files/Git/usr/bin/bash.exe" -l

.PHONY: gen-proto build-chat dev clean-static

# ── Proto codegen (buf) ───────────────────────────────────────────────────────
# Gera:
#   vectora/api/gen/      ← stubs Python (grpcio/protobuf)
#   chat/lib/gen/         ← stubs TypeScript (ConnectRPC ES)
gen-proto:
	@echo ">> Gerando stubs a partir do proto..."
	cd vectora/api/protos && buf generate
	@echo "OK Stubs Python em vectora/api/gen/"
	@echo "OK Clients TypeScript em chat/lib/gen/"

# ── Frontend build (Next.js standalone) ──────────────────────────────────────
# Compila o Next.js com `output: standalone` e copia o resultado para
# vectora/chat_static/ junto com os assets estáticos e pasta public/.
#
# Layout resultante em vectora/chat_static/:
#   server.js          ← entry point Node.js
#   .next/server/      ← bundle server-side
#   .next/static/      ← assets estáticos (CSS/JS/fonts)
#   node_modules/      ← deps mínimas (copiadas pelo Next.js)
#   public/            ← arquivos públicos (ícones, pdf.worker, etc.)
#
# Inicie com:  PORT=8080 VECTORA_API_URL=http://127.0.0.1:8081 node vectora/chat_static/server.js
# Ou use:      uv run vectora server chat   (gerencia os dois processos automaticamente)
build-chat:
	@echo ">> Instalando dependencias do frontend..."
	cd chat && pnpm install --frozen-lockfile
	@echo ">> Compilando Next.js..."
	cd chat && pnpm build
	@echo "OK Frontend compilado em chat/.next/"
	@echo "  Inicie com: uv run vectora server chat"

# ── Limpar static build ───────────────────────────────────────────────────────
clean-static:
	$(BASH) -c "rm -rf vectora/chat_static"
	@echo "OK vectora/chat_static/ removido"

# ── Dev: backend headless + frontend dev ─────────────────────────────────────
# Dois processos em paralelo: FastAPI headless em 8080, Next.js dev em 3000.
# O frontend se conecta ao backend via VECTORA_API_URL=http://localhost:8080.
# Requer: uv, pnpm
dev:
	@echo ">> Backend headless (porta 8080) + frontend dev (porta 3000)"
	@echo ">> Ctrl+C encerra ambos os processos."
	@trap 'kill 0' INT TERM; \
	  uv run vectora server headless --port 8080 & \
	  ( cd chat && pnpm dev ) & \
	  wait
