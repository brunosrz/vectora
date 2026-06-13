# Vectora — Plano de Experiência do Usuário (UX)

> Pseudo-plano de referência — não editar o `docs/plan.md` principal.
> Foco: tudo que impacta como o usuário **percebe, confia e usa** o Vectora,
> muito além de "UI bonita". Inclui estado, dados, feedback, resiliência,
> teclado, auth, streaming, acessibilidade e performance percebida.

---

## 0. Por que UX vai muito além da interface visual

Um componente bem estilizado que mostra dados velhos é pior do que um
componente feio que mostra dados corretos. Um toast que aparece e some em
2 s antes do usuário ler é pior que silêncio. Um `loading…` que dura 4 s
sem indicação de progresso faz o usuário recarregar a página.

Este documento mapeia os **buracos de experiência** do Vectora em seis
dimensões:

1. **Estado e dados** — freshness, cache, invalidação, multi-aba
2. **Feedback** — toasts, erros inline, loading states, progresso
3. **Teclado e navegação** — atalhos, foco, acessibilidade
4. **Resiliência** — offline, SSE, reconexão, retry
5. **Auth** — flash de não-autenticado, refresh, sessão expirada
6. **Performance percebida** — time-to-interactive, skeleton, streaming

---

## 1. Estado e dados

### UX-1 — Flash of Workspaces (sem skeleton)

**Problema**: `workspaces-store.ts` inicializa com `workspaces: []`,
`active_id: null` e `loading: false`. No primeiro render, o componente vê
lista vazia **antes** de `hydrate()` terminar. O usuário vê "Nenhum
workspace" por 200–500 ms mesmo tendo workspaces configurados.

**Causa raiz**: três estados colapsados num mesmo shape — "ainda não
carregou" (`fetchedAt === null && pending`), "carregou vazio" (`fetchedAt
!== null && workspaces.length === 0`), "erro" (sem campo `error`). O
booleano `loading` cobre o primeiro caso mas é descartado pelos
componentes.

**Correção** (não inventar `hydrated` quando já existe primitivo melhor):

- Substituir `loading: boolean` por máquina de estado `status:
"idle" | "loading" | "success" | "error"` (ver UX-11 + nota arquitetural
  §12). Derivar `hasLoaded = fetchedAt !== null`.
- **Reusar** `chat/lib/hooks/use-hydrated.ts` (já existe) para gatear
  qualquer leitura de store com `persist` durante o primeiro render do
  client e evitar mismatch SSR. Não criar um `hydrated` paralelo no
  workspaces-store — `workspaces-store` não é persistido, então o gate
  correto é `fetchedAt`.
- No componente: `if (!hasLoaded) return <WorkspacesSkeleton />`.
- Persistir **apenas** `active_id` em `localStorage` (não a lista — o
  backend é fonte de verdade). Elimina o flash do seletor de workspace
  no header ao recarregar.

**Impacto**: elimina o flash; skeleton consistente; o `active_id`
persistido sobrevive ao reload sem esperar o `hydrate()`.

---

### UX-2 — Sem TTL / auto-invalidação nos stores

**Problema**: `workspaces-store` tem `fetchedAt` mas **nunca é
verificado**. Se o usuário fica 10 min na mesma aba, a lista de workspaces
fica obsoleta sem que ninguém perceba. Idem para `threads-store` (sem
persist, sem revalidação em foco) e idem para `safeRoots` no mesmo
workspaces-store (carrega uma vez, jamais revalida).

**Comparação**: `workbench-store` tem `WORKBENCH_STALE_MS = 30_000` + o
hook `useWorkbenchSWR` (`chat/lib/hooks/workbench/use-swr.ts`, já
implementado, com dedup por chave). Os outros stores ignoram esse padrão.

**Correção** (não reinventar — aplicar o hook que já existe):

- `useWorkbenchSWR` é genérico o suficiente para qualquer store. Apenas
  renomear o arquivo para `chat/lib/hooks/use-swr.ts` e adotar nos
  componentes consumidores de `workspaces-store`, `threads-store`,
  `auth-store` (`hydrate`), `useLicenseStatus`.
- Constantes de staleness por domínio:
  - `WORKSPACES_STALE_MS = 60_000` (mudanças raras).
  - `THREADS_STALE_MS = 30_000` (multi-user pode criar novas).
  - `SAFE_ROOTS_STALE_MS = 5 * 60_000` (mudança quase nunca).
  - `LICENSE_STALE_MS = 5 * 60_000` (cache 6h já no backend; UI revalida
    com janela menor).
- **Triggers de revalidação fora do hover do componente**:
  - `document.visibilitychange` → revalida ao voltar para a aba.
  - `window.focus` → idem.
  - `online` (UX-16) → força revalidação ao reconectar.
  - SSE `workspace_changed` / `safe_root_changed` (futuro — FS-19 + Bloco
    G para multi-server) → invalida `fetchedAt`.

---

### UX-3 — `patchMessages` sem GC de mensagens antigas

**Problema**: `threads-store.patchMessages(threadId, updater)` acumula
mensagens para sempre. Em threads longas (100+ mensagens com tool calls,
artifacts, anexos inline), o store pode crescer para 10–20 MB de RAM sem
mecanismo de limpeza. Toda thread visitada na sessão fica residente.

**Impacto real**: abas abertas por horas ficam lentas; React re-renderiza
listas grandes. Custo agravado pelo spread shallow em cada token do
stream (UX-5).

**Correção**:

- **Cap por thread**: `MESSAGES_IN_MEMORY_CAP = 200`. Acima disso, dropar
  mensagens do **início** (mais antigas); histórico recuperável via
  `GET /threads/{id}/history?before=<msg_id>` on-demand quando o user
  rola para cima.
- **TTL por thread inativa**: `lastActiveAt` por entry no cache; cleanup
  de threads sem acesso há > 5 min (já há campo `updatedAt` — basta
  reusar e separar de `fetchedAt`). Cleanup pode rodar em `setInterval`
  de 60 s ou ser oportunista no próximo `setMessages`.
- **Cap global de bytes** (defesa em profundidade): estimar tamanho
  serializado do `cache` no devtools; se > 50 MB, evict thread menos
  recentemente acessada (LRU). Mensurar antes de implementar — pode ser
  overkill.

---

### UX-4 — `new-thread-registry` leak

**Problema**: `chat/lib/stores/new-thread-registry.ts` é um `Set` global
de módulo. A API já expõe `clearNew(threadId)` — mas **ninguém chama
após a thread ser persistida**. Em sessões longas (dias), acumula IDs
que não correspondem mais a threads novas.

**Consequência**: o `ChatInterface` pula o fetch de histórico em threads
que **deveriam** ter histórico (porque `isNew(threadId)` continua
retornando `true` muito depois do thread já ter sido salvo no backend).

**Correção** (cirúrgica, a API certa já existe):

- No `use-stream-handler.ts`, no primeiro evento `thread_persisted` (ou
  no primeiro `setMessages` bem-sucedido após criação): chamar
  `clearNew(threadId)`. Garante remoção determinística.
- Defesa em profundidade: TTL de 5 min via `setTimeout` no `markAsNew` —
  remove sozinho mesmo se o caller esquecer.
- Migrar para Zustand opcional — o `Set` de módulo é correto enquanto a
  API for `markAsNew`/`isNew`/`clearNew` sem subscribers reativos.

---

### UX-5 — Sem Immer → mutações acidentais

**Problema**: Zustand sem Immer exige retornar objetos novos em `set()`.
Qualquer `state.someArray.push(...)` dentro de um selector ou action
**muta silenciosamente** sem disparar re-render.

**Risco atual**: stores com arrays (`workspaces`, `messages`, `files`,
`openFiles`) são candidatos a mutação acidental difícil de debugar.

**Correção**:

```bash
pnpm --dir chat add immer
```

```typescript
// Envolver create com immer middleware
import { immer } from "zustand/middleware/immer";
export const useWorkbenchStore = create<WorkbenchState>()(
  immer((set) => ({
    // actions podem usar draft diretamente:
    addFile: (wsId, file) =>
      set((draft) => {
        draft.filesCache[wsId]?.tree.push(file);
      }),
  })),
);
```

Prioridade: aplicar primeiro nos stores que mais mutam (workbench, threads).

---

### UX-6 — Sem sincronização entre abas (multi-tab)

**Problema**: o usuário abre o Vectora em duas abas. Aba A cria um
workspace. Aba B ainda mostra a lista antiga. Aba A troca de thread. Aba B
não sabe. Não há canal de sincronização entre abas.

**Correção primária** — `BroadcastChannel`:

```typescript
// workspaces-store.ts
const bc = new BroadcastChannel("vectora:workspaces");
bc.onmessage = () => get().hydrate(); // revalidar ao receber sinal

