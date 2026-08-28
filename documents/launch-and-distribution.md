# Vectora — Lançamento e Distribuição

> Como o Vectora é empacotado, entregue, atualizado e testado por usuários
> reais antes do lançamento público. Cobre três frentes que descrevem a
> mesma jornada — do build ao usuário final, e do usuário final de volta
> como feedback: empacotamento/CI de release, programa de beta e fluxo de
> atualização.

Contexto de produto (ver `documents/history.md`, seção "O Vectora hoje"):
Vectora é local-first, sem cloud obrigatória. O desktop é Electron + backend
Python (compilado) como uma unidade só — o frontend pode estar visível
(janela) ou oculto (headless/bandeja), mas o backend sempre roda. Comunicação
Electron↔backend é por IPC (unix socket em Linux/macOS, named pipe com
fallback TCP loopback no Windows — ver §1.1), nunca uma porta TCP exposta
externamente; a única superfície TCP real é o modo servidor (web/VPS), por
design. `services/` é o Worker Cloudflare único que cobre auth/billing/
license/GDPR/api-keys/issues da company **e** a distribuição de releases do
desktop — ver `services/src/updates/worker.ts` e `services/src/license/routes.ts`.

---

## 1. Empacotamento e arquitetura de distribuição

### 1.1 Arquitetura

O binário do backend **não** é gerado por Nuitka sozinho. O pipeline real
(`build-hybrid.py`, raiz do monorepo) é híbrido, em duas fases:

```
Fase 1 — Nuitka --mode=package
  vectora/backend/  ──────────────────►  backend.pyd (Windows) / backend.so (Linux/macOS)
                                          (só o pacote backend vira código C — não o app inteiro)

Fase 2 — PyInstaller --onedir
  launcher.py + backend.pyd/.so + libs Python + frontend/dist + nats-server
                                          ──────────────────►  dist/vectora/  (pasta "vectora-core")
```

`launcher.py` é só o ponto de entrada empacotado (`sys.path` aponta pro
diretório do binário, depois `from backend.main import run`) — quem valida
licença e sobe o FastAPI é o próprio `backend/main.py`/`backend/api/server.py`,
não o launcher (ver §1.2).

**Por que `--onedir` e não `--onefile`**: os arquivos ficam soltos, sem
compressão — entre versões, DLLs/libs que não mudaram permanecem
byte-idênticas, então o blockmap do `electron-updater` baixa só o delta real
(poucos MB), não o pacote inteiro. Isso não muda a garantia de "artefato
distribuído não contém fonte" (regra 13 do `CLAUDE.md`): `backend.pyd`/`.so`
continua sendo extensão C compilada pelo Nuitka, as demais libs são
bytecode `.pyc` de dependências de terceiros, nunca o `.py` do backend.
`build-hybrid.py` inclusive falha o build (`_assert_no_secrets_inside_backend`)
se encontrar `.env`/`.pem`/chaves dentro de `backend/` — o Nuitka embutiria
esse arquivo permanentemente no binário entregue.

O cliente final recebe **um** instalador (`.msi`/`.dmg`/`.AppImage`/`.deb`/
`.rpm`) via `electron-builder`, que empacota o Electron shell + a pasta
`vectora-core` como `extraResources`. Sem `pip`, sem `npm`, sem dependências
externas.

### 1.2 Componentes do pipeline

| Peça                      | Papel                                                                                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `launcher.py`             | Entry-point PyInstaller — só ajusta `sys.path` e chama `backend.main.run()`; não faz gate de licença                                                   |
| Nuitka (`--mode=package`) | Compila só `backend/` para `backend.pyd`/`.so` (C, `--report=nuitka-report.xml`)                                                                       |
| PyInstaller (`--onedir`)  | Empacota launcher + `backend.pyd`/`.so` + libs + `frontend/dist` (como `chat_static`) + `nats-server` em `dist/vectora/`                               |
| `scons nats`              | Baixa o binário `nats-server` da plataforma pra `vectora/resources/` antes do build — sem ele o build falha                                            |
| Wrapper Electron          | `frontend/electron/src/main.ts` — spawna a pasta `vectora-core` como sidecar (`backend-lifecycle.ts`), IPC, tray, deep-link `vectora://`, auto-updater |
| Instaladores nativos      | `electron-builder` — Windows (NSIS/MSI), macOS (DMG notarizado), Linux (AppImage/deb/rpm)                                                              |
| Licenciamento             | Loop periódico dentro do FastAPI (`backend/services/license.py`) — ver §1.4                                                                            |

