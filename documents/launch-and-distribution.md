# Vectora — Lançamento e Distribuição

> Como o Vectora é empacotado, entregue, atualizado e testado por usuários
> reais antes do lançamento público. Consolida o que antes eram três
> documentos separados (programa de beta, distribuição comercial, fluxo de
> atualização) num único lugar, porque as três coisas descrevem a mesma
> jornada: do build ao usuário final, e do usuário final de volta como
> feedback.

Contexto de produto (ver `documents/history.md`, seção "O Vectora hoje"):
Vectora é local-first, sem cloud obrigatória. O desktop é Electron + backend
Python (Nuitka) como uma unidade só — o frontend pode estar visível (janela)
ou oculto (headless/bandeja), mas o backend sempre roda. Comunicação
Electron↔backend é por IPC (named pipe/unix socket), nunca TCP; a única
superfície TCP é o modo servidor (web/VPS), por design. `services/` é o
Worker Cloudflare único que cobre auth/billing/license/GDPR/api-keys/issues
da company **e** a distribuição de releases do desktop (o antigo
`update-server`) — ver `services/src/updates/worker.ts`.

---

## 1. Empacotamento e arquitetura de distribuição

### Arquitetura

```
electron/ (Electron shell)
└── backend Python compilado via Nuitka (binário nativo)
    ├── FastAPI + motor de conversa nativo (backend/)
    ├── frontend/dist (build Vite, servido como StaticFiles)
    └── recursos (skills, templates, icons)
```

O cliente final recebe **um** instalador (`.msi`/`.dmg`/`.AppImage`/`.deb`/
`.rpm`). Sem `pip`, sem `npm`, sem dependências externas — alinhado ao
princípio de "artefatos distribuídos não contêm fonte" (ver `CLAUDE.md` §13):
o backend vai sempre compilado (Nuitka, binário C, não decompilável); o
frontend vai como `dist/` (JS servido ao browser embutido no Electron).

### Componentes do pipeline

| Peça                     | Papel                                                                                                                        |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Launcher (`launcher.py`) | Faz o gate de licença antes de subir o backend; delega para o processo principal                                             |
| Bundle do frontend       | Build Vite (`frontend/dist`) embutido como diretório de dados no binário Nuitka; FastAPI serve com `serve_static=True`       |
| Build Nuitka             | Compila `backend/` inteiro para binário nativo (flags documentadas no build do projeto)                                      |
| Wrapper Electron         | `electron/src/main.ts` — spawn do binário Nuitka, `BrowserWindow`, encerramento limpo do processo filho no quit, autoUpdater |
| Instaladores nativos     | `electron-builder` — Windows (NSIS/MSI), macOS (DMG notarizado), Linux (AppImage/deb/rpm)                                    |
| Licenciamento            | Validação remota + cache local (ver seção 1.2)                                                                               |

### Fluxo de release (CI)

1. Push de tag de release dispara o pipeline (Jenkins, ver `Jenkinsfile` na
   raiz do monorepo).
2. Por sistema operacional (Windows/macOS/Linux):
   1. Build do frontend (`pnpm --dir vectora/frontend build`) → `frontend/dist/`.
   2. Sync de dependências Python (`uv sync --frozen`).
   3. Build Nuitka do backend → binário nativo.
   4. Build Electron + empacotamento (`electron-builder`) → instaladores.
3. Assinatura de código:
   - **Windows**: certificado EV (Azure Trusted Signing).
   - **macOS**: Apple Developer ID + notarização.
   - **Linux**: sem assinatura.
4. Upload dos artefatos e publicação via `services/` (worker unificado) —
   substituiu o antigo fluxo de GitHub Releases privadas: os binários e
   manifestos ficam em R2, servidos pelas rotas `/updates/*` e `/download/*`
   descritas na seção 3.
5. Manifesto (`latest.yml`, no padrão `electron-updater`) é gerado no build e
   publicado junto — é o que o autoUpdater consulta para saber se há versão
   nova.

### 1.2 Licenciamento

O launcher valida o token de licença antes de subir qualquer processo do
backend:

1. Lê o token de licença do ambiente (no Electron, injetado pelo instalador
   ou por Configurações → Licença).
2. Faz uma chamada de validação contra o endpoint de licença em `services/`.
3. Cacheia o resultado localmente (`~/.vectora/license_cache.json`) — TTL
   curto em uso normal, TTL estendido em modo offline (graceful degradation
   quando não há rede).
4. Exporta o tier de licença (`plus`/`pro`) para o backend — a camada de
   storage e de cache usam isso para recusar backends Pro (Postgres/Qdrant/
   Redis) quando o tier não permite.

O endpoint de status de licença é público (sem auth) e alimenta o banner de
trial no chat: aviso a partir de 7 dias antes do vencimento, bloqueio quando
expirado.

Modos de bypass (uso interno — CI/dev — nunca em produção): variável de
ambiente que pula o gate inteiro, e variável que aponta a validação para um
endpoint mock/staging.