// Após qualquer mutação:
bc.postMessage("invalidate");
```

Aplicar nos stores que importam para coerência: `workspaces`, `threads`,
`auth`.

**Correção secundária** — `storage` event do localStorage:

```typescript
window.addEventListener("storage", (e) => {
  if (e.key?.startsWith("vectora-settings-")) loadUserSettings();
});
```

Garante que preferências mudam em todas as abas sem reload.

---

## 2. Feedback — toasts, erros, loading

### UX-7 — Sistema de toast ausente ou inconsistente

**Problema atual**: erros de API são silenciados (`return null`) ou
mostrados em `console.error`. O usuário não sabe que uma ação falhou.
Exemplos: `fetchJson` retorna `null` sem notificar; `trust()` falha
silenciosamente se o workspace não existe.

**O que falta**:

- Um sistema centralizado de notificações (toast/snackbar).
- Categorias: `success`, `error`, `warning`, `info`.
- Duração configurável; erros ficam até o user fechar.
- No máximo 3 toasts visíveis simultaneamente (fila).

**Implementação sugerida**:

```typescript
// chat/lib/stores/toast-store.ts
interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  body?: string;
  duration?: number; // ms; undefined = manual dismiss
}

// Uso nos stores:
useToastStore.getState().push({
  type: "error",
  title: "Falha ao criar workspace",
  body: err.message,
});
```

**Biblioteca**: Sonner (`sonner`) — zero config, acessível, <3 KB. Ou
Radix Toast (já no shadcn/ui) se o projeto já usa.

**Cobertura obrigatória**:

- Falha de rede (fetch retornou null)
- Erro de validação 422 do backend
- Expiração de sessão (401 inesperado fora do auth flow)
- Ações destrutivas concluídas (delete de arquivo → "Movido para a lixeira")
- Ações git concluídas (commit → "Commit realizado: abc1234")

---

### UX-8 — Loading states de granularidade errada

**Problema**: `workspaces-store.loading` é um booleano global. Qualquer
operação (listar, criar, confiar) liga o mesmo spinner. O usuário não sabe
o que está carregando.

**Padrão atual no workbench-store**: cada slice tem `fetchedAt` e o hook
`useWorkbenchSWR` controla loading por chave — correto, mas não replicado.

**Correção**:

```typescript
// Estados de loading por operação, não global:
interface WorkspacesState {
  pending: {
    hydrate: boolean;
    create: boolean;
    trust: string | null; // ID do workspace sendo confiado
    gitInit: string | null;
  };
}
```

Regra: **nunca um único `loading: boolean`** para múltiplas operações.
Cada botão de ação deve ter seu próprio estado de `pending`.

---

### UX-9 — Skeleton screens vs spinners

**Problema**: spinners centrados na tela bloqueiam a percepção de progresso.
Em conexões rápidas, o spinner pisca (aparece e some em <100 ms), o que é
pior que não mostrar nada.

**Regra de ouro**:

- `< 100 ms`: não mostrar nada (o dado chegou antes de qualquer feedback)
- `100–1000 ms`: spinner pequeno, inline (não bloqueante)
- `> 1000 ms`: skeleton screen com forma do conteúdo esperado

**O que o Vectora precisa**:

- `ThreadListSkeleton` — 5 linhas com shimmer (sidebar)
- `FileTreeSkeleton` — árvore com shimmer (painel files)
- `DiffSkeleton` — 3 blocos de arquivos com shimmer (painel diff)
- `MessageListSkeleton` — bolhas de chat com shimmer (janela principal)

**Implementação**: Tailwind `animate-pulse` + blocos `bg-muted/40` com
shapes correspondentes ao conteúdo real.

**Delay de 100 ms antes de mostrar skeleton**:

```typescript
function useDelayedLoading(isLoading: boolean, delay = 100) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!isLoading) {
      setShow(false);
      return;
    }
    const t = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(t);
  }, [isLoading, delay]);
  return show;
}
```

---

### UX-10 — Erros inline vs modais

**Problema**: erros de formulário (criar workspace com path inválido, commit
sem mensagem) não têm feedback inline. O handler retorna `null` e o
formulário fica no mesmo estado sem indicar o que deu errado.

**Regra**: erro de **input do usuário** → inline, abaixo do campo.
Erro de **sistema** (rede, servidor) → toast.

**Implementação**:

```typescript
// Retorno tipado nos stores:
type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; field?: string };

// Componente:
const result = await create(path);
if (!result.ok) {
  setFieldError(result.field ?? "root", result.error);
}
```

---

### UX-11 — Ausência de estados de erro persistentes

**Problema**: se `hydrate()` falha (backend offline), `workspaces` fica
`[]` e `loading: false`. O usuário vê tela vazia sem explicação.

**Correção**:

```typescript
interface WorkspacesState {
  error: string | null;
}

// No hydrate():
try { ... }
catch (e) {
  set({ error: "Não foi possível carregar workspaces. Tente novamente.", loading: false });
}