### 1.3 Fluxo de release (CI real — GitHub Actions)

O `Jenkinsfile` na raiz cobre CI contínuo (`scons lint && scons tests` em
todo push, infra própria com agente uv/pnpm/scons). `.github/workflows/
vectora.yml` roda em paralelo: lint/security/frontend/build/testes sempre
— em todo PR contra `master` e em todo push em `master` — sem gate manual.
Só o fluxo de release de verdade (build dos instaladores por SO +
publicação no canal de update) continua condicionado, agora numa tag `v*`
real ou `workflow_dispatch` manual, não mais `[up-release]`. A tag é criada
por `release-please.yml` quando o usuário mescla o PR de release acumulado
que ele mantém automaticamente (changelog + versão calculados a partir dos
títulos de PR em Conventional Commits) — nunca a cada push comum.

Jobs (em ordem de dependência):

1. `lint` (ruff + ruff format + ty), `security` (bandit + pip-audit) e
   `frontend` (oxlint + tsc + vitest) — em paralelo.
2. `build_verification` — `python -m compileall backend` + `pnpm build` do
   frontend, gate antes de gastar minutos caros de matriz.
3. `test-unit` (pytest unit + stress) e `test-external` (integration + e2e)
   — em paralelo, ambos dependem de `build_verification`.
4. `release-native` — matriz `ubuntu-latest`/`macos-26`/`windows-latest`:
   build do frontend Vite, fetch do `nats-server` (`scons nats`), build
   híbrido (`python build-hybrid.py --jobs 4`), smoke test
   (`./dist/vectora/vectora --version` com `VECTORA_LICENSE_BYPASS=1`),
   assinatura Windows (certificado via `CSC_LINK`/`CSC_KEY_PASSWORD`,
   secrets `WIN_CERTIFICATE_BASE64`/`WIN_CERTIFICATE_PASSWORD`), build do
   shell Electron + `electron-builder --publish always` (assina/notariza
   macOS via `APPLE_ID`/`APPLE_APP_SPECIFIC_PASSWORD`/`APPLE_TEAM_ID`;
   Linux sem assinatura) e upload dos instaladores como artifact.
5. `publish-update-channel` — roda uma única vez após a matriz inteira
   terminar (evita race condition de read-modify-write concorrente na
   mesma chave `config` do KV): lê a versão de `pyproject.toml`, baixa
   todos os instaladores da matriz, e roda `pnpm run release` dentro de
   `services/` (`services/scripts/release.ts`), que sobe os binários pro
   R2 e atualiza `config` no KV (rollout, `previous_stable`, histórico).

Nenhum passo publica GitHub Release "privada" nem depende de um `update-server`
separado — R2 + KV do worker `services` são a única fonte servida ao
`electron-updater` e à página de downloads.

### 1.4 Licenciamento

A validação **não** bloqueia o boot do backend nem é feita pelo `launcher.py`
— ela roda como task assíncrona de fundo dentro do próprio FastAPI
(`_license_revalidation_loop` em `backend/api/server.py`, criada no startup,
cancelada no shutdown) e como revalidação síncrona pontual quando o usuário
salva um token novo. Modelo real (`backend/services/license.py`):

1. Lê o token: `VECTORA_TOKEN` (env) tem prioridade; senão, `[license].token`
   em `~/.vectora/config.toml` (setado pela UI/setup wizard, espelhado pra
   `os.environ` uma vez lido).
