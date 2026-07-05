# Vectora — IDE Mode para todas as workbenches + Preview de verdade

> `ideMode` já existe (`frontend/lib/stores/settings-store.ts:107`,
> alternado por `components/header/ide-mode-switcher.tsx`), mas hoje é
> essencialmente um interruptor de **uma** workbench: a de arquivos
> (`files-tab.tsx`/`file-item.tsx`/`pinned-section.tsx`/`window-layer.tsx`)
> — quando ligado, arquivo abre docked em vez de em janela flutuante; as
> outras 7 workbenches (diff/git, plan, tasks, preview, storage,
> context_graph, terminal) não mudam nada quando o modo liga. Este
> documento generaliza `ideMode` pra ser um estado de layout que qualquer
> workbench pode reagir a, e detalha os dois casos concretos pedidos:
> **diff/git** (diff/commit completos, não só nomes de arquivo) e
> **preview** (barra de URL com path relativo, navegação, viewport
> mobile/desktop, e inspetor de elemento). O inspetor, especificamente,
> **força `ideMode` a ligar** se estiver desligado — não faz sentido
> inspecionar elemento num preview pequeno flutuante.
>
> Achado importante da pesquisa: o backend **já tem** endpoint de diff por
> arquivo e por commit prontos (`backend/api/handlers/workspaces.py:1007-
1426`) e o frontend **já** os consome — só que via clique pra expandir
> (`changes-view.tsx`/`history-view.tsx`), como texto puro colorido
> (`git/shared.tsx::HunkView`, um `<pre>` com verde/vermelho por linha, sem
> highlight de sintaxe, sem lado a lado). Isso não é "não existe", é
> "existe pouco" — o trabalho aqui é upgrade de fidelidade + virar painel
> persistente de IDE mode, não construir do zero.

---

## 1. Panorama — `ideMode` de flag de uma aba pra estado de layout global

Hoje (`src/routes/session/$threadId.tsx:564`):

```tsx
{ideMode && !chatMode && enableFeaturesBeta ? (
  // ── Layout IDE: sidebars ao topo, Header só acima do DockedEditor ──
  ...
) : (
  // layout normal
)}
```

Isso já troca o **layout da página inteira** (sidebars pro topo, editor
docked) — a generalização não é inventar um conceito novo, é fazer as
outras workbenches **também perguntarem** `ideMode` e renderizarem uma
variante mais rica quando `true`, do mesmo jeito que `files-tab.tsx` já
faz. Convenção proposta pra todo tab novo:

```tsx
// dentro de cada *-tab.tsx
const ideMode = useSettingsStore((s) => s.ideMode);

return ideMode ? <DiffTabIde {...props} /> : <DiffTabCompact {...props} />;
```

`DiffTabCompact` é o componente atual (inalterado — usuários fora do beta
continuam vendo exatamente o que veem hoje); `*Ide` é o painel novo. Isso
mantém `enableFeaturesBeta` como guarda-chuva único de risco — nada de
feature flag por aba.

---

## 2. Git/Diff workbench — diff completo + view de commit completa

### 2.1 O que já existe (não refazer)

| Peça                                | Onde                                                                                                              | Estado                                    |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Diff resumo (arquivos + contadores) | `GET /workspaces/{id}/git/diff` (`workspaces.py:1007`)                                                            | ✅ pronto                                 |
| Hunks de 1 arquivo                  | `GET /workspaces/{id}/git/diff/file` (`workspaces.py:1107`)                                                       | ✅ pronto                                 |
| Diff completo de 1 commit           | `GET /workspaces/{id}/git/commit/diff` (`workspaces.py:1400`, `git show --unified=3 --stat`, truncado em 100 KiB) | ✅ pronto                                 |
| Render do hunk                      | `git/shared.tsx::HunkView` — `<pre>` colorido, sem highlight                                                      | ⚠️ funcional, baixa fidelidade            |
| Fluxo de acesso                     | clique no arquivo/commit expande inline                                                                           | ⚠️ funciona, mas não é "workbench de IDE" |

### 2.2 O que muda em IDE mode