// No componente:
if (error) return <ErrorBanner message={error} onRetry={hydrate} />;
```

Padrão: todo estado que pode falhar deve ter `error: string | null` e
exibir um `<ErrorBanner onRetry={...}>` com botão de retry.

---

## 3. Teclado e acessibilidade

### UX-12 — Mapa de atalhos incompleto

**Atalhos implementados** (após bfe9723):

- `Ctrl+N` → novo arquivo (painel Files)
- `Ctrl+Shift+N` → nova pasta (painel Files)
- `Del` → mover para lixeira (item focado)
- `Shift+Del` → delete permanente
- `Esc` → cancelar criação inline

**Atalhos faltantes de alta prioridade**:

| Ação                                | Atalho sugerido        | Onde           |
| ----------------------------------- | ---------------------- | -------------- |
| Nova thread                         | `Ctrl+T`               | Global         |
| Focar input do chat                 | `Ctrl+L` ou `/`        | Global         |
| Alternar painel lateral (workbench) | `Ctrl+\`               | Global         |
| Abrir painel Files                  | `Ctrl+Shift+E`         | Global         |
| Abrir painel Diff                   | `Ctrl+Shift+G`         | Global         |
| Navegar entre threads               | `Alt+↑` / `Alt+↓`      | Sidebar focada |
| Confirmar HITL                      | `Enter`                | Modal HITL     |
| Rejeitar HITL                       | `Esc`                  | Modal HITL     |
| Buscar em arquivos                  | `Ctrl+Shift+F`         | Global         |
| Submeter chat                       | `Enter` (já tem)       | Chat input     |
| Quebra de linha                     | `Shift+Enter` (já tem) | Chat input     |

**Implementação**:

```typescript
// chat/lib/hooks/use-global-shortcuts.ts
// Centralizar TODOS os atalhos globais aqui (não dispersos em useEffect)
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "t") {
      e.preventDefault();
      navigate("/session/new");
    }
    // ... demais atalhos
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, [navigate]);
```

---

### UX-13 — Foco e ordem de tab

**Problemas identificados**:

- `FileItem` e `DirNode` têm `tabIndex=0` mas a ordem não é natural (itens
  dentro de pastas abertas podem ter tabIndex depois de irmãos).
- Botões de ação (trash, @, rename) ficam fora do foco quando o item não
  está hovered — invisíveis para usuários de teclado.
- Modais de confirmação de delete não trapam o foco (usuário pode Tab para
  fora do modal sem perceber).

**Correções**:

- Focus trap em todos os modais (`@radix-ui/react-dialog` já implementa —
  garantir que os confirms de delete usem Dialog, não `window.confirm`).
- Botões de ação sempre visíveis quando item está focado via teclado
  (`focus-within:opacity-100`).
- `aria-label` em botões ícone (trash, @, chevron).

---

### UX-14 — ARIA e semântica

**O que está faltando**:

- `role="tree"` + `role="treeitem"` na árvore de arquivos.
- `aria-expanded` nos nós de pasta.
- `aria-selected` no item ativo.
- `aria-live="polite"` na área de mensagens do chat (para screen readers
  anunciarem novas mensagens do agente sem interromper o usuário).
- `aria-busy="true"` nos botões durante operações async.

**Por que importa**: acessibilidade não é só compliance — é também SEO
(em contextos de SSR futuro) e qualidade geral de markup semântico.

---

## 4. Resiliência

### UX-15 — Reconexão SSE sem notificação

**Problema**: quando o SSE (`/chat/stream`) cai (rede flaky, VPS reinicia,
idle timeout do nginx), o cliente não sabe. A mensagem do agente para de
chegar. Sem indicação visual, o usuário pensa que o agente travou.

**Comportamento atual**: o `EventSource` do browser tenta reconectar
automaticamente (back-off padrão), mas o chat UI não reflete isso.

**Correção**:

```typescript
// chat/lib/hooks/use-stream-handler.ts
// Escutar eventos do EventSource:
eventSource.onerror = () => {
  setConnectionStatus("reconnecting"); // toast ou badge
};
eventSource.onopen = () => {
  if (connectionStatus === "reconnecting") {
    setConnectionStatus("connected");
    toast.success("Reconectado");
  }
};
```

**UI**: badge discreto no header ("Reconectando…" com spinner) durante
ausência de SSE. Some ao reconectar.

---

### UX-16 — Sem modo offline / sem detecção de rede

**Problema**: se o usuário perde conexão, `fetch()` rejeita. Os stores
silenciam o erro (`return null`). Não há feedback "você está offline".

**Correção mínima**:

```typescript
// chat/lib/hooks/use-network-status.ts
export function useNetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}
```

**UI**: banner fixo no topo quando offline ("Sem conexão — as alterações
serão sincronizadas quando você reconectar"). Botões de ação ficam
`disabled` (não silenciosamente ignorados).

---

### UX-17 — Retry automático com back-off exponencial

**Problema**: `fetchJson` faz uma única tentativa e retorna `null` em
qualquer falha. Falhas de rede transitórias (500ms de dropout) causam perda
silenciosa de operação.

**Correção**:

```typescript
async function fetchJson(
  url: string,
  init?: RequestInit,
  { retries = 2, backoff = 300 } = {},
): Promise<any | null> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, init);
      if (res.ok) return await res.json();
      if (res.status < 500) return null; // 4xx não faz sentido retentar
    } catch {
      /* network error */
    }
    if (attempt < retries) await sleep(backoff * 2 ** attempt);
  }
  return null;
}
```

Não aplicar a ações destrutivas (DELETE, POST crítico) sem idempotency
check — retry de um DELETE pode não ser idempotente se o backend não
garantir.

---

### UX-18 — Resiliência do streaming de chat

**Problema**: se o SSE cai no meio de uma resposta do agente (ex: na
mensagem 500 de 2000 caracteres), o fragmento parcial fica preso no store.
Recarregar a página mostra a mensagem completa do histórico, mas o estado
intermediário ficou "travado" visualmente.

**Correção**:

- Ao montar uma thread que tem mensagem com `role="assistant"` sem
  `finished: true`, verificar no backend se a mensagem está realmente
  em andamento (via `GET /threads/{id}/status`).
- Se não estiver → marcar como `status: "interrupted"` e mostrar badge
  "Resposta interrompida — reconectar?" com botão de retry.

---

## 5. Auth UX

### UX-19 — Flash of Unauthenticated Content (FOUC de auth)

**Problema**: `auth-store.ts` inicializa com `isAuthenticated: false` (antes
de reidratar do `sessionStorage`). Durante os primeiros milissegundos, o
`__root.tsx` vê usuário não-autenticado e pode redirecionar para `/signin`
desnecessariamente, ou piscar conteúdo protegido.

**Causa**: a reidratação do persist (sessionStorage) é síncrona no Zustand
se `getItem` for síncrono — mas o `beforeLoad` do TanStack Router pode
rodar antes da hidratação estar completa.

**Correção**:

```typescript
// __root.tsx beforeLoad:
await useAuthStore.persist.rehydrate();
const { isAuthenticated } = useAuthStore.getState();
if (!isAuthenticated) throw redirect({ to: "/auth/signin" });
```

Garantir que `rehydrate()` é `await`-ado **antes** de qualquer guard.

---

### UX-20 — Sessão expirada durante uso ativo

**Problema**: o access token expira enquanto o usuário está editando. A
próxima requisição retorna 401. `auth-store.hydrate()` tenta refresh
automático — mas se o refresh token também expirou (sessão longa), o
usuário é redirecionado para `/signin` **perdendo o contexto atual**
(thread aberta, texto digitado no input).

**Correção** (`chat-input-store` é volátil — `pushDraft` no momento do
redirect é nulo se não for persistido antes):

1. Antes do redirect de logout, persistir em `sessionStorage`:
   - `vectora:return_to = location.href`
   - `vectora:input_draft = <texto atual do input>` (capturado via
     evento `beforeunload` ou diretamente no interceptor 401).
2. Após login bem-sucedido, `navigate(returnTo ?? "/")` + hidratar
   `chat-input-store.pushDraft(savedDraft)` no mount do
   `ChatInterface`.
3. `sessionStorage` (não `localStorage`) — o draft é específico da aba
   e expira ao fechar o browser. Limpar `vectora:input_draft` após
   consumido para evitar reaparecer numa rota diferente.
4. Casos de borda: se a thread atual também foi removida do backend
   (admin deletou), `return_to` cai num 404 — `__root.tsx beforeLoad`
   detecta e redireciona para `/`.

---

### UX-21 — Sem indicação de "sessão vai expirar"

**Problema**: o usuário recebe 401 sem aviso prévio. Em sessões com tokens
de curta duração (<1h), isso é frequente.

**Correção**:

- Decodificar `exp` do JWT access token (sem verificar assinatura — só
  para UX).
- 5 min antes do exp: toast de aviso "Sua sessão vai expirar em 5 min.
  [Renovar agora]".
- Ao clicar, chamar o refresh endpoint e renovar silenciosamente.

---

## 6. Performance percebida

### UX-22 — Time-to-Interactive (TTI) da thread

**Problema**: ao navegar para uma thread existente, o usuário espera:

1. Rota carregada (TanStack Router)
2. Auth verificada
3. Workspace carregado
4. Thread e mensagens carregadas
5. SSE conectado

Cada etapa é serial. Em conexões lentas, TTI pode ser 3–5 s.

**Otimizações**:

- Prefetch de thread ao hover no sidebar (`router.preload()`).
- Carregar mensagens em paralelo com workspace (não são dependentes).
- Mostrar skeleton de mensagens imediatamente (sem esperar workspace).
- Conectar SSE antes mesmo de o workspace carregar.

---

### UX-23 — Virtualização da lista de mensagens

**Status**: `@tanstack/react-virtual` já está no projeto (`plan.md` Bloco
T). Verificar se está sendo aplicado na `MessageList` — em threads longas
(100+ mensagens), renderizar tudo causa janks visíveis.

**O que falta**: aplicar `useVirtualizer` na `MessageList` com `estimateSize`
calibrado para mensagens com blocos de código (estimativa conservadora de
200px; variância real ajustada por `measureElement`).

**Cuidado**: com SSE em andamento (streaming), novos itens são adicionados
ao final — virtualizer deve `scrollToIndex(last)` automaticamente a menos
que o usuário tenha rolado para cima (user-scrolled detection).

---

### UX-24 — Streaming UX

**Problemas no streaming atual**:

- Não há indicador de "agente digitando" antes do primeiro token chegar.
  Janela de latência do modelo pode ser 1–3 s de silêncio.
- Tool calls que demoram (ex: grep em repositório grande) não têm
  estimativa de progresso.
- Mensagem parcial não tem indicador de "ainda chegando" (cursor piscante
  ou spinner ao final do texto).

**Correções**:

- Ao enviar mensagem, mostrar imediatamente balão do agente com `…`
  (ou cursor piscante) antes do primeiro token.
- Tool calls em progresso: `<ToolCallBadge status="running">` com spinner
  inline e timestamp "há 3 s".
- Ao terminar o stream (`finish_reason`): remover cursor, mostrar timestamp
  final e botão de cópia.

---

### UX-25 — Sem indicador de uso de contexto

**Problema**: o usuário não sabe o quanto da janela de contexto do modelo
está preenchida. Em threads longas, o modelo começa a "esquecer" coisas —
mas o usuário não tem como perceber isso até o comportamento degradar.

**Correção**:

- Backend: incluir `usage.input_tokens` e `model_context_limit` na
  resposta SSE (evento `usage` já existe em alguns providers).
- Frontend: barra de contexto discreta no header da thread
  (`████░░░░ 42% de contexto usado`).
- Ao atingir 80%: aviso "Contexto quase cheio — considere nova thread".
- Ao atingir 95%: aviso bloqueante com botão "Continuar em nova thread
  (compactar histórico)".

---

## 7. HITL (Human-in-the-Loop) UX

### UX-26 — Modal de HITL sem contexto suficiente

**Problema atual**: o modal de aprovação de ação destrutiva (ex: `rm -rf`,
`git push --force`) mostra o comando, mas não mostra:

- Qual arquivo/pasta será afetado (path completo).
- Preview do diff resultante (para write/edit de arquivo).
- Por que o agente quer fazer isso (reasoning step).

**Correção**:

```
┌─ Confirmar ação — Agente quer modificar arquivo ──────────────────┐
│                                                                    │
│  📄 src/api/handlers/workspaces.py                                 │
│                                                                    │
│  Motivo: "Corrigir o path de resolução no delete_fs_node"          │
│                                                                    │
│  Alterações:                                                       │
│  - 12 linhas adicionadas  + 3 linhas removidas                     │
│  [Ver diff completo ▼]                                              │
│                                                                    │
│  Modo atual: Perguntar sempre              [Alterar modo]          │
│                                                                    │
│  [Negar]  [Aprovar esta vez]  [Sempre aprovar este tipo]           │
└────────────────────────────────────────────────────────────────────┘
```

**Dados necessários do backend**: `action.reasoning`, `action.diff_preview`,
`action.affected_paths` — já captados no evento de tool call, apenas não
expostos na UI.

---

### UX-27 — Sem histórico de ações HITL

**Problema**: o usuário aprovou ou negou 10 ações nesta sessão. Não há como
ver o que aprovou, o que negou, e reverter decisões de "sempre aprovar".

**Correção**:

- Sidebar ou Settings → aba "Permissões": lista de regras ativas ("Sempre
  aprovar: escrita em `src/`") com botão de revogar.
- Log de ações desta sessão: `[14:32] Aprovado: editar workspaces.py`.

---

## 8. Onboarding e empty states

### UX-28 — Empty states sem ação clara

**Problema**: quando não há threads, o usuário vê uma tela em branco ou
mensagem genérica. Não há convite claro para começar.

**Correção**:

```
Nenhuma conversa ainda.

