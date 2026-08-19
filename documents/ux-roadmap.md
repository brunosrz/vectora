# Vectora — Roadmap de Experiência do Usuário (UX)

> Documento vivo. Reescrito a partir de auditoria do código real
> (frontend `vectora/frontend/`, backend `vectora/backend/`) — não é uma
> lista de intenções, é um retrato do que existe hoje e do que falta.
> Cada item da seção "Implementado" foi confirmado lendo o componente,
> hook, store ou endpoint citado. Itens da seção "Pendente" foram
> verificados como ausentes no momento da auditoria.
>
> Foco: tudo que impacta como o usuário **percebe, confia e usa** o
> Vectora — estado, dados, feedback, resiliência, teclado, auth,
> streaming, acessibilidade e performance percebida, não só "UI bonita".

---

## 1. Implementado

O frontend já resolveu a maior parte dos buracos de UX estruturais que
motivaram este documento originalmente. Lista por área, com os
arquivos que sustentam cada item.

### 1.1 Estado, cache e sincronização

- **Skeleton em vez de flash de conteúdo vazio**: `use-hydrated.ts`
  gateia leitura de stores com `persist` no primeiro render do client;
  `use-delayed-loading.ts` evita o pisca-pisca de loading em respostas
  rápidas (< 100 ms não mostra nada). `file-tree-skeleton.tsx` e
  `diff-skeleton.tsx` cobrem os painéis Files e Diff do workbench.
- **Stale-while-revalidate genérico**: `lib/hooks/workbench/use-swr.ts`
  (`useWorkbenchSWR`) é o hook central de staleness usado pelos stores
  do workbench.
- **GC de mensagens em memória**: `threads-store.ts` aplica
  `MESSAGES_IN_MEMORY_CAP = 200` — acima disso, entradas mais antigas
  saem do cache do processo automaticamente.
- **Immer nos stores que mais mutam**: `workbench-store.ts` e
  `threads-store.ts` já usam o middleware `immer` do Zustand
  (`immer: "^11.1.16"` no `package.json`) — mutação acidental de
  arrays/objetos aninhados deixou de ser um risco nesses dois stores.
- **Sincronização entre abas**: `lib/hooks/use-broadcast-sync.ts` usa
  `BroadcastChannel` para propagar invalidação entre abas abertas.
- **Novos endpoints de contexto do workspace**: `GET
/workspaces/{id}/stack-hint` (usado pelo empty-state, ver 1.8) já
  existe no backend (`backend/api/handlers/workspaces.py`).

### 1.2 Feedback — toasts, erros, loading

- **Toast centralizado**: `lib/stores/toast-store.ts` +
  `components/ui/toaster.tsx` / `components/ui/snackbar.tsx`. Cobre
  sucesso/erro/aviso com fila e dismiss manual para erros.
- **Banner de rede**: `components/layout/network-status-banner.tsx`
  distingue "offline" (vermelho) de "SSE reconectando" (âmbar), ambos
  `aria-live="polite"`, alimentado por `lib/hooks/use-network-status.ts`.
- **HITL com contexto completo**: `components/chat/features/hitl-panel.tsx`
  já mostra `reasoning`, diff preview com contagem +N/-M linhas
  (expansível), caminhos afetados e modo de permissão ativo. Tem ação
  "sempre permitir" que persiste numa allowlist por workspace
  (`POST /smart-approval/allowlist`, `backend/services/smart_approval.py`).
  Ainda falta uma tela de gerenciamento dessa allowlist (ver seção 2).

### 1.3 Teclado e navegação

