# Vectora — build targets
#
# Pré-requisitos:
#   gen-proto: buf CLI (https://buf.build/docs/installation)
#   build-chat: Node.js + pnpm (https://pnpm.io/installation)
#
# Uso:
#   make gen-proto    # gera stubs Python + TypeScript a partir do .proto
#   make build-chat   # build Next.js → vectora/chat_static/ (bundled no wheel)
#   make dev          # atalho: inicia o servidor de dev (backend + frontend)

.PHONY: gen-proto build-chat dev clean-static

# ── Proto codegen (buf) ───────────────────────────────────────────────────────
# Gera:
#   vectora/api/gen/           ← stubs Python (grpcio/protobuf)
#   chat/frontend/lib/gen/     ← stubs TypeScript (ConnectRPC ES)
gen-proto:
	@echo "→ Gerando stubs a partir do proto..."
	cd vectora/api/protos && buf generate
	@echo "✓ Stubs Python em vectora/api/gen/"
	@echo "✓ Clients TypeScript em chat/frontend/lib/gen/"

# ── Frontend build (Next.js static export) ───────────────────────────────────
# Compila o Next.js com `output: export` e copia o resultado para
# vectora/chat_static/ — incluído no wheel pelo hatchling.
build-chat:
	@echo "→ Instalando dependências do frontend..."
	cd chat/frontend && pnpm install --frozen-lockfile
	@echo "→ Compilando Next.js (static export)..."
	cd chat/frontend && pnpm build
	@echo "→ Copiando para vectora/chat_static/..."
	$(RM) -r vectora/chat_static
	mkdir -p vectora/chat_static
	cp -r chat/frontend/out/. vectora/chat_static/
	@echo "✓ Frontend compilado em vectora/chat_static/"

# ── Limpar static build ───────────────────────────────────────────────────────
clean-static:
	$(RM) -r vectora/chat_static
	@echo "✓ vectora/chat_static/ removido"

# ── Dev: backend + frontend ───────────────────────────────────────────────────
# Abre dois processos: FastAPI em 8080, Next.js dev em 3000.
# Requer: uv, pnpm
dev:
	@echo "Iniciando backend (porta 8080) e frontend (porta 3000)..."
	@echo "Ctrl+C encerra ambos."
	@(uv run vectora server headless --port 8080 & \
	  cd chat/frontend && pnpm dev; \
	  kill %1 2>/dev/null)