**Painel dedicado, não mais expansão inline.** Em `ideMode`, a lista de
arquivos (`changes-view.tsx`)/commits (`history-view.tsx`) vira uma coluna
estreita à esquerda (mesmo papel de um explorer de arquivo) e clicar num
item **não expande a linha** — abre o diff docked na área principal, igual
a `DockedEditor` já faz pra arquivo (`components/workbench/windows/
docked-editor.tsx`). Reaproveita o **mesmo componente de docking** — a
"aba" de um diff é conceitualmente igual à aba de um arquivo aberto, só
que read-only e com conteúdo derivado (`git diff`), não um arquivo real em
disco.

```
DiffDockedPanel (novo, components/workbench/windows/diff-docked-panel.tsx)
  tab bar: [arquivo1.ts ×] [arquivo2.py ×] [commit a1b2c3 ×]
  conteúdo: <MonacoDiffEditor original={before} modified={after} language={...} />
```

### 2.3 Monaco Diff Editor em vez de `<pre>`

Monaco (`@monaco-editor/react`, já dependência do Vectora pro
`file-editor.tsx`) tem um modo de **diff editor nativo**
(`DiffEditor`/`editor.createDiffEditor`) — side-by-side ou inline, com
highlight de sintaxe pela linguagem do arquivo (mesma detecção de
linguagem por extensão já usada no editor normal), minimap, e navegação
"próxima mudança"/"mudança anterior" de fábrica. Isso substitui
`HunkView` no modo IDE (o modo compacto atual continua usando `HunkView` —
mais leve, sem custo do Monaco pra quem só quer ver rapidinho):

```tsx
import { DiffEditor } from "@monaco-editor/react";

<DiffEditor
  original={fileBeforeContent} // conteúdo do blob antigo (git show HEAD:path)
  modified={fileAfterContent} // conteúdo atual em disco
  language={detectLanguage(path)} // já existe em file-editor.tsx
  options={{ readOnly: true, renderSideBySide: true }}
/>;
```

**Gap de backend**: os endpoints hoje devolvem **hunks** (formato unified
diff — linhas com `+`/`-`/contexto), não os dois arquivos completos
(antes/depois) que o `DiffEditor` do Monaco espera. Precisa de um endpoint
novo (ou parâmetro novo no existente):

```
GET /workspaces/{id}/git/diff/file/full?path=X&ref=HEAD
  → { before: string | null, after: string }
```

`before` usa `git show {ref}:{path}` (`None` se o arquivo é novo/untracked
— `DiffEditor` trata `original=""` como "tudo é adição", mas `null` no
retorno da API é mais explícito pra distinguir "arquivo novo" de "arquivo
vazio"); `after` lê o arquivo do disco direto (mesma função já usada por
`file_read`, `backend/tools/fs.py`). Reaproveita `backend/tools/git.py`
pra resolver o blob antigo — é uma chamada de `git show`, mesma família de
subprocess que `_git_diff_impl` já faz.

### 2.4 View de commit completa (arquivos editados por commit)

`history-view.tsx` hoje mostra o diff do commit inteiro como um `<pre>`
só (`GET /git/commit/diff`, `git show --unified=3 --stat`). Em IDE mode,
isso vira uma **lista de arquivos afetados por aquele commit**, cada um
clicável pra abrir no `DiffDockedPanel` — mesma UX do "Mudanças", só que a
base de comparação é `{commit}^` vs `{commit}` em vez de `HEAD` vs disco.

Endpoint novo (ou variante do `/git/diff/file/full` acima com parâmetro
`ref` sendo o par de shas em vez de `HEAD`):

```
GET /workspaces/{id}/git/commit/{sha}/files
  → { files: [{ path, status: "M"|"A"|"D", additions, deletions }] }
```

É o `git show --stat --name-status {sha}` parseado — variação pequena do
parsing que `_parse_unified_diff()` (`workspaces.py:952`) já faz pro caso
de "Mudanças"; não é lógica nova, é o mesmo parser aplicado à saída de
`git show` em vez de `git diff`.

---

## 3. Preview workbench — de iframe cru pra dev tool de verdade

### 3.1 Problema de fundo: cross-origin