- **Registry central de atalhos**: `lib/hooks/use-global-shortcuts.ts`
  substitui listeners espalhados por um registro declarativo
  (`ctrl+t` nova thread, `ctrl+l` limpar mensagens, `ctrl+\` toggle
  workbench, `ctrl+,` settings, `ctrl+k` command palette, `ctrl+?`
  cheatsheet, mais atalhos locais de foco).
- **Command palette `Ctrl+K`**: `components/layout/command-palette.tsx`
  — busca fuzzy por categoria, navegação por setas, fecha no Esc.
- **Cheatsheet de atalhos**: `components/layout/keyboard-shortcuts-dialog.tsx`.
- **Árvore de arquivos acessível**: `components/workbench/files/dir-node.tsx`
  usa `role="treeitem"` + `aria-expanded`.

### 1.4 Resiliência

- **Reconexão SSE visível**: coberta pelo mesmo
  `network-status-banner.tsx` citado em 1.2 — estado "reconectando" é
  distinto de "offline".
- **Detecção de rede**: `lib/hooks/use-network-status.ts` (evento
  `online`/`offline` do browser).

### 1.5 Auth

- **FOUC de auth corrigido**: o guard de `beforeLoad` da rota raiz
  (`src/routes/__root.tsx`) aguarda `persist.rehydrate()` do
  `auth-store` antes de decidir se redireciona para `/auth/signin`.
- **Aviso de sessão prestes a expirar**: `lib/hooks/use-session-expiry.ts`
  agenda um toast 5 minutos antes do `token_expires_at` (repassado pelo
  backend via `UserResponse`, já que o access token é cookie httpOnly)
  com ação "Renovar" que chama `POST /auth/refresh`. Complementa o
  refresh silencioso que já existe em qualquer 401
  (`vectora-client.ts::tryRefreshToken`).

### 1.6 Performance percebida e streaming

- **Custo por mensagem**: `components/chat/message-item.tsx` calcula
  `estimateCost()`/`formatCost()` (`lib/config/model-prices.ts`) a
  partir de `usageMetadata.input_tokens`/`output_tokens` e mostra o
  valor estimado inline na mensagem.
- **Uso de contexto/quota visível**: `components/chat/features/usage-popover.tsx`
  mostra uso por provider com barra de progresso e cor por faixa,
  tratando erro de consulta como erro visível (não como "0 gasto").
- **Renderização de tool calls em progresso**:
  `components/chat/tool-call-renderer.tsx`.

### 1.7 HITL e transparência do agente

- **RAG provenance (citações)**: `message-item.tsx` renderiza
  `RagCitationList`/`RagCitation` (`features/rag-citation-popover.tsx`)
  — a resposta do agente carrega citações estruturadas, não é
  parsing de string no cliente.
- **Timeline de memória/atividade da thread**: aba "Memória" do
  workbench (`components/workbench/tabs/memory-tab.tsx`) mostra
  indexações RAG e buscas em andamento, mais o contexto recuperado em
  pílulas expansíveis por bucket, com toggle ativo/inativo e remoção
  por bucket.
- **Tarefas em segundo plano**: aba "Tarefas" (`tabs/tasks-tab.tsx`)
  lista rotinas/webhooks da sessão com histórico de execuções e link
  para a thread-resultado, atualizando ao vivo via SSE de webhooks.
- **Descoberta de tools**: `components/settings/environment/tabs/tool-policy-panel.tsx`
  lista as tools disponíveis e permite habilitar/desabilitar por
  usuário (`GET`/`PUT /tools/policy`). Falta contador de uso histórico
  (ver seção 2).

### 1.8 Onboarding e empty states

- **Wizards de primeiro uso**: `components/onboarding/setup-wizard.tsx`
  (pós-signup, dentro do produto) e `components/onboarding/pre-auth-wizard.tsx`
  (antes do login) — ambos com testes próprios.
- **Empty state com sugestões por stack**: `components/chat/features/empty-state-header.tsx`
  consulta `GET /workspaces/{id}/stack-hint` e mostra 3 sugestões
  clicáveis (que populam o input, não enviam direto) adaptadas à stack
  detectada (`nodejs`/`python`/`go`/`rust`/`java`/`unknown`).

### 1.9 Multimodal input

- **STT (voz)**: `lib/hooks/files/use-voice-input.ts` integrado ao
  composer via `components/chat/features/voice-input-button.tsx`.
- **Notificação OS de resposta longa**: `chat-interface.tsx` dispara
  `new Notification(...)` quando a resposta demora e a aba não está
  visível, com pedido de permissão sob demanda.
- **Drop zone com previews ricos**: `components/chat/features/file-preview-grid.tsx`
  já renderiza thumbnail de imagem, primeira página de PDF (via
  `lib/utils/files/pdf-preview.ts`) e preview de código/texto (4
  primeiras linhas) — cobre boa parte do que se esperava de "drop zone
  rico".
- **Paste inteligente (parcial)**: colar texto longo vira anexo
  `pasted-<timestamp>.txt` automaticamente; colar imagem do clipboard
  já é capturado como anexo pelo `useFileUpload`. Detecção de URL como
  card, detecção de linguagem de código colado, e prompt para
  JSON/YAML grande **não existem** — ver seção 2.

### 1.10 Mobile e responsividade

- **Workbench em telas estreitas**: `components/layout/ide-mode-layout.tsx`
  colapsa os três painéis (chat/workbench/editor) para um por vez
  abaixo do breakpoint `md`, com faixa de abas no topo para trocar —
  mesmo padrão de nav-strip usado pelas sub-abas do workbench.

---

## 2. Pendente

Itens confirmados como **ausentes** no código atual. Descrições
mantidas enxutas — cada um é um problema real, não um desejo abstrato.

### UX-1 — Gerenciamento visual da allowlist de HITL

O botão "sempre permitir" do `hitl-panel.tsx` já persiste regras via
`POST /smart-approval/allowlist`, mas não há tela para o usuário ver
quais regras estão ativas nem revogá-las. Precisa de uma lista em
Settings (workspace → regras → botão revogar), lendo o endpoint
correspondente de leitura (a confirmar se já existe no backend; se não
existir, também entra no escopo).

### UX-2 — Uso histórico no tool palette

`tool-policy-panel.tsx` mostra a lista de tools e liga/desliga, mas não
mostra "usada N vezes nos últimos 7 dias" nem exemplo de schema — a
pergunta "o que esse agente sabe fazer, e com que frequência usa" só é
respondida parcialmente.

### UX-3 — Smart paste: URL card, linguagem de código, JSON/YAML

O paste hoje só distingue "texto curto" (insere) de "texto longo"
(vira arquivo `.txt`) e "imagem" (vira anexo). Falta:

- Detectar URL colada e oferecer expandir como card (título + OG
  image) via um endpoint de preview.
- Detectar linguagem de código colado e inserir como bloco markdown
  com a linguagem certa em vez de texto plano.
- Prompt "formatar e anexar como arquivo?" para JSON/YAML grande.

### UX-4 — TTS (ouvir mensagem em voz alta)

Não existe botão de leitura em voz alta nas mensagens do agente. Seria
`SpeechSynthesisUtterance` com pause/resume/skip de blocos de código,
gate de acessibilidade real (visão reduzida, uso hands-free).

### UX-5 — Screenshot capture no Electron

Não há uso de `desktopCapturer` no `frontend/electron/` nem botão de
anexar screenshot no plus-menu do chat. Hoje o fluxo é
print-screen-e-arrastar manual.

### UX-6 — Feedback inline (bug/sugestão) pelo próprio app

Não existe modal de feedback no menu do usuário. Hoje reportar um
problema depende de canal externo ao produto.

### UX-7 — CI gate contra strings hardcoded

Não há script `lint:i18n` nem hook equivalente no `package.json` do
frontend. A regra de nunca hardcodear string visível (ver
`CLAUDE.md`) depende inteiramente de revisão manual — PRs podem
reintroduzir string solta sem que nada acuse.

### UX-8 — Formato de data/hora/número explícito por locale

Não foi encontrado um helper central `formatDate`/`formatNumber` que
force locale explícito a partir do idioma escolhido pelo usuário
(`useT().lang`). Onde o código usa `Date.toLocaleString()` sem locale
explícito, o formato segue `navigator.language` do browser, que pode
divergir do idioma escolhido no app.

### UX-9 — Safe-area inset (notch/Dynamic Island em iOS)

Nenhum uso de `env(safe-area-inset-*)` no CSS do app. Em PWA standalone
num iPhone com notch, o header pode ficar cortado.

### UX-10 — Gestos mobile nativos (pull-to-refresh, long-press)

Não há handler de `touchstart`/`touchmove` para pull-to-refresh na
sidebar, nem long-press para abrir ações contextuais em bottom-sheet.
O layout responsivo do workbench (1.10) resolve a navegação entre
painéis, mas não os gestos de lista.

### UX-11 — Badge counters (sidebar/tray)

Não há contador de mensagens novas por thread na sidebar, nem badge no
tray icon do Electron para notificação pendente. Relevante sobretudo
para threads compartilhadas entre usuários (Pro).

### UX-12 — Quiet hours para notificações OS

Não existe preferência de silenciar notificações num intervalo
(ex: 22h–8h). A notificação de resposta longa (1.9) dispara a qualquer
hora.

### UX-13 — Resume conversation entre dispositivos

Não há indicador "você estava aqui em outro device há N min". Depende
de expor `last_active_at` por `(user, device, thread)`, que hoje não
está no schema de threads.

### UX-14 — Backup/restore wizard na reinstalação

`vectora backup create/restore` existe como comando de CLI, mas não há
modal que detecte instalação anterior incompatível e ofereça importar
workspaces/threads/memórias com preview do que será trazido.

### UX-15 — Insight semanal de uso

Não existe notificação ou card periódico com resumo de uso (tokens da
semana, tools mais usadas, modelo mais usado, custo estimado).

### UX-16 — RTL

Nenhum uso de `dir="rtl"` ou classes lógicas (`ms-*`/`me-*`) no lugar
de `margin-left`/`margin-right` foi encontrado de forma sistemática.
Não é bloqueante hoje (produto é pt-BR/en/es), mas qualquer adição de
idioma RTL no futuro exigiria auditoria de CSS primeiro.

---

## 3. Notas de arquitetura que continuam válidas

Princípios que orientaram os itens já implementados e devem continuar
orientando os pendentes.

**Toast como canal único de feedback silencioso.** Nenhuma falha de
ação do usuário deveria terminar em `console.error` sem chegar ao
`toast-store`. Isso já é maioria hoje; ao tocar um fluxo que ainda
retorna `null` silenciosamente, empurrar para o toast é a correção
mínima.

**Skeleton é contrato de UX, não decoração.** Se o layout do conteúdo
real muda (novo campo, nova coluna), o skeleton correspondente
(`file-tree-skeleton.tsx`, `diff-skeleton.tsx`) precisa mudar junto.

**SSE é o sistema nervoso central do chat.** Toda degradação de
conexão deve ficar visível em poucos segundos — o padrão já existe em
`network-status-banner.tsx`; qualquer canal SSE novo (ex: eventos de
workspace) deve reusar o mesmo hook de status em vez de inventar um
paralelo.

**Reusar hooks existentes antes de criar novo.** Antes de qualquer
item da seção 2, checar `lib/hooks/` — em particular
`use-hydrated.ts`, `workbench/use-swr.ts`, `use-broadcast-sync.ts`,
`use-network-status.ts`, `use-session-expiry.ts` e
`use-global-shortcuts.ts` cobrem a maior parte dos primitivos de UX
que este documento historicamente pedia para criar do zero.

**Visibilidade do agente é confiança.** O cluster HITL + citações RAG

- timeline de memória (seção 1.7) já entrega a maior parte da proposta
  original: o usuário consegue ver o que o agente fez e de onde tirou
  cada afirmação. O que falta (seção 2, UX-1 e UX-2) é gerenciamento e
  histórico dessas decisões, não a visibilidade em si.