### Setup de desenvolvimento (sem build comercial)

Dev local não precisa do launcher nem do build Nuitka — segue o fluxo comum
descrito no `CLAUDE.md` (`uv run vectora start` + Vite dev server). O
launcher e o binário Nuitka só entram para testar o pipeline de distribuição
em si.

### Próximos passos (fora do escopo imediato)

- Portal do cliente (Stripe Customer Portal) acessível via Configurações →
  "Gerenciar assinatura", abrindo o portal externo a partir do Electron.
- Distribuição somente-leitura de um CLI Plus (sem frontend/Electron) para
  compatibilidade com early adopters que só querem a linha de comando.
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
significativa (IA+ com edição de imagem, Deep Agents 2.0, SDKs externos,
Host/Client, plugins novos, Helpdesk/Code Review como betas longos de 60+
dias). Cadência típica: 1 beta iniciando por mês, com 2–3 ciclos ativos em
paralelo.

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
> muda e aprovar antes** de qualquer atualização ser aplicada — o oposto de
> um fluxo que só mostra o changelog depois de já ter instalado e sem
> permitir reverter.

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

O wrapper Electron hoje já teria autoDownload/autoInstall automáticos e uma
tray que só oferece "aplicar" depois de já ter baixado — o design deste
fluxo inverte isso: busca o changelog antes de qualquer download, exige
aprovação explícita, faz backup, e oferece rollback real. O worker
`services/` já serve `latest.yml` e os binários com lógica de rollout/
quarantine (ver `services/src/updates/worker.ts`); o que falta é o endpoint
de changelog por versão, o script de release que popula esse changelog, e a
UI dedicada no frontend (hoje o evento de status de update chega por IPC mas
sem banner/modal).

### 3.3 Arquitetura

```
   CI (tag de release)         services/ (Worker: R2 + KV)              Desktop (Electron)
 ┌─────────────┐   release   ┌───────────────────────────┐  feed  ┌────────────────────┐
 │ build nativo│ ──────────► │ R2: binários + changelog  │ ◄───── │ electron-updater   │
 │ + changelog │             │ KV: config (rollout)      │        │ (autoDownload=OFF) │
 └─────────────┘             └───────────────────────────┘        └─────────┬──────────┘
                                                                            │ IPC
                                                                  ┌─────────▼──────────┐
                                                                  │ frontend (Electron):│
                                                                  │ banner+changelog+  │
                                                                  │ progresso+rollback │
                                                                  └────────────────────┘
```

### Sequência (caminho feliz)

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

**Rotas do worker `services/` relevantes a este fluxo** (as três primeiras
já existem em `services/src/updates/worker.ts`; a quarta é a peça que falta):

```
GET  /updates/:channel/:os/:arch/latest.yml       — manifesto electron-updater
GET  /updates/:channel/:os/:arch/:version/:file   — binário/blockmap
POST /telemetry/update-result                     — estados de update
GET  /changelog/:channel/:version?from=<atual>    — notas acumuladas (a implementar)
```

`GET /changelog` retornaria um JSON com a versão alvo, a versão de origem,
uma flag `mandatory` para updates de segurança (que ainda exigem clique, mas
deixam isso claro na UI), e uma lista de entradas por versão com data e
notas em markdown — renderizadas no modal de changelog.

Configuração de rollout (em KV) mantém, por canal, a versão atual, o
percentual de rollout, a versão estável anterior (`previous_stable`, usada
pelo rollback), e uma lista de versões colocadas em quarentena.

**Canais IPC** entre main e renderer cobrem: disponibilidade de update (com
changelog embutido), aprovação de download, progresso, download concluído,
comando de instalar (com flag de backup), dispensar, comando de rollback
para uma versão específica, erro, e listagem de backups disponíveis.

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

**Quarantine automático (nível de frota, complementar ao rollback manual):**
se o volume de crash-reports de uma versão específica passar de um limiar
em uma janela curta (via telemetria já existente), o worker move essa
versão para a lista de quarentena e volta a servir a `previous_stable` para
novos checks — isso não desfaz instalações já feitas, mas contém o alcance
do problema para quem ainda não atualizou.

### 3.6 Peças a construir, por camada

- **Worker (`services/src/updates/`)** — endpoint de changelog; script de
  release que sobe binários + manifestos para R2, gera o changelog por
  versão a partir de um `CHANGELOG.md` central, e atualiza a config de
  rollout no KV.
- **Electron main** — trocar para download/instalação manuais; buscar e
  repassar changelog no evento de update disponível; handlers IPC de
  aprovar/instalar/rollback; rotina de backup; suporte a downgrade.
- **Electron preload** — expor os novos canais IPC no bridge de contexto.
- **Frontend** — componentes de banner de update, modal de changelog,
  indicador de progresso, e seção "Atualizações" nas configurações
  (rollback e lista de backups).
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