2. **Sem token configurado → tier `free` direto, sem erro** — uso local solo
   sem conta é o caminho normal, não um bloqueio.
3. Com token: `POST` em `VECTORA_LICENSE_URL` (default
   `https://services.vectora.company/license/validate`, ver
   `services/src/license/routes.ts::/validate`) com `{token, vectora_version}`.
4. Resposta cacheada em `~/.vectora/license_cache.json` — TTL 6h online; em
   falha de rede, cai pro cache até 48h (offline graceful). Cache expirado
   sem resposta válida → `LicenseError` (token existe mas não dá pra
   confirmar), exposta via `GET /license/status`, que alimenta o banner de
   trial/bloqueio no chat.
5. `LicenseError` só ocorre com token presente e inválido/expirado/revogado
   (HTTP 401/403 ou `valid: false` no corpo), ou sem cache utilizável.
6. `get_effective_storage_mode()` — a camada de storage só libera backends
   Pro (Postgres/Qdrant/Redis) quando `storage_mode="complete"` **e** o
   cache indica `tier="pro"`; caso contrário faz fallback silencioso pra
   `lite` (SQLite + LanceDB).

`VECTORA_LICENSE_BYPASS=1` pula a validação inteira (retorna tier `pro`
sintético por 365 dias) — uso interno em CI/smoke test, nunca em produção.

### 1.5 Setup de desenvolvimento (sem build comercial)

Dev local não precisa do `launcher.py` nem do build híbrido — segue o fluxo
comum descrito no `CLAUDE.md` (`uv run vectora start` + Vite dev server). O
launcher e o pipeline Nuitka+PyInstaller só entram para testar a distribuição
em si (`python build-hybrid.py` na raiz do monorepo).

### 1.6 Próximos passos (fora do escopo imediato)

- Portal do cliente (Stripe/Asaas Customer Portal, já existe como rota em
  `services/src/license/routes.ts::/portal`) acessível via
  Configurações → "Gerenciar assinatura" no Electron.
- Distribuição somente-leitura de um CLI Plus (sem frontend/Electron) para
  early adopters que só querem a linha de comando.
- Canal de update dedicado para builds de ACP server em beta.

---

## 2. Programa de beta com feedback recompensado

> Programa formal de teste fechado de features pré-lançamento. Recompensa
> feedback útil com tempo extra de assinatura ou acesso vitalício.

**Por que existir:** lançar features grandes sem usuários reais testando é
apostar no escuro. O programa de beta entrega três coisas ao mesmo tempo:
produto refinado pela realidade, case studies/testimonials para o
lançamento público, e uma base de evangelistas orgânicos.

**Premissa cardinal:** testes sem feedback são inúteis. Toda recompensa
exige feedback estruturado validado humanamente — sem isso é só um trial
estendido, não um programa de beta.

### 2.1 Três tiers de participação

#### Tier 1 — Beta Tester (entrada)

- Recebe acesso a uma feature em beta fechado, usa por pelo menos 14 dias,
  responde survey estruturado ao final (10–15 perguntas, ~20 min).
- **Recompensa:** +3 meses do plano atual após validação do feedback, mais
  acesso público à feature 30 dias antes do lançamento geral.
- **Elegibilidade:** cliente Plus ou Pro ativo há ≥ 30 dias; inscrição via
  formulário curto (cargo, stack, contexto); aceite de NDA leve.
- **Capacidade por feature:** 50–100 slots.

#### Tier 2 — Power Tester (intermediário)

- Tudo do Beta Tester, mais: abre 3+ issues qualificadas (repro steps,
  contexto, severidade), sugere 1 melhoria com proposta concreta, participa
  de 1 entrevista de 30 min ao final do ciclo.
- **Recompensa:** +12 meses do plano atual após validação; selo público
  "Vectora Power Tester" (reconhecimento em release notes); acesso
  antecipado automático a todas as próximas betas.
- **Elegibilidade:** foi Beta Tester em pelo menos 1 ciclo anterior, ou
  cliente Pro ativo há ≥ 90 dias com uso significativo (threads + tool
  calls).
