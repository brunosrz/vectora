# Vectora — Modo IDE e Workbenches

Referência do estado atual do modo IDE (`uiMode`) e das abas de workbench do
frontend. Descreve o que existe no código hoje — não é um plano de feature.

---

## 1. `uiMode` — três layouts, não um interruptor

O produto tem três modos de interface, guardados em `useSettingsStore`
(`frontend/lib/stores/settings-store.ts`) como `uiMode: "assistant" | "ide" |
"kanban"`, trocados pelo `IdeModeSwitch`
(`frontend/components/header/ide-mode-switcher.tsx`) no header. O switch é
condicionado a `showModeSwitch`/`enableFeaturesBeta` conforme o contexto da
rota, não a um único flag booleano.

O roteamento de layout acontece em `frontend/src/routes/session/$threadId.tsx`:

```tsx
{uiMode === "kanban" && !chatMode ? (
  <KanbanBoard threadId={threadId} />
) : uiMode === "ide" && !chatMode ? (
  <IdeModeLayout
    isNarrow={isNarrowViewport}
    navBar={<WorkbenchNavBar threadId={threadId} side="left" />}
    workbenchContent={...}
    ...
  />
) : (
  // layout "assistant" — chat centralizado, workbench como painel lateral
)}
```

- **`assistant`** (default) — chat centralizado, workbench como painel
  lateral/flutuante.
- **`ide`** — layout `IdeModeLayout` (`frontend/components/layout/
ide-mode-layout.tsx`): navegação lateral fixa + editor/painéis docked via
  `DockedEditor` (`frontend/components/workbench/windows/docked-editor.tsx`).
- **`kanban`** — `KanbanBoard` substitui o chat pela visão de tarefas.

A store persiste `uiMode` (`localStorage`, chave versionada) e migra estados
antigos: a versão 2 do schema normaliza um `uiMode` ausente ou desatualizado
de volta para `"assistant"`.

---

## 2. Abas de workbench

`WorkbenchTab` (`frontend/lib/stores/workbench-store.ts`) define as abas
disponíveis, na ordem em que aparecem:

```
files → diff → plan → tasks → browser → storage → context_graph → library → terminal
```

O painel (`workbench-panel.tsx`/`workbench-slide-panel.tsx`) é multi-aba com
estado persistido por thread (`activeTabByThread`) e cache volátil por aba
(padrão _stale-while-revalidate_, igual ao `threads-store`).

| Aba             | Componente principal                                                                                                       | O que faz                                                                  |
| --------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `files`         | `workbench/files/files-tab.tsx`                                                                                            | Explorer de arquivos do workspace, pins, histórico por arquivo             |
| `diff`          | `workbench/git/git-tab.tsx`, `changes-view.tsx`, `history-view.tsx`                                                        | Status git, diff de mudanças e histórico de commits                        |
| `plan`          | `workbench/tabs/plan-tab.tsx`                                                                                              | Plano do agente (todo list)                                                |
| `tasks`         | `workbench/tabs/tasks-tab.tsx`                                                                                             | Tarefas em background                                                      |
| `browser`       | `workbench/tabs/browser-tab.tsx`, `browser-devtools-panel.tsx`                                                             | Gestão de dev server + DevTools do Chromium controlado pelo agente         |
| `storage`       | —                                                                                                                          | Inspeção de storage (Postgres/Redis/Qdrant/SQLite/LanceDB conforme o modo) |
| `context_graph` | `workbench/tabs/context-graph-tab.tsx`                                                                                     | Build/consulta do grafo de contexto do workspace                           |
| `library`       | `workbench/tabs/library-tab.tsx` (+ `library-mcp-section.tsx`, `library-memory-section.tsx`, `library-skills-section.tsx`) | Conectores MCP, memória e skills                                           |
| `terminal`      | `workbench/terminal/`                                                                                                      | Terminal via PTY                                                           |

---

## 3. Git/Diff — hunks coloridos, sem editor de diff dedicado

`GET /workspaces/{id}/git/diff` e `GET /workspaces/{id}/git/diff/file`
(`backend/api/handlers/workspaces.py`) devolvem, respectivamente, o resumo
de arquivos alterados e os hunks de um arquivo específico (unified diff
parseado por `_parse_unified_diff`); `GET /workspaces/{id}/git/commit/diff`
devolve o diff completo de um commit (`git show --unified=3 --stat`).

O frontend consome esses hunks em `HunkView`
(`workbench/git/shared.tsx`) — um `<pre>` com coloração verde/vermelho por
linha (sem highlight de sintaxe, sem visão lado a lado). `changes-view.tsx`
e `history-view.tsx` expandem o diff inline ao clicar no arquivo/commit; não
há um editor de diff dedicado (tipo Monaco `DiffEditor`) nem um painel
docked específico para diffs — a fidelidade de renderização hoje é a mesma
em `assistant` e em `ide` mode.

---

## 4. Browser workbench — DevTools reais, não um iframe de preview

A aba `browser` não é um iframe apontando para o dev server do usuário; é a
superfície de duas famílias de tools nativas do agente sobre um Chromium
controlado via CDP (Chrome DevTools Protocol):

- **`backend/tools/browser.py`** — navegação e interação básica (clicar,
  preencher, rolar, screenshot) e gestão de dev server (start/stop de
  processos configurados em `.vectora/launch.json`, no formato usado pelo
  Claude Code).
- **`backend/tools/browser_devtools.py`** — controle avançado: múltiplas
  abas, logs de console e de rede, `evaluate` de JavaScript arbitrário,
  política de dialogs, emulação (rede/dispositivo), tracing de performance,
  heap snapshot e comparação de snapshots, análise de trace.

A sessão do Chromium é gerenciada por `backend/browser/session.py`
(`has_browser_session`, `list_tabs`, `new_tab`, `select_tab`, `close_tab`),
com isolamento (`backend/browser/ssrf_guard.py`) e fallback de busca
(`search_fallback.py`). No frontend, `BrowserTab`
(`workbench/tabs/browser-tab.tsx`) lista servidores configurados em
`launch.json`, permite iniciar/parar cada um e mostra `BrowserDevtoolsPanel`
para inspecionar console/rede/estado da página que o agente está
controlando — é uma superfície de observabilidade sobre o browser do
agente, não uma preview embutida do app do usuário.

---

## 5. Referências de teste

- Backend: `vectora/tests/unit/test_browser_dev_server.py`,
  `test_browser_session_real.py`, `test_browser_session_jail.py`,
  `test_browser_session_uid_helpers.py`,
  `test_browser_search_fallback_real.py`.
- Frontend: `frontend/components/header/__tests__/ide-mode-switcher.test.tsx`,
  `frontend/components/workbench/git/__tests__/`,
  `frontend/e2e/workbench-tabs.spec.ts`, `frontend/e2e/git-workflow.spec.ts`.