Comece sua primeira conversa com o agente →  [Nova conversa]

Ou explore o que é possível:
  💻 "Crie um projeto FastAPI básico em /tmp/meu-projeto"
  🔍 "Explique o arquivo src/api/server.py"
  📝 "Revise o código em src/handlers/"
```

Empty states são **calls to action**, não mensagens de erro.

---

### UX-29 — Workspace não confiável sem guia de onboarding

**Problema**: ao abrir workspace não confiável, o botão "Confio nesta pasta"
aparece, mas o usuário não entende o modelo de segurança do Vectora (por que
precisa confiar? O que muda ao confiar?).

**Correção**: tooltip expandido + link para documentação. Ao confiar pela
primeira vez: `toast.success("Workspace desbloqueado — agora pode editar
arquivos e rodar comandos nesta pasta.")`.

---

## 9. Responsividade e mobile

### UX-30 — Workbench inacessível em mobile

**Problema**: o painel workbench (Files/Diff/Plan) está em layout desktop
(coluna lateral). Em telas < 768px, está oculto ou inacessível.

**Correção**: em mobile, workbench vira bottom sheet (drawer) deslizável
para cima. Aba de tabs fica no bottom nav. Mesmo conteúdo, layout diferente.

---

### UX-31 — Input do chat em mobile

**Problemas**:

- Teclado virtual empurra o layout de maneiras inconsistentes.
- `@mention` popup não cabe na tela com teclado aberto.
- Botões de attach/voice ficam fora da área tocável.

**Correção**: usar `visualViewport` API para detectar área real disponível
com teclado virtual e ajustar o bottom padding dinamicamente.

---

## 10. Multimodal input (áudio, paste, drop, captura)

> Já existe `chat/lib/hooks/files/use-voice-input.ts` (Web Speech API
> com push-to-talk não-contínuo, `interimResults`, mapping de erros
> em pt-BR-friendly, idioma via `lang` prop). Esta seção mapeia o que
> falta integrar e estender.

### UX-32 — STT (speech-to-text) production-ready

**Estado atual**: o hook `useVoiceInput` existe e é correto. Cobre
Chrome/Edge desktop e Android. **Não cobre** Safari macOS/iOS sem
extensão, Firefox por default (precisa flag), nem ambientes offline /
self-hosted onde o user não quer enviar áudio para servidor da Google
(Web Speech API roteia para Google em Chrome).

**Lacunas a fechar**:

- **Integração visível no chat-input**: botão de microfone ao lado do
  send. Estado visual: idle (mic cinza), listening (mic vermelho +
  pulse + `interimTranscript` em itálico no input), error (mic com
  badge + toast UX-7).
- **Idioma sincronizado com Settings → Idioma** (`useT().lang` → BCP-47:
  `pt-BR`, `en-US`, `es-ES`). Não hardcoded `en-US` no caller.
- **Fallback remoto** quando `isSupported === false`:
  - Provider primário: gravação local via `MediaRecorder` → upload para
    `POST /v1/audio/transcribe` (endpoint novo no Bloco J) → backend
    chama Cohere/OpenAI Whisper conforme `effective_env` do user.
  - Indicação clara "modo nuvem" vs "modo browser local" no tooltip.
- **Push-to-talk vs continuous**: toggle em Settings → Preferências →
  Voz. Push-to-talk = hold space para falar (padrão Discord); continuous
  = clica uma vez, fala, clica de novo (padrão atual).
- **VAD (voice activity detection)**: stop automático quando o user
  para de falar por 2 s — evita "comeu o silêncio" do final.
- **i18n de erros** — `useVoiceInput` ainda retorna mensagens em inglês
  (`"No speech detected. Please try again."`). Mover para
  `strings.csv.ts` `voice.error.*`.

### UX-33 — TTS (text-to-speech) opcional

**O que é**: botão "🔊 Ouvir" em cada mensagem do agente. Lê em voz
alta usando `SpeechSynthesisUtterance` (Web Speech API output, sem
custo, presente em todos os browsers modernos). Provider remoto opcional
(Cohere/OpenAI) para qualidade superior — controla via Settings.

**Casos de uso**: acessibilidade (visão reduzida), uso hands-free
durante outras tarefas, revisão de respostas longas. Skip de
code-blocks ao falar (não ler caractere por caractere).

**Pause/resume/cancel** durante a leitura. Lê com voz do idioma da
mensagem (autodetect via primeiros chars ou metadata da resposta).

### UX-34 — Smart paste

**Hoje**: paste de texto grande vira `pasted-<ts>.txt` (já implementado,
Bloco A4). Falta inteligência por tipo de conteúdo:

- **URL**: detecta padrão; opcionalmente busca `<title>` + OG image via
  `GET /v1/web/preview?url=...` e renderiza card ao invés do bare URL.
  Toggle "expandir como card" no Settings.
- **Código com língua detectável**: detecta lang via `highlight.js
auto` ou heurística simples (regex de `def `, `function `, `class `,
  `<html`); insere como bloco markdown `` `lang` `` ao invés de
  texto plano.
- **Imagem do clipboard** (`navigator.clipboard.read`): vira anexo
  com preview thumbnail no input antes de enviar — confirma com o user
  ("Anexar como imagem?").
- **JSON / YAML grande**: prompt "formatar e anexar como arquivo?"
  evita poluir o input.

### UX-35 — Drop zone rico

**Hoje**: drag-and-drop existe no input (Bloco A4) com indicação
visual. Faltam previews ricos:

- **Imagem**: thumbnail 80×80 no input chip antes de enviar; dimensões
  no tooltip.
- **PDF**: thumbnail da página 1 (via `pdf.js` client-side) + contador
  "12 páginas, 1.2 MB".
- **Pasta inteira** (`webkitGetAsEntry`): "Adicionar 47 arquivos da
  pasta src/" → indexar como RAG (UX flow já existe via slash command
  `/rag add`).
- **Vídeo / áudio**: chip com duração + thumbnail do primeiro frame.

### UX-36 — Screenshot capture (Electron)

**O que é**: botão "📸 Anexar screenshot" no plus-menu (só visível
no desktop Electron). Usa `desktopCapturer` para listar telas/janelas;
user escolhe; screenshot vira anexo de imagem.