- **Capacidade por feature:** 10–20 slots.

#### Tier 3 — Founding User (vitalício)

- Tudo do Power Tester, mais: entrevistas mensais com o fundador (1h),
  case study público com nome e empresa, testemunho em vídeo (5–10 min),
  citação em materiais comerciais, participação em **todas** as betas (não
  só as de interesse).
- **Recompensa:** acesso vitalício ao plano Pro (ou superior); selo
  "Founding User" com página dedicada no site; convite para canal privado
  direto com o fundador; voto qualificado em decisões de roadmap; brinde
  físico.
- **Elegibilidade:** foi Power Tester em pelo menos 2 ciclos, ou cliente
  Enterprise/OEM com uso comprovado de ≥ 6 meses, ou convite direto do
  fundador. Exige NDA mais rigoroso (sem discutir publicamente features
  pré-anúncio).
- **Capacidade global:** máximo 50 founding users (escassez deliberada, para
  manter exclusividade e qualidade do feedback). Perda de status por
  inatividade (3 meses sem entrevista) não revoga o acesso vitalício já
  concedido — só libera o slot.

### 2.2 Anti-gaming — evitando feedback de baixa qualidade

**Survey estruturado, não livre.** Respostas vazias ou superficiais
("ok", "bom", "gostei") são rejeitadas — sem recompensa. O survey cobre
fluxo executado, pontos de confusão, features esperadas e ausentes,
features difíceis de descobrir, recomendação (sim/não + motivo), gatilhos
de cancelamento, comparação com concorrentes, tempo economizado estimado,
bugs encontrados, sugestão livre.

**Validação humana.** Cada feedback passa por revisão do fundador (ou
designado) antes de a recompensa ser creditada — 7–14 dias após o fim do
ciclo. Critério de aprovação: respostas demonstram uso real, pelo menos 3
das 10 respostas são acionáveis (viram issue ou ajustam roadmap), sem
indício de bot/múltiplas contas.

**Anti-duplicação.** 1 usuário = 1 inscrição por feature; múltiplas contas
do mesmo CPF/CNPJ contam como uma; IP/email duplicado dispara revisão
manual.

**Issues qualificadas (Power Tester)** precisam de título descritivo, steps
to reproduce, comportamento esperado vs. observado, severidade
auto-classificada, anexo quando aplicável. Issues fora do template são
devolvidas antes de contarem.

### 2.3 Operacionalização

Ciclo típico de uma beta (do anúncio ao lançamento público da feature):
anúncio público (T-30d) → abertura de inscrição (T-21d) → fechamento e
seleção (T-14d) → onboarding (T-7d) → início do beta (T+0) → lembrete e
survey intermediário opcional (T+14d) → fim do beta com survey obrigatório
(T+30d) → validação dos feedbacks (T+45d) → recompensas creditadas e
relatório agregado (T+60d) → lançamento público da feature (T+90d).

Onde os betas vivem: página pública listando betas abertas/fechadas/
próximas; inscrição via formulário simples sem login obrigatório;
comunicação privada em canal dedicado por feature; suporte direto via office
hours semanais; issues em repositório privado com acesso restrito aos
participantes.

Cada feature em beta tem um doc interno cobrindo objetivos, escopo (dentro/
fora, limitações conhecidas que não devem ser reportadas como bug),
onboarding, link do survey e prazo, e resultados preenchidos pós-beta
(participantes, feedbacks válidos, issues criadas/resolvidas, mudanças
significativas pré-lançamento).

### 2.4 Calendário pré-lançamento (proposta)

Antes do lançamento público, a expectativa é rodar betas escalonadas para as
features maiores (storage backends Pro, chat web multi-usuário, MCP Library

- Native Tools, IA+ com TTS/STT/geração de imagem, VSIX), cada uma com 1 mês
  de beta fechado e capacidade crescente de slots (30 a 100), culminando no
  lançamento público geral. Volume total esperado pré-lançamento: ~300–400
  testers únicos (com sobreposição entre ciclos); ROI esperado de ~30 Founding
  Users + ~50 Power Testers + ~200 Beta Testers no momento do lançamento.

