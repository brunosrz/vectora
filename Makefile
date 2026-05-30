# Vectora — build targets
#
# Pré-requisitos:
#   gen-proto:  buf CLI  (https://buf.build/docs/installation)
#   build-chat: Node.js + pnpm  (https://pnpm.io/installation)
#
# Uso:
#   make gen-proto    # gera stubs Python + TypeScript a partir do .proto
#   make dev          # atalho: inicia backend (8080) + frontend dev (3000)
#   make clean-static # remove vectora/chat_static/
#
# SHELL portátil: no Windows usa o short-name 8.3 (PROGRA~1) para evitar o
# espaço de "Program Files" — `make` não aceita aspas no valor de SHELL, e
# espaços não-escapados quebram o exec. Em Linux/macOS (incluindo o GHA
# Ubuntu) usa /bin/bash diretamente.
ifeq ($(OS),Windows_NT)
  SHELL := C:/PROGRA~1/Git/usr/bin/bash.exe
  BASH  := C:/PROGRA~1/Git/usr/bin/bash.exe -l
else
  SHELL := /bin/bash
  BASH  := /bin/bash -l
endif

.PHONY: gen-proto dev clean-static

# ── Proto codegen (buf) ───────────────────────────────────────────────────────
# Gera:
#   vectora/api/gen/      ← stubs Python (grpcio/protobuf)
#   chat/lib/gen/         ← stubs TypeScript (ConnectRPC ES)
gen-proto:
	@echo ">> Gerando stubs a partir do proto..."
	cd vectora/api/protos && buf generate
	@echo "OK Stubs Python em vectora/api/gen/"
	@echo "OK Clients TypeScript em chat/lib/gen/"

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