**Casos de uso**: debugging UI ("o que tem de errado nesta tela?"),
revisão de design, reprodução de bugs. Substitui o ciclo
"print screen → salvar → arrastar".

**Backend**: nenhum endpoint novo — screenshot é multimodal image, já
roteado para LLMs com visão (Gemini, GPT-4o, Claude 4).

---

## 11. Wizards e first-run

### UX-37 — First-run wizard pós-signup (root)

**Estado atual**: após signup root, o user cai direto no chat sem
contexto. Aba "Administração" tem os campos, mas a primeira coisa que
aparece é "Crie sua primeira conversa" — sem token, sem provider, sem
RAG configurado. Mensagem inicial falha com erro críptico ("nenhum
modelo disponível").

**Wizard proposto** (Bloco K8 do `plan.md` — formalizar aqui o fluxo
visual):

```
Passo 1 / 4 — Sua licença Vectora
  ┌──────────────────────────────────────────────────────────┐
  │ Cole seu VECTORA_TOKEN                                    │
  │ [vct_........................................]   [Validar]│
  │                                                            │
  │ Sem token? Funciona em modo trial por 30 dias.            │
  │ [Continuar sem token →]                                    │
  └──────────────────────────────────────────────────────────┘

Passo 2 / 4 — Provedor de IA principal
  ◉ Google Gemini       (recomendado — barato + multimodal)
  ○ OpenAI              (GPT-5.x)
  ○ Anthropic           (Claude 4.x)
  ○ Cohere              (Command R+)
  ○ Ollama local        (avançado — exige hardware)

  API Key: [........................]   [Testar conexão]

Passo 3 / 4 — Cohere (RAG)
  Cohere alimenta o RAG (embeddings + reranking). Obrigatório.
  API Key: [........................]   [Testar conexão]
  [Pular — configurar depois]   (RAG ficará desabilitado)

Passo 4 / 4 — Primeiro workspace
  Onde fica seu projeto principal?
  [📁 Selecionar pasta]    Ou pule e crie depois.
  ☑ Inicializar git nesta pasta (se ainda não for repo)
  ☑ Confiar nesta pasta (libera escrita e terminal)

  [← Voltar]                                  [Concluir →]
```

**Storage**: flag `vectora:onboarding-done-<userId>` em `localStorage`.
Skip mostra banner laranja permanente até completar.

**i18n**: todas as strings via `useT()` em `wizard.*`.

### UX-38 — Empty-state evoluído com prompts sugeridos

**O que é**: na primeira thread (sem mensagens), substituir o input
nu por uma tela de exemplos clicáveis baseados no workspace ativo:

```
O que posso fazer pelo seu projeto?

  💻 Detectei FastAPI + Vite. Posso:
     [Explicar a arquitetura]
     [Revisar o último commit]
     [Adicionar testes para src/api/handlers/]

  📚 Adicione documentação ao RAG:
     [Indexar pasta docs/]

  ✨ Ou comece do zero:
     [Texto livre…]
```

**Detecção de stack**: analisar `package.json`, `pyproject.toml`,
`go.mod`, etc. via `GET /workspaces/{id}/stack-hint` (endpoint novo,
~100 LOC backend).

**Atalhos clicáveis** preenchem o input (não enviam direto — user
revisa antes de mandar).

### UX-39 — Feature discovery passive

**O que é**: detectar features importantes que o user ainda não usou e
mostrar banner não-intrusivo no momento certo:

- "Você sabia que pode arrastar pastas para o chat para indexar RAG?"
  (mostra na 3ª mensagem do user, se RAG estiver vazio).
- "Ative o painel de arquivos com ⌃⇧E" (mostra quando user pede ao
  agente para listar arquivos pela 2ª vez).
- "Workspaces remotos? Conecte ao VPS via SSH" (mostra a usuários com
  apenas 1 workspace local após 7 dias).

**Storage**: `localStorage.vectora:tips-seen` (Set de IDs). Cada tip
aparece no máximo 1 vez. Botão "Não mostrar dicas" desliga global.

### UX-40 — Backup/restore wizard (re-instalação)

**O que é**: ao detectar `~/.vectora/` populado mas com configuração
incompatível (ex: schema migrations pendentes, ou versão major mudou),
modal pergunta:

- "Detectamos instalação anterior. Quer importar workspaces, threads,
  memórias?"
- Backup automático antes de migrar.
- Lista visual do que será importado (workspaces, threads, memory items,
  envs, plugins, skills).

Conecta com `vectora backup create/restore` do Bloco M6.

---

## 12. Visibilidade do agente (transparência)

### UX-41 — Activity panel: timeline persistente da thread

**Problema**: tool calls aparecem inline na mensagem do agente, mas
ficam soterradas em respostas longas. Não há visão consolidada do que
o agente fez nesta thread.

**Solução**: nova aba no Workbench "Activity" — timeline cronológica
de todos os tool calls da thread atual com filtros (tipo, status,
arquivo). Click no item → scroll para a mensagem que o originou.

**Backend**: `GET /threads/{id}/activity` retorna lista de
`{tool_name, args_summary, status, duration_ms, timestamp,
message_id}`. Reusa o tracer SQLite (`VectoraTracer` do Bloco A8).

### UX-42 — RAG provenance (citações [1][2])

**Problema**: quando o agente responde com base em RAG, o user não sabe
de onde veio cada afirmação. "O sistema usa SQLite" pode vir de docs,
de inferência, ou de alucinação.

**Solução**:

- Backend injeta no contexto markers `[doc:abc123]` referenciando
  chunks recuperados.
- Adapter de resposta substitui pelos numéricos `[1][2]…` + tabela de
  fontes ao final.
- Frontend renderiza `[1]` como link clicável que abre popover com:
  trecho do chunk, path do arquivo (ou URL web), score do reranker.

**Por que importa**: confiança verificável. Sem isso, o user precisa
confiar cegamente no agente — anti-padrão para RAG.

### UX-43 — "Por que isso?" — explicar decisão de routing

**Problema**: o orchestrator decide se delega para `coder`, `search`,
`rag` ou responde direto. O `ThinkingEvent` (A3) carrega o motivo, mas
o frontend só mostra "thinking…" colapsado.

**Solução**:

- Expandir o bloco de thinking para mostrar: ação escolhida, alternativas
  consideradas, justificativa de uma linha.
- Modo "dev" (Settings → Avançado): mostra prompt completo enviado ao
  modelo, função de routing chamada, scores quando aplicável.

### UX-44 — Mapa de arquivos tocados na thread

**O que é**: ao final da thread (ou em aba dedicada), treemap visual
dos paths que foram lidos/escritos/executados:

```
src/  (8 arquivos)
├─ api/handlers/  (3 ✏)
│  ├─ chat.py       — lido, editado, +12 / -3
│  ├─ workspaces.py — lido, editado, +25 / -8
│  └─ admin.py      — lido apenas
└─ ...
```

Cores: cinza (lido), azul (editado), vermelho (deletado), verde
(criado). Métrica + diff inline.

### UX-45 — Memory loaded chip + "esquecer isso"

**Hoje** (Bloco C1): badge "🧠 N memórias carregadas" por mensagem.
Falta:

- Click no badge → popover lista as memórias específicas que entraram
  no contexto desta resposta.
- Cada item com botão "🗑 Esquecer esta memória" → `DELETE
/memory/{id}` + toast confirmando.
- Toggle "ignorar memórias nesta thread" — útil para teste ad-hoc sem
  apagar permanente.

### UX-46 — Cost preview no model picker

**Problema**: trocar de modelo no dropdown não mostra impacto de custo.
User escolhe `gpt-5.5-pro` por curiosidade e queima orçamento.

**Solução**:

- Cada modelo no picker mostra: `$0.003/1k in · $0.012/1k out · context
1M tokens`.
- Estimativa para a mensagem atual: `~ $0.04 com este modelo` baseado
  em tokens já no contexto + estimativa de resposta.
- Cor verde (barato), amarelo (médio), vermelho (caro) por badge.
- Fonte de preços: tabela estática versionada (`chat/lib/config/model-
prices.ts`), atualizada manualmente — preços de LLM mudam ~trimestral.

### UX-47 — Tool palette descoberta

**O que é**: aba "Tools" no Settings (read-only para member, editável
para admin via tool_policy) lista **todas as tools** disponíveis com:

- Nome + descrição + categoria + ícone (já existe metadata).
- Estado: habilitada / desabilitada para este user.
- Exemplo de uso: snippet do schema esperado.
- Histórico: "usada N vezes nas últimas 7 dias".

Resolve a pergunta "o que esse agente sabe fazer?" — hoje só
descoberta empírica.

---

## 13. Command palette e descoberta de features

### UX-48 — Command palette global `⌘K`

**Problema**: slash commands (`/rag`, `/clone`, etc — Bloco B4)
funcionam só no chat. Navegação entre threads, abertura de Settings,
troca de workspace exigem cliques.

**Solução**: paleta `⌘K`/`⌃K` global no estilo
Linear/Slack/VS Code Command Palette. Categorias:

- **Threads**: fuzzy search por título; Enter abre.
- **Workspaces**: lista + ações (trust, switch, criar).
- **Settings**: abre tab direto (`Settings → Idioma`).
- **Tools**: ações imediatas (`Reindexar workspace`, `Nova worktree`).
- **Comandos do agente**: traduz para mensagem no input
  (`Refatorar último arquivo tocado`).

Atalho `?` dentro da palette → cheatsheet (UX-49).

### UX-49 — Cheatsheet de atalhos `⌘?`

**O que é**: modal navegável com todos os atalhos categorizados.
Buscável (`?` filtra). Atalhos customizáveis (UX-49a, futuro).

Gerado **automaticamente** a partir do `use-global-shortcuts.ts`
(UX-12) — não pode ficar dessincronizado com a implementação. Cada
atalho registra `{keys, label, scope, action}` num registry, e o modal
itera.

### UX-50 — Help contextual `?` flutuante

**O que é**: botão `?` discreto no canto inferior direito da view atual.
Click abre painel lateral com docs da view ativa (`/files`, `/diff`,
`/settings/admin`, etc.). Conteúdo vem de `docs.vectora.company` via
fetch + cache (offline-friendly via service worker).

Reduz a fricção de "preciso abrir outra aba para saber como funciona".

---

## 14. Custo, quotas e transparência de modelo

### UX-51 — Quota gauge visível

**Hoje**: usage popover existe (Bloco A7, 5h + semanal + contexto).
Falta:

- Gauge no header — não só popover. Cor fade verde → amarelo (60%)
  → vermelho (85%).
- Reset countdown: "renova em 2h 14min".
- Pre-warning antes de bloquear: aos 95% → toast "Quase no limite —
  considere upgrade ou aguarde a renovação".

### UX-52 — Custo acumulado por thread

**O que é**: ao final de cada mensagem do agente, badge sutil
`$0.03 · 1.4k tokens · 2.3 s`. Hover expande:

- Breakdown: input / output / cached tokens.
- Modelo usado.
- Tool calls que consumiram tokens próprios (RAG embedding, web search
  reranker).
- Custo acumulado da thread inteira no rodapé.

Cobertura crítica para Pro (multi-user) — admin precisa ver custo por
user/thread/workspace para alocação.

### UX-53 — Insight semanal de uso

**O que é**: notificação semanal opt-in (`Settings → Avançado →
Insights`) com resumo:

- "Você usou 1.2M tokens essa semana (+12% vs semana passada)".
- "Top 3 tools: file_edit (340), git_status (180), rag_search (95)".
- "Modelo mais usado: gemini-2.5-flash (78% das mensagens)".
- "Custo estimado: $4.30" (Pro).

Email via Resend (Bloco O4) ou só in-app card.

---

## 15. Notificações

### UX-54 — Notificação OS quando resposta longa termina

**Problema**: respostas longas (research deep, refactor grande, RAG
ingest) demoram 1–5 min. O user troca de tab, esquece, volta tarde.

**Solução** (Electron + Notification API no web):

- Se a resposta demorar > 15 s **e** a aba do chat não estiver visível
  (`document.visibilityState === "hidden"`): permission prompt + ao
  terminar dispara notificação OS clicável.
- Click → foca a janela + scroll para a mensagem.
- Settings → Preferências → "Notificar quando resposta termina"
  (default ligado, threshold configurável).

### UX-55 — Badge counters (sidebar + tray)

**O que é**: contadores numéricos em:

- Thread na sidebar: número de mensagens novas desde última visita
  (multi-user — outro user pode estar conversando na thread
  compartilhada).
- Settings → Admin: badge vermelho se há updates de licença /
  storage health / users pendentes.
- Tray icon (Electron, Bloco D4): badge se há notificação pendente.

### UX-56 — Quiet hours

**O que é**: Settings → Preferências → "Não perturbar das 22h às 8h".
Suprime notificações OS no intervalo. Útil para Pro multi-user com
agente trabalhando overnight.

---

## 16. Internacionalização e formatos locais

### UX-57 — Auditoria de strings hardcoded

**Problema**: a Diretriz 2 do `plan.md` proíbe strings hardcoded, mas
não há CI gate. PRs novos podem reintroduzir. Auditoria mostra
candidatos em error messages do `useVoiceInput`, tooltips no
workbench, etc.

**Solução**:

- Script `pnpm --dir chat lint:i18n` que faz grep em `.tsx`/`.ts` por
  string literals em JSX text nodes, `aria-label`, `placeholder`,
  `title` props que **não** vêm de `useT()`. Allow-list para nomes
  técnicos (`MCP`, `RAG`, `⌃⇧F`).
- Hook pre-commit + CI.

### UX-58 — Formato de data/hora/número por locale

**Problema**: hoje muitos timestamps usam `Date.toLocaleString()` sem
locale explícito — pega `navigator.language`, que pode divergir do
`useT().lang`. User pt-BR no Chrome en-US vê "11/3/2026" quando
deveria ver "03/11/2026".

**Solução**: helper `formatDate(date, { locale: useT().lang })` que
sempre passa locale explícito. `formatNumber`, `formatCurrency`
(para Pro) idem.

### UX-59 — RTL ready (futuro)

**O que é**: garantir que componentes não assumem direção LTR (sem
`margin-left` quando deveria ser `margin-inline-start`). Tailwind 4
suporta `ms-*`/`me-*` lógicos. Trabalho gradual; preparar quando
adicionar árabe/hebraico ao i18n.

---

## 17. Polish mobile, gestos e a11y avançada

### UX-60 — `prefers-reduced-motion` completo

**Problema**: animações de mensagem, sidebar slide, fade do skeleton
podem causar náusea em usuários sensíveis. Hoje cobertura parcial.

**Solução**: auditar todas as `transition-*` e `animate-*` do Tailwind;
envolver em `motion-safe:`. Usar `useReducedMotion()` (hook custom ou
`framer-motion` se já estiver instalado) para desabilitar animações
JS-driven.

### UX-61 — Pull-to-refresh em mobile

**O que é**: gesto de puxar a lista de threads para baixo dispara
`hydrate()`. Padrão iOS/Android nativo, esperado pelos users.

Implementação: `touchstart`/`touchmove`/`touchend` no container da
sidebar com threshold de 80 px + indicador visual.

### UX-62 — Long-press para ações contextuais

**Hoje**: ações de thread (renomear, deletar, exportar) ficam no menu
"⋯". Em mobile, long-press deveria abrir bottom-sheet com as mesmas
ações — padrão iOS.

### UX-63 — Safe-area inset (iOS notch)

**Problema**: em iPhone com notch/Dynamic Island, o header é cortado.
Falta `env(safe-area-inset-top)` / `bottom` nos paddings do app shell.

**Solução**: adicionar utilitários Tailwind 4 `pt-safe`/`pb-safe` no
`AppShell`. PWA standalone (manifest já tem) precisa disso.

### UX-64 — Send feedback inline

**O que é**: botão "🐛 Feedback" no header user-menu. Modal com:

- Categoria (bug / sugestão / dúvida).
- Texto.
- Anexo opcional: screenshot via `desktopCapturer` (Electron) ou
  upload (web).
- Inclui automaticamente: versão, browser/OS, último erro do console,
  thread_id ativa.
- Enviado para `vectora-company/issues` via webhook (Bloco P6) ou
  email `support@`.

### UX-65 — Resume conversation entre devices (Pro)

**O que é**: indicador "você estava aqui no Mac há 2 min" ao abrir o
chat no celular. Aproveita backend multi-device (Pro tem multi-thread
nativo).

Implementação: `last_active_at` por `(user, device_fingerprint, thread)`.
Banner aparece se outro device deixou a mesma thread aberta < 5 min
atrás.

---

## 10b. Priorização

> Numeração da seção mantida para compatibilidade com referências
> cruzadas — a seção é a **antiga §10**, expandida com os itens
> UX-32–UX-65 das seções novas (10–17 acima).

| #     | Feature                                        | Impacto | Esforço | Prioridade |
| ----- | ---------------------------------------------- | ------- | ------- | ---------- |
| UX-7  | Sistema de toast centralizado                  | Alto    | Pequeno | **P1**     |
| UX-15 | Reconexão SSE com indicador visual             | Alto    | Pequeno | **P1**     |
| UX-19 | Fix FOUC de auth (rehydrate await)             | Alto    | Pequeno | **P1**     |
| UX-1  | Flash of Workspaces (hydrated flag + skeleton) | Alto    | Pequeno | **P1**     |
| UX-9  | Skeleton screens (thread, files, diff)         | Alto    | Médio   | **P1**     |
| UX-24 | Streaming UX (cursor piscante, tool progress)  | Alto    | Médio   | **P1**     |
| UX-26 | HITL modal com contexto + diff preview         | Alto    | Médio   | **P1**     |
| UX-11 | Estados de erro persistentes + retry button    | Alto    | Pequeno | **P2**     |
| UX-16 | Detecção de offline + banner                   | Médio   | Pequeno | **P2**     |
| UX-20 | Recuperar contexto após expiração de sessão    | Alto    | Médio   | **P2**     |
| UX-2  | TTL / auto-invalidação nos stores              | Médio   | Médio   | **P2**     |
| UX-12 | Mapa de atalhos completo + hook centralizado   | Médio   | Médio   | **P2**     |
| UX-8  | Loading states por operação (não global)       | Médio   | Médio   | **P2**     |
| UX-22 | TTI da thread (prefetch + paralelismo)         | Médio   | Médio   | **P2**     |
| UX-3  | GC de mensagens antigas no threads-store       | Médio   | Médio   | **P3**     |
| UX-13 | Foco/tab order + focus trap em modais          | Médio   | Médio   | **P3**     |
| UX-17 | Retry com back-off exponencial                 | Médio   | Pequeno | **P3**     |
| UX-6  | BroadcastChannel multi-tab                     | Médio   | Pequeno | **P3**     |
| UX-5  | Immer middleware nos stores                    | Médio   | Pequeno | **P3**     |
| UX-18 | Streaming interrompido → badge + retry         | Médio   | Médio   | **P3**     |
| UX-25 | Indicador de uso de contexto                   | Médio   | Médio   | **P3**     |
| UX-10 | Erros inline nos formulários (tipagem ok/fail) | Médio   | Médio   | **P3**     |
| UX-28 | Empty states com call to action                | Médio   | Pequeno | **P3**     |
| UX-23 | Virtualização MessageList                      | Médio   | Médio   | **P4**     |
| UX-14 | ARIA completo (tree, live, busy)               | Médio   | Médio   | **P4**     |
| UX-21 | Aviso de sessão prestes a expirar              | Médio   | Pequeno | **P4**     |
| UX-27 | Histórico e gerenciamento de regras HITL       | Baixo   | Médio   | **P4**     |
| UX-4  | new-thread-registry cleanup                    | Baixo   | Pequeno | **P4**     |
| UX-29 | Onboarding de workspace não-confiável          | Baixo   | Pequeno | **P4**     |
| UX-30 | Workbench mobile (bottom sheet)                | Baixo   | Grande  | **P5**     |
| UX-31 | Input do chat em mobile (visualViewport)       | Baixo   | Médio   | **P5**     |

**Extensão — UX-32 a UX-65** (seções 10–17):

| #     | Feature                                      | Impacto | Esforço | Prioridade |
| ----- | -------------------------------------------- | ------- | ------- | ---------- |
| UX-37 | First-run wizard pós-signup root             | Crítico | Médio   | **P1**     |
| UX-42 | RAG provenance — citações [1][2] com popover | Alto    | Médio   | **P1**     |
| UX-32 | STT integrado ao chat-input (button + i18n)  | Alto    | Pequeno | **P1**     |
| UX-46 | Cost preview no model picker                 | Alto    | Pequeno | **P2**     |
| UX-41 | Activity panel: timeline persistente         | Alto    | Médio   | **P2**     |
| UX-38 | Empty-state com prompts sugeridos por stack  | Alto    | Médio   | **P2**     |
| UX-51 | Quota gauge visível no header                | Médio   | Pequeno | **P2**     |
| UX-52 | Custo acumulado por thread (badge)           | Médio   | Médio   | **P2**     |
| UX-48 | Command palette ⌘K global                    | Alto    | Médio   | **P2**     |
| UX-43 | "Por que isso?" — explicar routing           | Médio   | Médio   | **P3**     |
| UX-45 | Memory loaded chip + "esquecer isso"         | Médio   | Pequeno | **P3**     |
| UX-34 | Smart paste (URL/código/imagem)              | Médio   | Médio   | **P3**     |
| UX-35 | Drop zone rico (thumbnails, PDF, vídeo)      | Médio   | Médio   | **P3**     |
| UX-54 | Notificação OS ao terminar resposta longa    | Médio   | Pequeno | **P3**     |
| UX-49 | Cheatsheet de atalhos ⌘? gerado do registry  | Médio   | Pequeno | **P3**     |
| UX-50 | Help contextual `?` flutuante                | Médio   | Médio   | **P3**     |
| UX-39 | Feature discovery passive ("você sabia…")    | Médio   | Médio   | **P3**     |
| UX-57 | Auditoria de strings hardcoded (CI gate)     | Médio   | Médio   | **P3**     |
| UX-44 | Mapa de arquivos tocados (treemap)           | Médio   | Médio   | **P4**     |
| UX-33 | TTS opcional (read aloud)                    | Baixo   | Pequeno | **P4**     |
| UX-36 | Screenshot capture (Electron)                | Médio   | Pequeno | **P4**     |
| UX-47 | Tool palette descoberta                      | Médio   | Pequeno | **P4**     |
| UX-55 | Badge counters (sidebar + tray)              | Médio   | Pequeno | **P4**     |
| UX-58 | Formato de data/hora/número por locale       | Baixo   | Pequeno | **P4**     |
| UX-60 | `prefers-reduced-motion` completo            | Médio   | Pequeno | **P4**     |
| UX-64 | Send feedback inline com screenshot          | Médio   | Médio   | **P4**     |
| UX-40 | Backup/restore wizard ao re-instalar         | Médio   | Médio   | **P5**     |
| UX-53 | Insight semanal de uso (email/in-app)        | Baixo   | Médio   | **P5**     |
| UX-56 | Quiet hours                                  | Baixo   | Pequeno | **P5**     |
| UX-61 | Pull-to-refresh em mobile                    | Baixo   | Pequeno | **P5**     |
| UX-62 | Long-press → bottom-sheet em mobile          | Baixo   | Médio   | **P5**     |
| UX-63 | Safe-area inset iOS notch                    | Baixo   | Pequeno | **P5**     |
| UX-65 | Resume conversation entre devices            | Médio   | Médio   | **P5**     |
| UX-59 | RTL ready (gradual)                          | Baixo   | Grande  | **P5**     |

---

## 11. Sequência de implementação recomendada

```
Sprint UX-1 — Feedback e estado (1 semana)
  UX-7    sistema de toast (Sonner ou Radix Toast)
  UX-11   estados de erro + retry button em todos os stores
  UX-1    hydrated flag + WorkspacesSkeleton
  UX-9    skeletons: ThreadList, FileTree, DiffTab
  UX-8    loading states por operação

Sprint UX-2 — Resiliência de rede (1 semana)
  UX-15   SSE reconexão + badge de status
  UX-16   detecção offline + banner
  UX-17   retry com back-off nos fetchJson não-destrutivos
  UX-18   streaming interrompido → badge + retry

Sprint UX-3 — Auth e sessão (1 semana)
  UX-19   fix FOUC de auth (await rehydrate)
  UX-20   salvar contexto antes de redirect de 401
  UX-21   aviso de sessão prestes a expirar

Sprint UX-4 — Streaming e percepção (1 semana)
  UX-24   streaming UX (cursor, tool progress, botão copiar)
  UX-22   TTI: prefetch + paralelismo de carregamento
  UX-25   indicador de uso de contexto

Sprint UX-5 — HITL e atalhos (1 semana)
  UX-26   HITL modal com diff preview + reasoning
  UX-12   atalhos globais centralizados em use-global-shortcuts.ts
  UX-13   focus trap + tabindex + botões visíveis no teclado
  UX-28   empty states com call to action

Sprint UX-6 — Store hygiene (1 semana)
  UX-2    TTL / auto-invalidação
  UX-3    GC de mensagens no threads-store
  UX-5    Immer middleware
  UX-6    BroadcastChannel multi-tab
  UX-4    new-thread-registry cleanup
  UX-10   erros inline tipados nos formulários

Sprint UX-7 — Acessibilidade (1 semana)
  UX-14   ARIA completo (tree, live, busy, labels)
  UX-23   virtualização MessageList com @tanstack/react-virtual

Sprint UX-8 — Mobile (2 semanas, gate: demanda real)
  UX-30   workbench como bottom sheet em mobile
  UX-31   input do chat com visualViewport
  UX-61   pull-to-refresh
  UX-62   long-press bottom-sheet
  UX-63   safe-area inset iOS

Sprint UX-9 — Onboarding e transparência (1 semana — bloqueia lançamento)
  UX-37   first-run wizard pós-signup root
  UX-38   empty-state com prompts sugeridos por stack
  UX-42   RAG provenance (citações [1][2])
  UX-32   STT integrado ao chat-input + i18n de erros

Sprint UX-10 — Custo & comando (1 semana)
  UX-46   cost preview no model picker
  UX-51   quota gauge visível
  UX-52   custo acumulado por thread
  UX-48   command palette ⌘K
  UX-49   cheatsheet ⌘? gerada do registry

Sprint UX-11 — Visibilidade do agente (1–2 semanas)
  UX-41   activity panel timeline
  UX-43   "por que isso?" explica routing
  UX-45   memory loaded chip + esquecer
  UX-44   mapa de arquivos tocados
  UX-47   tool palette descoberta

Sprint UX-12 — Multimodal & notificações (1 semana)
  UX-34   smart paste
  UX-35   drop zone rico
  UX-36   screenshot capture Electron
  UX-54   notificação OS resposta longa
  UX-55   badge counters
  UX-33   TTS opcional

Sprint UX-13 — Polish institucional (1 semana)
  UX-39   feature discovery passive
  UX-50   help contextual `?` flutuante
  UX-57   auditoria strings hardcoded + CI gate
  UX-58   formato data/hora/número por locale
  UX-60   prefers-reduced-motion completo
  UX-64   send feedback inline com screenshot

Sprint UX-14 — Backup & insights (opcional, pós-1.0)
  UX-40   backup/restore wizard
  UX-53   insight semanal
  UX-56   quiet hours
  UX-65   resume conversation entre devices
  UX-59   RTL ready (preparação gradual)
```

---

## 12. Notas de arquitetura

### O toast como canal único de feedback

Toda falha de ação do usuário deve chegar ao toast store. O padrão correto:

```typescript
// Em qualquer store:
const result = await fetchJson("/workspaces/create", { ... });
if (!result) {
  useToastStore.getState().push({
    type: "error",
    title: "Falha ao criar workspace",
  });
  return null;
}
```

O objetivo é que **nenhum `return null`** seja silencioso para o usuário.

### Skeleton é um contrato de UX, não decoração

O skeleton screen define a forma esperada do conteúdo. Se o layout do
conteúdo real mudar (ex: novo campo na thread), o skeleton deve ser
atualizado junto. Trate como parte da API de componente.

### Estados de loading são máquinas de estado, não booleans

```
idle → loading → (success | error) → idle
```

Nunca representar esse ciclo com `loading: boolean` + `error: string | null`
separados — eles podem ficar out-of-sync. Usar discriminated union:

```typescript
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; message: string };
```

### SSE como sistema nervoso central

O SSE de streaming do chat é o canal mais crítico do Vectora. Toda
degradação de SSE deve ser visível ao usuário em < 3 s. O fluxo de
reconexão deve ser transparente (sem reload de página).

O SSE de workspace events (futuro — FS-12, FS-19) deve usar o mesmo
padrão de status de conexão.

### Hooks já existentes — não reinventar

Antes de criar hook novo, verificar `chat/lib/hooks/`:

| Hook                                         | O que faz                                |
| -------------------------------------------- | ---------------------------------------- |
| `use-hydrated.ts`                            | Gate de hidratação para `persist` stores |
| `workbench/use-swr.ts` (`useWorkbenchSWR`)   | Stale-while-revalidate genérico          |
| `files/use-voice-input.ts` (`useVoiceInput`) | STT Web Speech API                       |
| `auth/use-user-id.ts`                        | ID do user autenticado                   |
| `auth/use-client-profile.ts`                 | Perfil do user                           |
| `chat/use-stream-handler.ts`                 | Roteador de eventos SSE                  |
| `chat/use-feedback.ts`                       | Submissão de feedback                    |
| `chat/use-thread-messages.ts`                | Loader de histórico                      |
| `threads/use-threads.ts`                     | Lista de threads                         |
| `files/use-file-upload.ts`                   | Upload de anexos                         |
| `use-license-status.ts`                      | Status de licença                        |

Itens deste documento que criariam paralelos (UX-1, UX-2, UX-15
parcial, UX-32 parcial) devem **reusar** o existente. Reinventar é
dívida técnica + bug surface.

### STT como camada com fallback

`useVoiceInput` cobre 70% dos browsers. O resto exige fallback remoto:

```
input do user
    │
    ├─ isSupported? → useVoiceInput (Web Speech)
    │                      │
    │                      └─ network/aborted → fallback ↓
    │
    └─ MediaRecorder local → POST /v1/audio/transcribe
                                    │
                                    ├─ Cohere ASR (default)
                                    ├─ OpenAI Whisper (fallback)
                                    └─ Local Whisper.cpp (futuro, sandbox)
```

Decisão de provider remoto via `effective_env` do user (mesmo padrão
de LLM). Sem provider configurado + Web Speech indisponível → desabilitar
botão de mic com tooltip explicativo.

### Wizards como state machines

Wizards multi-step (UX-37, UX-40) NÃO devem ser implementados como
sequência de `useState` espalhados. Modelar como XState ou reducer
discriminado:

```typescript
type WizardState =
  | { step: "token"; tokenInput: string; tokenError: string | null }
  | { step: "provider"; provider: ProviderId; apiKey: string; testing: boolean }
  | { step: "cohere"; apiKey: string; testing: boolean }
  | { step: "workspace"; path: string; gitInit: boolean; trust: boolean }
  | { step: "done" };
```

Permite back/forward sem perder dados, validação por step, persistência
do progresso em sessionStorage (se user fechar a aba no meio).

### Provenance como marker no streaming

UX-42 (citações RAG) **não** deve ser implementado como post-processing
client-side parseando `[doc:abc]` da string final. O backend já emite
`ToolCallEvent` com `name=rag_search` e o resultado contém os chunks.

Caminho correto:

1. Backend instrumenta `inject_context_into_prompt()` para mapear
   chunks → IDs sequenciais por thread e enviar `RagCitationEvent`
   `{citation_id, chunk_id, score, source_path, source_url, excerpt}`.
2. LLM gera resposta com markers `[1][2]` (instrução no system prompt).
3. Frontend renderiza markers como `<sup>` clicável que abre popover
   com o `RagCitationEvent` já cacheado.

Sem post-processing de string — schema-first, conforme princípio 6 do
plan mestre.

### Empty state ≠ tela vazia

Toda view do produto tem 3 estados de vazio que precisam ser
explicitamente desenhados (UX-28, UX-38):

1. **Vazio temporário** (loading): skeleton shape do conteúdo
   esperado.
2. **Vazio funcional** (sem dados, mas user é novo): call to action
   contextual ("Crie seu primeiro workspace" + botão).
3. **Vazio erro** (falhou ao carregar): banner com `onRetry`.

Mostrar tela em branco em qualquer um dos 3 é bug, não estado válido.

### Visibilidade do agente é confiança

UX-26, UX-41, UX-42, UX-43, UX-44, UX-45 formam um cluster único:
**transparência operacional do agente**. Cada uma sozinha é
incremental; juntas mudam a relação do user com o agente de "caixa
preta que às vezes acerta" para "ferramenta auditável que erra
visivelmente".

Priorizar este cluster em conjunto. Lançar UX-41 sem UX-42 deixa o
activity panel descontextualizado; lançar UX-42 sem UX-45 sugere que
o agente "lembra mágica" sem que o user veja a mecânica.