### 2.5 Pós-lançamento — programa contínuo

Depois do lançamento público, o programa continua para toda feature nova
significativa (IA+ com edição de imagem, SDK de extensões, Host/Client,
plugins novos, Helpdesk/Code Review como betas longos de 60+ dias). Cadência
típica: 1 beta iniciando por mês, com 2–3 ciclos ativos em paralelo.

### 2.6 Aspectos legais

- **NDA leve (Beta Tester):** sem screenshots/vídeos públicos de features
  não anunciadas; pode dizer publicamente que está em beta de algo, sem
  detalhar; aceita ser contatado para o survey final; aceita que o feedback
  seja usado livremente pelo Vectora. Aceite via checkbox na inscrição.
- **NDA rigoroso (Founding User):** proíbe discussão pública de features
  pré-anúncio e compartilhamento de credenciais/builds com terceiros,
  enquanto o status estiver ativo. Assinatura eletrônica.
- **Propriedade do feedback:** pertence ao Vectora; pode ser implementado
  livremente, sem compensação além da recompensa do tier; nome/empresa só é
  citado com opt-in explícito.
- **Cancelamento de assinatura:** meses extras creditados permanecem
  disponíveis mesmo após cancelamento (validade de 24 meses). Acesso
  vitalício de Founding User se transfere contratualmente em caso de venda
  ou descontinuação da empresa.

### 2.7 Métricas de saúde do programa

Acompanhar mensalmente: proporção inscritos/slots (meta ≥ 3×, indica demanda
e permite seleção qualitativa), taxa de conclusão do survey (≥ 70%),
proporção de feedbacks aprovados (≥ 80%), bugs reportados que viram
resolvidos pré-lançamento (≥ 60%), Founding Users ativos (≥ 40 de 50), NPS
médio dos testers (≥ 50). Métricas abaixo da meta disparam revisão do
formato do programa.

### 2.8 Erros a evitar

1. **Beta perpétuo** — feature em beta por mais de 6 meses sem decisão de
   lançamento ou kill é sinal de produto sem direção. Todo beta tem prazo
   fechado.
2. **Feedback sem ação visível** — issue qualificada sem resposta em até 7
   dias mata engajamento.
3. **Recompensa desalinhada** — sempre no plano atual do tester ou superior,
   nunca um plano que ele já tem.
4. **Selecionar amigos** — critério de seleção objetivo e transparente
   (uso real, cargo, contexto).
5. **Burnout do fundador** — entrevistas mensais escalam mal além de ~50
   Founding Users; quando o programa crescer, delegar para um community
   manager part-time.
6. **NDA pesado demais** — vira atrito. Reservar o NDA rigoroso só para
   Founding User.
7. **Misturar beta público e fechado** — confunde marketing; beta fechado
   fica privado até o anúncio público de "feature lançada".

---

## 3. Fluxo de atualização (changelog, aprovação manual, backup e rollback)

> Proposta de design ainda não implementada. O usuário precisa **ver o que
> muda e aprovar antes** de qualquer atualização ser aplicada — o oposto do
> fluxo de hoje, que baixa e agenda a instalação sem intervenção do usuário.

### 3.1 Princípios inegociáveis

1. **Nada automático** — nenhum download ou instalação sem clique
   explícito do usuário.
2. **Changelog primeiro** — as notas da versão nova aparecem antes do
   download; o usuário aprova as mudanças conscientemente.
3. **Backup antes de instalar** — snapshot dos dados do usuário antes de
   qualquer atualização ser aplicada.
4. **Rollback real** — voltar para a versão anterior e restaurar o backup
   correspondente, não só reinstalar um binário antigo.

### 3.2 Estado atual vs. gap

