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
# Windows: SHELL = caminho completo do Git Bash (rm -rf, cp -r, mkdir -p, kill)
SHELL = "C:/Program Files/Git/usr/bin/bash.exe"

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
	@echo ">> Compilando Next.js (standalone)..."
	cd chat && pnpm build
	@echo ">> Copiando para vectora/chat_static/..."
	rm -rf vectora/chat_static
	mkdir -p vectora/chat_static
	cp -r chat/.next/standalone/. vectora/chat_static/
	mkdir -p vectora/chat_static/.next/static
	cp -r chat/.next/static/. vectora/chat_static/.next/static/
	mkdir -p vectora/chat_static/public
	cp -r chat/public/. vectora/chat_static/public/
	@echo ">> Garantindo @swc/helpers no standalone (Windows/pnpm)..."
	rm -rf vectora/chat_static/node_modules/@swc/helpers
	mkdir -p vectora/chat_static/node_modules/@swc
	cp -rL chat/node_modules/.pnpm/@swc+helpers@*/node_modules/@swc/helpers vectora/chat_static/node_modules/@swc/helpers
	@echo "OK Frontend compilado em vectora/chat_static/"
	@echo "  Inicie com: uv run vectora server chat"

# ── Limpar static build ───────────────────────────────────────────────────────
clean-static:
	rm -rf vectora/chat_static
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