`preview-tab.tsx:213-217` hoje: `activeUrl = "http://localhost:{port}"` —
o iframe aponta **direto** pro processo do dev server do usuário, numa
porta diferente da origem do próprio Vectora. Isso é **cross-origin** pro
frame pai (a SPA do Vectora) — `iframe.contentDocument` é bloqueado pelo
browser (same-origin policy), então **nenhuma das features pedidas que
precisam olhar dentro da página** (inspetor de elemento, path da URL
relativo) funciona com a arquitetura atual, não importa quanto JS se
escreva no lado do Vectora.

### 3.2 Solução: reverse proxy same-origin pelo backend

Fazer o backend proxiar o dev server, servindo-o **sob a própria origem**
do Vectora — o iframe passa a apontar pra um path do próprio backend, não
pra `localhost:{port}` direto. Isso resolve os três problemas de uma vez
(cross-origin do inspetor, path relativo da URL bar, e dá de graça o
"clique num link interno continua dentro do preview" que hoje já
funciona por acidente, mas sem controle nenhum do lado do Vectora).

```
GET/POST/WS  /workspaces/{id}/preview/proxy/{path:path}
  → encaminha pra http://localhost:{port}/{path}
  → reescreve o header Host
  → devolve a resposta (streaming, sem bufferizar body — importante pra
    assets grandes e pra long-polling/SSE que o app do usuário use)
```

Router novo em `backend/api/handlers/workspaces.py` (mesmo arquivo dos
outros endpoints de preview, `2862-2990`). Implementação: `httpx.AsyncClient`
em modo stream pra HTTP normal; **WebSocket precisa de tratamento
separado** (HMR do Vite/webpack-dev-server roda em WS) — FastAPI aceita
upgrade de WebSocket nativamente
(`@view_router.websocket(...)`), então o proxy de WS é um segundo handler
que faz `websockets.connect()` pro dev server real e faz bridge
bidirecional das mensagens. **Isso é o item de maior risco técnico do
documento** — se o proxy de WS não for feito, o HMR do projeto do usuário
para de recarregar sozinho dentro do preview (ainda funciona com reload
manual, só perde o "salvei e já viu" instantâneo). Vale prototipar esse
pedaço isolado antes de plugar no resto.

Efeito colateral bom: como o iframe agora é same-origin, o sandbox do
iframe (`sandbox="allow-scripts allow-forms allow-modals allow-popups"`,
`preview-tab.tsx:456`) pode manter as mesmas flags — não precisa relaxar
segurança pra ganhar acesso ao DOM, o proxy resolve isso "de fora".

### 3.3 Barra de URL com path relativo (`/` = home)

Com o proxy, `iframe.src` inicial é
`/workspaces/{id}/preview/proxy/` (a raiz do dev server, mapeada como "/").
Como o iframe é same-origin agora, o componente pai lê
`iframe.contentWindow.location.pathname` diretamente (sem postMessage) e
faz `path.replace(`/workspaces/${id}/preview/proxy`, "") || "/"` pra
mostrar só a parte relevante na barra — exatamente o pedido ("se acessar
página interna fica `/nome-da-pagina`"). Navegação client-side (React
Router, etc. dentro do projeto do usuário) já dispara `popstate`/mudança
de `pathname` que um listener no elemento `iframe` (via polling curto ou
`MutationObserver` no título, já que `popstate` de dentro do iframe não
propaga automaticamente pro pai) consegue captar — polling leve (250ms) do
`pathname` é aceitável aqui, é um preview de dev, não um app de produção
sensível a esse custo.

Editar a barra e apertar Enter continua chamando
`iframe.contentWindow.location.href = novoPath` (funciona cross-origin
mesmo sem o proxy, já que setar `.location` de uma window é sempre
permitido — mas com o proxy o destino é relativo ao próprio prefixo, então
o componente monta a URL final concatenando o prefixo do proxy).

### 3.4 Voltar / Próximo / Reload

`history.back()`/`.forward()`/`.go(n)` de uma `Window` são acessíveis
**mesmo cross-origin** (excecão histórica da same-origin policy — sempre
foi assim, independe do proxy) — então os três botões são simplesmente:

```tsx
<button onClick={() => iframeRef.current?.contentWindow?.history.back()}>
<button onClick={() => iframeRef.current?.contentWindow?.history.forward()}>
<button onClick={() => setIframeKey((k) => k + 1)}>  {/* reload — já existe */}
```

Estado de "dá pra voltar?" (desabilitar o botão) não tem API padrão pra
isso em cross-window — solução prática: manter uma pilha própria de
navegação no lado do Vectora (dispara em cada mudança de `pathname`
detectada pelo polling do §3.3), sem depender de introspectar o histórico
real do iframe.

### 3.5 Viewport mobile/desktop

Sem servidor nenhum envolvido — é só CSS. Um toggle no header do preview
alterna a `width`/`height` do container do iframe entre 100% (desktop) e
um preset de celular (375×812, mesmo tamanho usado pelas prints do v0.dev
que o usuário mandou), com uma moldura visual simples (borda arredondada +
sombra) pra ficar claro que é o modo mobile. Nenhuma mudança de backend.

### 3.6 Inspetor de elemento

Com o proxy (§3.2), o iframe é same-origin — o componente pai acessa
`iframe.contentDocument` direto, sem precisar injetar script nenhum no
código do usuário (diferente de ferramentas que exigem um SDK client-side
— aqui o Vectora já está "dentro" via same-origin).

```
1. Usuário clica no botão de inspetor (ícone de mira, como nas prints).
2. Se ideMode === false → liga ideMode automaticamente (pedido explícito
   do usuário: "ao usar o inspector... deve mudar para o ide mode caso
   ainda não esteja").
3. Um listener de mousemove em iframe.contentDocument desenha um overlay
   (posição via getBoundingClientRect() do elemento sob o cursor,
   projetado pras coordenadas do iframe no documento pai).
4. Clique "trava" a seleção — abre o painel de inspeção (mesmo papel do
   painel direito nas prints do v0.dev: tag, classes, texto, tipografia
   computada via getComputedStyle).
```

Painel de inspeção é um novo componente dockado
(`components/workbench/preview/element-inspector-panel.tsx`), populando:
tag/id/classes do elemento, dimensões (`getBoundingClientRect`), estilos
computados relevantes (fonte, cor, espaçamento — subconjunto do que
`getComputedStyle` retorna, não o dump inteiro), e um botão "copiar
seletor CSS" (utilitário comum desse tipo de ferramenta, custo baixo de
implementar já tendo o elemento em mãos).

**Fora de escopo deste documento** (mas citado pra não perder o fio):
edição inline do elemento (mudar texto/cor e refletir de volta no código
fonte, como o v0.dev faz) — isso exige mapear DOM → linha de código fonte
(source maps ou instrumentação do bundler do usuário), é uma escada de
complexidade muito maior que "selecionar e inspecionar" pedido aqui.

---

## 4. Faseamento sugerido

1. Proxy same-origin do preview (§3.2) — é a base de tudo, sem ele nada
   do resto do preview funciona. Prototipar o proxy de WebSocket isolado
   primeiro (maior risco técnico).
2. Barra de URL com path relativo + voltar/próximo/reload (§3.3-3.4) —
   depende só do proxy, não do inspetor.
3. Viewport mobile/desktop (§3.5) — independente, pode entrar em paralelo
   com o passo 2.
4. Inspetor de elemento (§3.6) — depende do proxy (passo 1) e do `ideMode`
   generalizado (§1) pra auto-ligar o modo.
5. `ideMode` generalizado pro git/diff (§2.2) — independente do preview,
   pode ser feito em paralelo com os passos 1-4.
6. Endpoint `/git/diff/file/full` + `DiffDockedPanel` com Monaco
   `DiffEditor` (§2.3).
7. `/git/commit/{sha}/files` + lista de arquivos por commit clicável
   (§2.4).
8. Verificação: `scons lint && scons tests`; manual — abrir um projeto
   real com Vite (testa HMR via proxy), inspecionar um elemento e
   confirmar que liga IDE mode sozinho, abrir diff de um arquivo grande
   com código de mais de uma linguagem no mesmo commit.