Hoje (`frontend/electron/src/main.ts::setupAutoUpdater`) o
`electron-updater` já roda com `autoDownload = true` e
`autoInstallOnAppQuit = true`: uma checagem dispara 30s após o boot e depois
a cada 6h (gated por `autoUpdateEnabled` em `GET /settings/prefs`,
fail-open — falha de leitura nunca desliga o update), baixa sozinho ao
detectar versão nova, e instala no próximo quit do app (ou via "Aplicar
atualização e reiniciar" no menu da tray, quando `updateReady`). O usuário só
vê um evento de status (`vectora:update-status`) — sem banner de changelog,
sem aprovação, sem backup. O design deste fluxo inverte isso: busca o
changelog antes de qualquer download, exige aprovação explícita, faz backup,
e oferece rollback real.

O worker `services` já serve `latest.yml` e os binários com lógica de
rollout/quarentena (`services/src/updates/worker.ts`); o que falta é o
endpoint de changelog por versão, o script de release que popula esse
changelog, e a UI dedicada no frontend.

### 3.3 Arquitetura

```
   CI (tag de release)         services/ (Worker: R2 + D1/KV)            Desktop (Electron)
 ┌─────────────┐   release   ┌───────────────────────────┐  feed  ┌────────────────────┐
 │ build híbrido│ ──────────► │ R2: binários + changelog  │ ◄───── │ electron-updater   │
 │ + changelog  │             │ KV: config (rollout)      │        │ (autoDownload=OFF) │
 └─────────────┘             └───────────────────────────┘        └─────────┬──────────┘
                                                                            │ IPC
                                                                  ┌─────────▼──────────┐
                                                                  │ frontend (Electron):│
                                                                  │ banner+changelog+  │
                                                                  │ progresso+rollback │
                                                                  └────────────────────┘
```

### Sequência (caminho feliz, proposto)

1. App liga; após um curto atraso, verifica atualizações sem baixar nada.
2. Ao detectar versão nova, o processo main busca o changelog
   versão-atual→versão-nova no worker.
3. Main envia ao renderer um evento com origem, destino e notas em
   markdown.
4. Renderer mostra um banner discreto: "Atualização disponível — Ver
   novidades".
5. Usuário abre o modal e lê o changelog renderizado.
6. Usuário clica "Aprovar e baixar" → main inicia o download.
7. Download em progresso → barra de progresso no renderer.
8. Download concluído → renderer oferece "Instalar agora (faz backup)" ou
   "Depois".
9. Usuário confirma → main faz backup dos dados do usuário → aplica a
   atualização e reinicia.
10. App volta na versão nova; telemetria registra conclusão.

Em nenhum ponto antes do passo 6 algo é baixado; antes do passo 9, nada é
instalado.

### 3.4 Contratos

**Rotas do worker `services` relevantes a este fluxo** (as cinco primeiras
já existem em `services/src/updates/worker.ts`; a sexta é a peça que falta):

```
GET  /updates/:channel/:os/:arch/latest.yml       — manifesto electron-updater (resolve rollout/quarentena)
GET  /updates/:channel/:os/:arch/:version/:file   — binário/blockmap
GET  /download/:channel/:target                   — primeira instalação, sem token, ignora rollout
GET  /version/:channel                             — versão estável atual (site, Hero/Downloads)
POST /telemetry/update-result                      — estados de update, via fila (`vectora-jobs`)
GET  /changelog/:channel/:version?from=<atual>     — notas acumuladas (a implementar)
```

`GET /changelog` retornaria um JSON com a versão alvo, a versão de origem,
uma flag `mandatory` para updates de segurança (que ainda exigem clique, mas
deixam isso claro na UI), e uma lista de entradas por versão com data e
notas em markdown — renderizadas no modal de changelog.

Configuração de rollout (chave `config` no KV, `RuntimeConfig` em
`worker.ts`) mantém, por canal, `version`, `rollout_percent`,
`previous_stable` (versão pra fallback de quarentena e alvo do rollback),
`history` (versões retidas em R2) e `uploads` (chaves R2 por
`<channel>/<version>`, usado por `scripts/release.ts` pra podar sem listar
o bucket inteiro). `rolloutBucket(token)` faz hash determinístico do token
pra bucket `[0..99]`, decidindo se o client recebe a versão nova ou
`previous_stable`.

**Canais IPC** entre main e renderer cobrem hoje: `vectora:update-status`
(estado do autoUpdater), `vectora:check-for-update` (checagem manual),
`vectora:quit-and-install`. O fluxo proposto adiciona: disponibilidade de
update com changelog embutido, aprovação de download, comando de instalar
(com flag de backup), comando de rollback para uma versão específica, e
listagem de backups disponíveis.

### 3.5 Backup e rollback

**Backup (antes de instalar):** zipar o diretório de dados do usuário
(`~/.vectora`, equivalente por SO) para um arquivo com timestamp antes de
cada instalação. Inclui configuração, banco SQLite e settings; exclui
caches. Retenção: manter os últimos 5 backups, descartando os mais antigos.

**Rollback (voltar versão):** como o `electron-updater` não faz downgrade
nativamente, o fluxo proposto é: habilitar downgrade explicitamente, apontar
o feed para o manifesto da versão anterior (o worker mantém os binários
antigos em R2 via `previous_stable`), baixar e aplicar essa versão, e ao
reiniciar restaurar o backup de dados correspondente. A UI de rollback (em
Configurações → Atualizações) lista versões instaladas recentemente e
backups disponíveis, oferecendo "Reverter para vX".

**Quarantine automático (nível de frota, já implementado, complementar ao
rollback manual):** `processUpdateTelemetry` (`services/src/updates/
worker.ts`) conta falhas por versão numa chave KV com TTL de 1h; 3 ou mais
falhas na mesma versão dentro dessa janela movem a versão pra lista de
quarentena, e `latest.yml`/`/download` passam a servir `previous_stable`
para novos checks. Isso não desfaz instalações já feitas, mas contém o
alcance do problema para quem ainda não atualizou.

### 3.6 Peças a construir, por camada

- **Worker (`services/src/updates/`)** — endpoint de changelog; script de
  release que gera o changelog por versão a partir de um `CHANGELOG.md`
  central (o script atual, `services/scripts/release.ts`, já sobe binários +
  manifestos pro R2 e atualiza a config de rollout no KV).
- **Electron main** — trocar `autoDownload`/`autoInstallOnAppQuit` para
  manuais; buscar e repassar changelog no evento de update disponível;
  handlers IPC de aprovar/instalar/rollback; rotina de backup; suporte a
  downgrade.
- **Electron preload** — expor os novos canais IPC no bridge de contexto
  (`preload.ts`).
- **Frontend** — componentes de banner de update, modal de changelog,
  indicador de progresso, e seção "Atualizações" nas configurações
  (rollback e lista de backups) — hoje só existe `update-banner.tsx`
  consumindo o evento de status cru.
- **`CHANGELOG.md`** — fonte única das notas por versão (formato Keep a
  Changelog), consumido pelo script de release.

### 3.7 Plano de implementação (fases)

1. Worker + script de release + config de rollout — feed de changelog
   funcionando.
2. Electron main — fluxo manual, changelog antes do download, backup,
   instalação.
3. Preload + UI do frontend — banner, modal de changelog, progresso,
   instalar.
4. Rollback — downgrade, restauração de backup, UI de versões/backups.
5. Telemetria e testes cobrindo os estados do fluxo (changelog visto,
   aprovado, revertido).

### 3.8 Decisões em aberto

1. Fonte do changelog: `CHANGELOG.md` no repo com extração por versão
   (recomendado), ou notas de uma release do GitHub?
2. Rollback restaura os dados automaticamente, ou reinstala o binário
   antigo e pergunta antes de restaurar o backup? (recomendado: perguntar)
3. Escopo do backup: só config + banco (`~/.vectora`), ou workspaces
   também?
4. Canais expostos ao usuário: só o canal estável, ou também um canal beta
   opt-in na UI de configurações?
