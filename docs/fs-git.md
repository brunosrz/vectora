# Vectora — Plano File System + Git (pseudo-plano de feature set)

> **Nota**: este é um documento de planejamento independente, não um bloco
> oficial do `docs/plan.md`. Ele descreve o conjunto completo de features
> relacionadas a filesystem e git — o que já existe, o que está quebrado,
> o que falta e recomendações extras. Quando uma feature for aprovada para
> implementação, migrar para o plano principal como sub-bloco.

---

## 1. Estado atual (o que já foi implementado)

### 1.1 Painel de Arquivos (Workbench → Aba Files)

Implementado em `chat/components/workbench/tabs/files-tab.tsx`:

| Feature                                     | Estado | Notas                                         |
| ------------------------------------------- | ------ | --------------------------------------------- |
| Árvore de arquivos lazy-expanded            | ✅     | SWR via `GET /workspaces/{id}/tree?path=`     |
| Viewer inline read-only                     | ✅     | `<pre>` com truncamento, `kind: "binary"`     |
| Pin de arquivo por thread                   | ✅     | Persistido no workbench-store                 |
| Filtro/busca na árvore                      | ✅     | Client-side sobre os entries já carregados    |
| Novo arquivo (toolbar + Ctrl+N)             | ✅     | Input inline no nó pai, `POST /fs/file`       |
| Nova pasta (toolbar + Ctrl+Shift+N)         | ✅     | Input inline no nó pai, `POST /fs/dir`        |
| Delete → Lixeira (send2trash)               | ✅     | `DELETE /fs?path=` sem `?permanent=true`      |
| Delete permanente (Shift+botão / Shift+Del) | ✅     | `DELETE /fs?path=&permanent=true`             |
| Tecla Del em item focado                    | ✅     | `tabIndex=0` + `onKeyDown`                    |
| Adicionar ao contexto do chat (`@path`)     | ✅     | Botão `@` → `pushMention` no chat-input-store |
| `@mention` no input do chat                 | ✅     | `at-mention-menu.tsx` + `resolveAtMentions`   |

### 1.2 Painel Diff (Workbench → Aba Diff)

Implementado em `chat/components/workbench/tabs/diff-tab.tsx`:

| Feature                        | Estado | Notas                                         |
| ------------------------------ | ------ | --------------------------------------------- |
| Resumo de arquivos modificados | ✅     | `GET /workspaces/{id}/git/diff`               |
| Hunks por arquivo (lazy)       | ✅     | `GET /workspaces/{id}/git/diff/file?path=`    |
| Colorização `+/-` nos hunks    | ✅     | Classes `text-green-500` / `text-destructive` |
| Badge `+N −M` na aba           | ✅     | Via workbench-store chip                      |
| Estado vazio (repo não-git)    | ✅     |                                               |

### 1.3 Ferramentas Git (Backend — Agent)

Implementado em `src/tools/git.py` — todas acessíveis pelo agente via HITL:

`git_status`, `git_log`, `git_diff`, `git_branch`, `git_checkout`,
`git_commit`, `git_worktree`, `git_push`, `git_pull`, `git_stash`, `git_init`.

Tools `gh_*` em `src/tools/gh.py`: PRs, issues via `gh` CLI.

### 1.4 Checkpointer (base para Rewind)

`src/services/checkpoint.py`: `AsyncSqliteSaver` do LangGraph gravando em
`~/.vectora/checkpoints.db`. Cada node de execução cria um checkpoint
(`checkpoint_id` UUID). O LangGraph suporta `get_state_history(config)` para
listar todos os checkpoints de uma thread.

**O rewind não existe na UI hoje** — a base técnica existe, mas não há endpoint
nem componente para expor ou usar essa funcionalidade.

---

## 2. Problemas identificados no Diff Tab

O diff tab funciona, mas tem 4 problemas que devem ser corrigidos:

### P1 — Arquivos não-rastreados (untracked) não aparecem

`git diff HEAD` retorna apenas arquivos rastreados com mudanças. Arquivos novos
que nunca foram staged (`git add`) são invisíveis. O correto é combinar:

```python
# status porcelain cobre staged + unstaged + untracked
status_text = repo.git.status("--porcelain=v1") or ""
```

Mapeamento de status porcelain (`XY path`):

- `XY = " M"` → modificado unstaged
- `XY = "M "` → modificado staged
- `XY = "MM"` → staged + mais mudanças unstaged
- `XY = "??"` → untracked (novo, nunca staged)
- `XY = "D "` → deletado staged
- `XY = " D"` → deletado unstaged
- `XY = "A "` → adicionado staged (novo arquivo já em stage)
- `XY = "R "` → renomeado staged

**Fix**: substituir `git diff HEAD --numstat` por `git status --porcelain=v1`
em `workspace_git_diff` e agrupar por `staged`, `unstaged`, `untracked`.

### P2 — N+1 chamadas git para derivar status de cada arquivo

Para cada arquivo em `diff_text.splitlines()` o backend faz uma chamada extra:

```python
ns = repo.git.diff("HEAD", "--name-status", path) or ""  # 1 call por arquivo
```

Com 20 arquivos modificados → 21 chamadas git. Correto seria extrair status
direto do `git status --porcelain=v1` numa única passagem.

### P3 — Sem separação staged/unstaged na UI

Tudo aparece numa lista única. Sem o agrupamento, o usuário não sabe o que
já está em stage (vai no próximo commit) vs o que ainda não foi adicionado.

**Fix visual**: dois grupos colapsáveis — "Staged" (verde) e "Unstaged + Não
rastreados" (amarelo/cinza), igual à **Source Control View** do VS Code.

### P4 — Sem ações no diff tab

O diff é read-only. Não é possível stagear, descartear ou commitar arquivos
diretamente do painel. Isso força o usuário a pedir ao Vectora para fazer via
tool calls ou abrir o terminal.

---

## 3. Features pendentes (proposta de implementação)

### FS-1 — Editor de arquivo inline no painel

**O que é**: clicar em um arquivo abre um editor com o conteúdo editável
(não apenas o viewer `<pre>` atual). Botões Salvar e Cancelar.

**Por que**: editar um arquivo rápido (corrigir um typo, ajustar config)
sem precisar pedir ao agente ou abrir outro editor.

**Backend** — novo endpoint:

```python
# PUT /workspaces/{id}/fs/file
# Auth: Depends(get_current_user) + ownership do workspace.
# Anti-traversal: src.services.security.resolve_within_workspace (B2),
# NÃO duplicar lógica em _resolve_inside.
class UpdateFsFileRequest(BaseModel):
    path: str
    content: str
    expected_sha256: str | None = None  # ETag — opcional para 1ª escrita

MAX_EDIT_BYTES = 2 * 1024 * 1024  # 2 MiB — acima disso, recusa

@view_router.put("/{workspace_id}/fs/file", response_model=StatusResponse)
async def update_fs_file(
    workspace_id: str,
    body: UpdateFsFileRequest,
    user: User = Depends(get_current_user),
):
    ws = workspace_registry.get(workspace_id)
    require_workspace_writer(user, ws)  # ABAC (B7)
    resolved = resolve_within_workspace(body.path, Path(ws.cwd))
    if resolved is None or not resolved.is_file():
        raise HTTPException(400, "Arquivo inválido.")
    if resolved.is_symlink():
        # Symlink já foi resolvido — revalidar que o alvo final ainda está
        # dentro do workspace. resolve_within_workspace deve seguir + checar
        # is_relative_to no resolved.resolve(strict=True).
        ...
    encoded = body.content.encode("utf-8")
    if len(encoded) > MAX_EDIT_BYTES:
        raise HTTPException(413, "Arquivo excede 2 MiB — edite externamente.")
    # ETag / If-Match: prevenir lost-update entre dois clientes.
    if body.expected_sha256 is not None:
        current_sha = sha256(resolved.read_bytes()).hexdigest()
        if current_sha != body.expected_sha256:
            raise HTTPException(412, "Arquivo mudou desde a última leitura.")
    # Charset: se o original era binário ou não-utf8, escrever utf-8 corrompe.
    # Detectar antes via chardet/file magic; rejeitar binários e arquivos
    # cujo encoding original não seja utf-8/ascii com aviso ao frontend.
    resolved.write_bytes(encoded)
    return StatusResponse(status="ok")
```

**Frontend** — modificações em `files-tab.tsx`:

- `FileContent` ganha `editing: boolean` + `loadedSha256: string` (do GET).
- Clicar em "editar" (ícone pencil no viewer) muda para `<textarea>` com
  o conteúdo atual.
- Botão "Salvar" → `PUT /workspaces/{id}/fs/file` com `expected_sha256`
  → invalidate SWR → volta viewer. Em 412 → modal "Arquivo mudou no
  servidor — recarregar e descartar suas mudanças?".
- Botão "Cancelar" → descarta state local → volta viewer.
- Warning se sair sem salvar (dirty state).
- Para arquivos > 200 KB: aviso "arquivo grande — somente leitura".
- Arquivos binários ou não-utf8 detectados pelo backend → viewer
  read-only com mensagem "Edição inline não suportada para este tipo".

**Detalhes de UX**:

- Font monospace no editor, tabs → 2 espaços.
- Sem syntax highlighting inicialmente. Se evoluir, preferir
  `@codemirror/basic-setup` (~100 KB) ao Monaco (~300 KB).
- Indicador "✎ editando" na barra do viewer quando em modo edit.
- Não bloquear salvar com warnings de formato — o usuário é responsável.

**Symlinks**: a árvore de arquivos, `browse-dir` e o editor inline
**não seguem symlinks por default**. Se for habilitar follow, o resolved
target deve passar de novo por `is_relative_to(workspace_root)` para
impedir escape do workspace.

**Cross-platform paths**: backend sempre devolve paths normalizados em
formato POSIX (`a/b/c.py`) nas responses, mesmo no Windows. O frontend
faz `path.split("/")` em vários lugares — manter essa invariante evita
quebrar UI. Backend converte para `Path` antes de tocar o FS.

**Arquivos**: `files-tab.tsx`, `src/api/handlers/workspaces.py`,
`src/services/security.py` (reuso de `resolve_within_workspace`).

---

### FS-2 — Diff Tab: corrigir status + staged/unstaged + ações

**Implementação em fases**:

**Fase A (corretude)** — backend:

- Substituir `git diff HEAD --numstat` por `git status --porcelain=v1`.
- Parser em `_parse_porcelain_status(text)` → `list[DiffFile]` com
  **dois flags independentes** (booleano único não cobre `XY=MM`):

  ```python
  class DiffFile(BaseModel):
      path: str
      staged_change: Literal["", "M", "A", "D", "R", "C", "T"]
      unstaged_change: Literal["", "M", "D", "A", "T"]
      untracked: bool  # XY == "??"
      additions: int
      deletions: int
  ```

  `XY=MM` vira `staged_change="M", unstaged_change="M"` — UI mostra o
  arquivo nos dois grupos com badge diferenciada (não duplicar entrada
  na response; o frontend decide a apresentação).

- Eliminar as N chamadas extras de `--name-status` — extrair tudo numa
  passada do porcelain.
- Mudança de schema breaking: bumpar versão da response em
  `X-Vectora-Diff-Schema: 2`; frontend antigo cai em fallback.

**Fase B (staged/unstaged)** — frontend:

- Dois grupos colapsáveis no `DiffTab`: "Staged" e "Modificados / Não rastreados"
- Cores distintas: verde para staged, amarelo para unstaged, cinza para untracked
- Badge da aba passa a mostrar `N arquivos` em vez de `+X -Y` (mais informativo
  quando há untracked)

**Fase C (ações)** — backend + frontend:

```python
# POST /workspaces/{id}/git/stage    body: {path: str}
# POST /workspaces/{id}/git/unstage  body: {path: str}
# POST /workspaces/{id}/git/commit   body: {message: str, paths?: list[str]}
# POST /workspaces/{id}/git/discard  body: {path: str}  ← git checkout HEAD -- <path>
```

UI da aba Diff com as ações:

- Cada arquivo → botões hover: `+` (stage), `−` (unstage), `↩` (discard)
- Painel inferior fixo: input de mensagem de commit + botão "Commit"
- Discard pede confirmação (não vai para lixeira — é `git checkout HEAD --`)
- Commit só habilita quando há arquivos staged e mensagem não vazia

---

### FS-3 — Rewind: "Retroceder até aqui" com desfazer arquivos

**O que é**: o usuário clica em qualquer mensagem e escolhe "Retroceder até
aqui". Isso desfaz a conversa **e** os arquivos que o agente modificou naquela
sequência — igual ao botão mostrado no screenshot (Claude Code tem isso).

**Por que é crítico**: sem rewind, uma sequência de edições ruins do agente
fica permanente. O usuário precisa pedir ao agente para desfazer manualmente,
o que frequentemente não funciona bem. É uma feature que todos os assistentes
de código possuem.

#### 3.1 — Parte da conversa (LangGraph checkpointer)

O LangGraph já tem a infraestrutura:

```python
# Listar todos os checkpoints de uma thread
async for state in checkpointer.alist({"configurable": {"thread_id": tid}}):
    # state.config["configurable"]["checkpoint_id"]
    # state.values["messages"]  ← mensagens até aquele ponto
    pass

# Restaurar thread para um checkpoint específico
# Basta passar o checkpoint_id na próxima chamada de stream
config = {
    "configurable": {
        "thread_id": thread_id,
        "checkpoint_id": target_checkpoint_id,  # LangGraph volta para aqui
    }
}
```

**Backend** — novo endpoint:

```python
# GET /threads/{thread_id}/checkpoints
# Retorna lista de checkpoints com (checkpoint_id, timestamp, message_count)

# POST /threads/{thread_id}/rewind
# body: {checkpoint_id: str}
# Marca o checkpoint_id como "current" no metadata da sessão
# Próxima chamada de StreamChat usará esse checkpoint_id
```

#### 3.2 — Parte dos arquivos (file snapshot system)

O checkpointer LangGraph salva apenas o estado do grafo (mensagens, memória
transitória). Não salva o filesystem. Para desfazer arquivos, precisamos de
uma camada separada.

**Estratégia A (Git — para workspaces git)**:

`git stash` **não serve** (stack linear, sem voltar a pontos intermediários
após múltiplos stashes). A abordagem correta é **gravar a árvore sem mexer
em HEAD** usando plumbing:

```bash
# Antes da resposta do agente que vai tocar arquivos:
git add -A --intent-to-add                       # untracked entram no index
TREE=$(git write-tree)                           # snapshot da árvore
PARENT=$(git rev-parse vectora/checkpoints/<thread_id> 2>/dev/null || echo "")
CHECKPOINT_SHA=$(git commit-tree "$TREE" \
   ${PARENT:+-p "$PARENT"} \
   -m "vectora: checkpoint <ts> thread=<thread_id>")
git update-ref refs/vectora/checkpoints/<thread_id> "$CHECKPOINT_SHA"
```

- `commit-tree` cria objeto commit **sem mover HEAD nem index do user**.
- Ref vive em `refs/vectora/checkpoints/<thread_id>` (namespace próprio,
  fora de `refs/heads/`) — não aparece em `git branch -a`, não polui log
  do dia-a-dia, não é puxado por `git fetch` default.
- Rewind: `git read-tree -m -u <CHECKPOINT_SHA>` (atualiza working tree
  - index sem reset hard, evita perder mudanças não-rastreadas posteriores
    ao checkpoint alvo). Para reset completo: `git restore --source=<sha>
--worktree --staged -- .`.
- Author do commit-tree fixado em `Vectora <vectora@local>` (env vars
  `GIT_AUTHOR_*`/`GIT_COMMITTER_*` na chamada, sem mexer no `git config`
  global do usuário; funciona em repos frescos sem `user.email`).
- Vantagem: deltas comprimidos pelo git, zero poluição visível.

**Estratégia B (snapshot — para workspaces sem git, ou pré-`git init`)**:

- Snapshot **diferencial**: copiar somente os arquivos que o
  `tool_resolver` (C2) registrou como tocados na rodada — não a árvore
  inteira. Lista vem dos `ToolCallEvent` de `file_write`/`file_edit`/
  `terminal` (heurística: parse de `cd ... && cmd`).
- Respeitar `.gitignore` do workspace (mesmo sem `.git/`, usar `pathspec`
  para parsing) + `.vectoraignore` opcional. Sem isso, `node_modules/`
  vira 200 MB por checkpoint.
- Storage: `~/.vectora/snapshots/<thread_id>/<checkpoint_id>/<rel_path>`.
- GC:
  - Deletar thread → limpar `snapshots/<thread_id>/` no mesmo handler.
  - Cron leve diário (cleanup job em `services/background.py`) remove
    snapshots de threads que não existem mais.
  - **Cap por usuário** (default 1 GiB, configurável em Settings → Admin
    → "Snapshots" com badge mostrando uso atual). Excedeu → recusa
    novo snapshot e degrada graciosamente (rewind continua funcionando
    nos checkpoints existentes).
- Index: tabela dedicada (ver §6), não `extra_json` do
  `vectora_sessions`.

**Estratégia C (híbrida — recomendada)**:

- Decisão **por checkpoint**, não por thread: `git init` no meio da
  conversa é caso real. Cada checkpoint carrega `strategy: "git" |
"snapshot"` no índice. Rewind para um checkpoint pré-`git init`
  usa snapshot; pós-`git init` usa commit-tree.
- Determinação no momento do save: `Path(ws.cwd, ".git").exists()` no
  instante do checkpoint.
- O índice `{checkpoint_id → (strategy, git_sha | snapshot_path)}`
  é a tabela `vectora_checkpoint_artifacts` (§6).

**Mutex por workspace**: rewind enquanto o agente executa uma tool call
que toca arquivos corrompe ambos os lados. Backend mantém
`asyncio.Lock` por `(workspace_id, thread_id)` em
`services/workspace_locks.py` — toda escrita de tool e o próprio rewind
adquirem o lock. Timeout default 30 s com erro claro ao user
("Operação concorrente em andamento — tente novamente").

#### 3.3 — UI do rewind

**Onde**: botão em cada mensagem (ícone `RotateCcw` ou `History`), visível
em hover — igual ao screenshot compartilhado.

**Fluxo**:

1. Usuário clica em "Retroceder até aqui" em mensagem M
2. Modal de confirmação: "Isso apagará as mensagens posteriores a M e
   restaurará os arquivos para o estado anterior. Continuar?"
3. Confirmar → `POST /threads/{id}/rewind` com `{checkpoint_id}`
4. Backend: restaura checkpoint LangGraph + snapshot de arquivos
5. Frontend: remove mensagens posteriores do store + invalida workbench
   (files + diff) → SWR recarrega
6. Input desbloqueado — usuário digita nova direção

**Componentes**:

- `RewindButton` em `message-item.tsx` (hover action)
- `RewindConfirmDialog` (modal)
- Hook `useRewind(threadId)` → `POST /threads/{id}/rewind`
- SSE event `rewind_complete` para sinalizar que arquivos foram restaurados

**Backend** (todos os endpoints com `Depends(get_current_user)` +
ownership check `thread.user_id == user.id` ou admin):

- `POST /threads/{thread_id}/rewind` body `{checkpoint_id: str}`
  - Adquire mutex `(workspace_id, thread_id)`.
  - Valida que checkpoint pertence ao thread e ao usuário.
  - Lê estratégia do `vectora_checkpoint_artifacts` (§6) e restaura
    arquivos (git via `read-tree` ou cópia de snapshot).
  - Atualiza `thread.metadata.current_checkpoint_id`.
  - Retorna `{status, files_restored: list[str], strategy}`.
- `GET /threads/{thread_id}/checkpoints`
  - Filtra `metadata->>'kind' = 'turn'` (ver §6 — índice de turnos)
    para evitar expor 20–50 checkpoints intermediários por thread.
  - Retorna timestamp, número de mensagens, arquivos modificados,
    `strategy`, link para preview do diff vs HEAD atual.

**Arquivos**: `src/api/handlers/threads.py`, `src/api/handlers/chat.py`,
`src/services/checkpoint.py`, `chat/components/chat/message-item.tsx`,
`chat/lib/stores/messages-store.ts` (ou equivalente).

---

### FS-4 — Rename/Move de arquivo ou pasta

**Backend** (auth + ownership + `resolve_within_workspace` em ambos os
paths):

```python
# POST /workspaces/{id}/fs/move
# body: {from_path: str, to_path: str}
# usa Path.rename() — move dentro do mesmo filesystem; shutil.move se cross-device
# Recusa se destino existe (sem overwrite silencioso).
```

**Frontend**: ícone de rename (duplo clique no nome do arquivo abre `InlineRenameInput`
— mesmo estilo do `InlineCreateInput` já existente). Drag-and-drop para mover
entre pastas (HTML5 drag API, baixa prioridade).

---

### FS-5 — Busca em arquivos (grep no painel)

**O que é**: campo de busca no topo do painel de arquivos que faz grep de
conteúdo nos arquivos do workspace (não apenas filtro por nome).

**Backend**:

```python
# GET /workspaces/{id}/fs/search?q=<query>&ext=<extensão>&case=false&max=50
# Implementação primária: ripgrep com hardlimits (workspace sem ripgrep cai
# em fallback Python lento mas seguro).
# Limites obrigatórios (workspace com 100k arquivos pode travar o backend):
#   --max-filesize 1M
#   --max-count 50           # hits por arquivo
#   --max-columns 200        # linhas longas (minified)
#   Respeitar .gitignore (ripgrep faz default; no fallback usar pathspec).
#   Timeout server-side total: 30s; após isso retorna parcial com `truncated: true`.
# Retorna [{path, line, column, snippet}].
```

**Frontend**: ícone de busca na toolbar, clique abre campo de query; resultados
como lista colapsada por arquivo com line numbers; clique abre arquivo no viewer
e destaca a linha. Badge "resultado parcial — refine a query" quando
`truncated`.

---

### FS-6 — Stage/Unstage + Commit direto do painel Diff (parte da FS-2C)

Já coberto em FS-2 fase C — listado separado por ser o mais requisitado.

**Ações por arquivo no diff**:

- `+` → `POST /workspaces/{id}/git/stage {path}`
- `−` → `POST /workspaces/{id}/git/unstage {path}`
- `↩` → `POST /workspaces/{id}/git/discard {path}` (pede confirm)

**Commit panel** (rodapé da aba Diff):

- Input de mensagem (placeholder "feat: ..." com sugestão de conventional commits)
- Checkbox "Commitar tudo" (stage all antes de commitar)
- Botão "Commit" → `POST /workspaces/{id}/git/commit {message, paths?}`
- Após commit bem-sucedido: invalidate diff SWR + toast "Commit criado"

---

### FS-7 — Histórico de arquivo (git log por arquivo)

**O que é**: em qualquer arquivo na árvore, botão "Ver histórico" → lista de
commits que tocaram aquele arquivo, com data, autor e mensagem. Clicar num
commit → ver o diff daquele commit para aquele arquivo.

**Backend**:

```python
# GET /workspaces/{id}/git/log/file?path=<path>&n=20&follow=true
# follow=true → git log --follow <path> para preservar histórico através de
# renames. Trade-off: --follow é caro em arquivos com histórico longo, e
# inválido para múltiplos paths. Single-file only.
# Retorna [{sha, author, date, message, additions, deletions, renamed_from?}].

# GET /workspaces/{id}/git/show?sha=<sha>&path=<path>
# Retorna o diff daquele commit para aquele arquivo.
```

**Frontend**: painel lateral dentro do viewer de arquivo ou modal.
Toggle "Seguir renames" (default ligado em single-file).

---

### FS-8 — Git Log visual (branch graph)

**O que é**: nova sub-aba dentro da aba Diff (ou aba própria "Git") com o
`git log --graph --oneline --decorate` renderizado. Lista de commits com SHA
abreviado, mensagem, autor, branch/tag labels.

**Ações por commit**:

- Copiar SHA
- Checkout → `git checkout <sha>` com HITL
- Cherry-pick → `git cherry-pick <sha>` com HITL
- Ver diff → abre painel de diff daquele commit

**Backend**: `GET /workspaces/{id}/git/log?n=50&all=true` — já existe parcialmente
em `git_log` tool; criar endpoint REST dedicado.

---

### FS-9 — Stash Manager UI

**O que é**: visualizar e gerenciar `git stash list` diretamente do painel,
sem precisar digitar no terminal.

**Ações**: `stash push` (com mensagem), `stash pop`, `stash apply`, `stash drop`,
`stash show` (diff do stash).

**Backend**: endpoints `POST /workspaces/{id}/git/stash` com `action` field.
Reusa `git_stash` tool mas expõe via REST para o painel.

---

### FS-10 — Conflict Resolution UI

**O que é**: quando um `git merge` ou `git pull` produz conflitos, o painel
de diff detecta status `"UU"` (both modified) e mostra um editor de resolução
side-by-side: versão "ours" à esquerda, "theirs" à direita, resultado editável
no centro.

**Backend**: `GET /workspaces/{id}/git/conflicts` retorna os arquivos com
conflito (porcelain `XY=UU/AA/DD/AU/UA/DU/UD`) e, para texto, os hunks
`<<<<<<<` / `=======` / `>>>>>>>`. Para arquivos binários, retorna apenas
`{path, kind: "binary"}` — sem hunks.

**UX por tipo**:

- **Texto**: editor 3-way (ours/theirs/merge) com hunks navegáveis.
- **Binário** (PNG, PDF, .docx, etc.): dois botões `Manter nossa` /
  `Manter deles` que rodam `git checkout --ours <path>` ou
  `--theirs <path>`. Preview lado-a-lado quando suportado (imagem).

**Por que**: conflitos de merge são uma das situações mais dolorosas de
resolver sem um editor visual. Alta prioridade quando o Vectora começar a
fazer PRs e merges frequentes.

---

### FS-11 — .gitignore Manager

**O que é**: detectar arquivos untracked que aparecem repetidamente e oferecer
"Adicionar ao .gitignore". Editor visual do `.gitignore` com validação de
padrões e preview de quais arquivos seriam ignorados.

**Backend**: `GET /workspaces/{id}/fs/gitignore-preview?pattern=<pat>` → lista
de arquivos que o padrão ignoraria.

---

### FS-12 — Auto-refresh on agent edit

> Renomeado de "File Watcher" — o nome anterior sugeria `inotify`/
> `FSEvents`/`ReadDirectoryChangesW`, mas a implementação só observa
> edições do **próprio agente** via SSE. Mudanças externas (terminal do
> user, VS Code aberto em paralelo) não são detectadas — para isso, ver
> FS-19.

**O que é**: quando o agente modifica arquivos via `file_write`/`file_edit`,
a árvore de arquivos atualiza automaticamente sem o usuário clicar em Refresh.

**Implementação atual**: SSE event `tool_call` com `name=file_write|file_edit`
já invalida `files+diff` em `use-stream-handler.ts` (T11.5 — já implementado).

**O que falta**: validar que a invalidação realmente dispara o re-fetch e que
a árvore mostra o arquivo novo/modificado após a resposta do agente.

**Gap conhecido**: o SWR só re-fetcha quando a aba está visível
(`skip: !expanded`). Se o usuário estiver em outra aba do workbench, o
refresh fica pendente até ele voltar para a aba Files. Marcar a aba com
chip "atualizações pendentes" quando houver invalidação enquanto
inativa.

---

### FS-14 — Compare branches/commits

**O que é**: visualizar `git diff branchA..branchB` (ou
`commitA..commitB`) com mesma UX da aba Diff. Necessário para revisar
PRs que o agente cria sem sair do chat.

**Backend**: `GET /workspaces/{id}/git/compare?base=<ref>&head=<ref>` —
reusa o parser de hunks do diff tab. Aceita SHAs, branches, tags.

**Frontend**: sub-aba na aba Diff "Comparar refs" com dois selects
(base/head) populados via `git_branch` + `git_log` recente. Resultado
renderiza idêntico ao diff de working tree.

---

### FS-15 — Revert commit

**O que é**: reverter um commit específico criando um commit novo de
revert (`git revert <sha>`). Distinto de checkout — mantém histórico
linear e seguro para branches compartilhadas.

**Backend** (HITL obrigatório, é destrutivo lógico): `POST
/workspaces/{id}/git/revert` body `{sha: str, message?: str}`.

**Frontend**: ação "Reverter" no menu de cada commit no Git Log visual
(FS-8). Modal de confirmação mostrando o diff inverso (o que será
desfeito) antes de aplicar.

---

### FS-16 — Worktree manager UI

**O que é**: UI para criar/listar/remover worktrees sem usar terminal.
A infra já existe (`git_worktree` tool em B3 + endpoint
`ListWorktrees`/`CreateWorktree` em B2).

**Frontend**: sub-aba "Worktrees" na aba Diff (ou seletor secundário no
header — Bloco B3). Lista com nome, branch, caminho, status (clean/
dirty). Ações: criar (nome + branch base), remover (com
`--force` opt-in), trocar para esta worktree (faz `SetActiveWorkspace`
apontando para o path da worktree).

**Aproveita 80% do código** da aba Diff (mesmos hunks, mesmo
`git_status`, mesmo `DiffFile` schema).

---

### FS-17 — Diff inline na árvore de arquivos (badges M/A/D)

**O que é**: badge `M` (modificado), `A` (adicionado), `D` (deletado),
`?` (untracked) ao lado de cada arquivo na árvore de Files, como na
**Source Control View** do VS Code.

**Backend**: nenhum endpoint novo — reusa `git status --porcelain=v1`
do FS-2A. Frontend faz join client-side com a árvore.

**Frontend**: `files-tab.tsx` consome o mesmo SWR de `diff` que a aba
Diff usa; cada entry da árvore checa se está no map de status.

**Por que**: trivial após FS-2A, mata a maior fricção da árvore atual
(não dá pra ver de relance o que mudou).

---

### FS-18 — Pre-commit hook validation

**O que é**: ao tentar commitar pelo painel Diff (FS-2C), mostrar se há
hooks `pre-commit` configurados (husky, `pre-commit` framework do Python,
`.git/hooks/pre-commit`) e rodá-los antes do commit, exibindo output
inline.

**Backend**: `POST /workspaces/{id}/git/commit` ganha flag
`dry_run_hooks: bool` (default `true`). Roda hook chain e devolve
`{status: "ok"|"hook_failed", output: str, hook_name: str}`. Se passou
em dry-run, commit prossegue automaticamente.

**Frontend**: spinner "rodando pre-commit…" no botão Commit; em falha,
expande área com output do hook e bloqueia commit até user corrigir e
re-tentar (ou marcar `--no-verify` opt-in com warning).

**Por que**: projetos com husky/pre-commit param o commit no terminal;
sem essa integração, o commit pelo painel sempre passa (porque GitPython
não roda hooks por default) e gera commits que quebram CI.

---

### FS-19 — File watcher real (mudanças externas)

**O que é**: detectar mudanças no filesystem feitas **fora** do agente
(user editando em VS Code, terminal externo, `npm install` criando
arquivos) e invalidar files/diff automaticamente.

**Por que separado de FS-12**: FS-12 é "auto-refresh on agent edit" via
SSE — barato e já implementado. FS-19 exige watcher real de FS, que tem
custo (CPU, file descriptors) e complexidade (debounce, ignore
`.git/index.lock`, etc.).

**Backend**: `watchdog>=4.0` (Python) por workspace ativo. Debounce
300 ms. Emite evento SSE `fs_changed` com lista de paths afetados (cap
em 100 — acima disso, força refresh completo).

**Frontend**: novo handler em `use-stream-handler.ts` (ou stream
dedicado de workspace events) → invalidate granular do SWR por path.

**Cap**: máximo 1 watcher por user (no workspace ativo) para limitar
descriptors. Encerrar quando sessão fecha.

---

## 4. Priorização sugerida

| #       | Feature                                         | Impacto | Esforço | Prioridade |
| ------- | ----------------------------------------------- | ------- | ------- | ---------- |
| FS-2A/B | Diff Tab: untracked + staged/unstaged           | Alto    | Pequeno | **P1**     |
| FS-17   | Badges M/A/D na árvore (bônus barato pós-2A)    | Médio   | Pequeno | **P1**     |
| FS-12   | Renomear + validar auto-refresh SSE             | Médio   | Pequeno | **P1**     |
| FS-3    | Rewind + desfazer arquivos (sprint exclusivo)   | Crítico | Grande  | **P1**     |
| FS-1    | Editor inline de arquivo (limites/ETag/charset) | Alto    | Médio   | **P2**     |
| FS-2C   | Stage/unstage/commit no painel                  | Alto    | Médio   | **P2**     |
| FS-13   | Abrir no VS Code (A + B + C)                    | Alto    | Médio   | **P2**     |
| FS-4    | Rename/Move                                     | Médio   | Pequeno | **P3**     |
| FS-5    | Busca em arquivos (ripgrep + limites)           | Médio   | Médio   | **P3**     |
| FS-7    | Histórico de arquivo (`--follow`)               | Médio   | Médio   | **P3**     |
| FS-16   | Worktree manager UI                             | Médio   | Médio   | **P3**     |
| FS-8    | Git Log visual                                  | Médio   | Grande  | **P4**     |
| FS-9    | Stash Manager                                   | Baixo   | Pequeno | **P4**     |
| FS-14   | Compare branches/commits                        | Médio   | Médio   | **P4**     |
| FS-15   | Revert commit                                   | Médio   | Pequeno | **P4**     |
| FS-10   | Conflict Resolution UI (texto → binário)        | Alto    | Grande  | **P5**     |
| FS-11   | .gitignore Manager                              | Baixo   | Pequeno | **P5**     |
| FS-18   | Pre-commit hook validation                      | Médio   | Médio   | **P5**     |
| FS-19   | File watcher real (watchdog)                    | Médio   | Médio   | **P5**     |
| FS-6    | (coberto por FS-2C)                             | —       | —       | —          |

---

## 5. Sequência de implementação recomendada

Sprint 1 e 2 ficam menores e mais focados; FS-3 ganha sprint próprio
(rewind é design-heavy, exige tabela nova + mutex + duas estratégias
testáveis).

```
Sprint 1 — Diff correto (1 semana)
  FS-2A/B   porcelain status (dois flags) + staged/unstaged
  FS-12     renomear + validar invalidação SSE (fechar dívida)
  FS-17     badges M/A/D na árvore (bônus barato pós-2A)

Sprint 2 — Rewind sozinho (2 semanas)
  FS-3      design + commit-tree em refs/vectora/checkpoints/
            + tabela vectora_checkpoint_artifacts
            + mutex por workspace + UI
  Marco: rewind funciona em workspace git; snapshot fallback NÃO entra
         ainda — entra no Sprint 6 quando GC/cap estiverem prontos.

Sprint 3 — Edição e ações git (1 semana)
  FS-1      editor inline (limites 2 MiB, ETag, charset detect)
  FS-2C     stage/unstage/commit no painel
  FS-4      rename/move
  FS-13     abrir no VS Code (A local + B Remote-SSH + C mirror)

Sprint 4 — Navegação avançada (1 semana)
  FS-5      grep com ripgrep + fallback Python + limites
  FS-7      histórico de arquivo com --follow
  FS-16     worktree manager UI

Sprint 5 — Git avançado (1–2 semanas)
  FS-8      log visual
  FS-9      stash manager
  FS-14     compare branches/commits
  FS-15     revert commit
  FS-10     conflict resolution (texto first; binário depois)

Sprint 6 — Polish (opcional)
  FS-11     .gitignore manager
  FS-18     pre-commit hook validation
  FS-19     file watcher real (watchdog)
  FS-3 snapshot fallback (workspaces sem git) com GC + cap
```

---

## 6. Notas de arquitetura

### Sobre o Rewind e o LangGraph checkpointer

O `AsyncSqliteSaver` grava automaticamente um checkpoint após cada node do
grafo. Numa thread com 5 turnos de conversa pode haver 20–50 checkpoints
(um por node executado). Para evitar lista poluída na UI:

- Marcar checkpoints "de turno" explicitamente no streaming layer:
  callback no `on_chain_end` do orchestrator escreve
  `metadata.kind = "turn"` no checkpoint final do turno.
- `list_checkpoints` filtra `WHERE metadata->>'kind' = 'turn'`. Os
  intermediários continuam existindo para debug, mas não vão pra UI.

A feature de rewind de arquivos é **ortogonal** ao LangGraph — o checkpointer
não sabe nada do filesystem. A associação `{checkpoint_id → estratégia +
artefato}` vive em **tabela dedicada** (não no `extra_json` de
`vectora_sessions` — JSON inflado degrada queries de listagem):

```sql
CREATE TABLE vectora_checkpoint_artifacts (
  thread_id      TEXT NOT NULL,
  checkpoint_id  TEXT NOT NULL,
  strategy       TEXT NOT NULL CHECK (strategy IN ('git', 'snapshot')),
  git_sha        TEXT,        -- preenchido quando strategy = 'git'
  snapshot_path  TEXT,        -- preenchido quando strategy = 'snapshot'
  files_touched  TEXT,        -- JSON array de paths relativos
  created_at     INTEGER NOT NULL,
  PRIMARY KEY (thread_id, checkpoint_id)
);
CREATE INDEX idx_checkpoint_artifacts_thread
  ON vectora_checkpoint_artifacts(thread_id, created_at DESC);
```

GC de snapshots e seleção de estratégia (`git` vs `snapshot`) operam
nessa tabela. Deletar thread → `DELETE WHERE thread_id = ?` + remoção do
diretório `snapshots/<thread_id>/` no mesmo handler (atômico via
contexto async).

### Sobre o Editor inline

Não usar Monaco Editor nem CodeMirror inicialmente — são dependências pesadas
(~300 KB). Um `<textarea>` simples com `font-family: monospace` e `white-space: pre`
cobre 90% dos casos de uso. Adicionar syntax highlighting somente se houver
demanda explícita, e nesse caso preferir `@codemirror/basic-setup` (~100 KB)
ao Monaco.

### Sobre o Diff Tab e untracked files

Arquivos untracked não têm `additions`/`deletions` (não há diff vs HEAD —
eles são novos). Exibir como `status: "?"`, `additions: 0`, `deletions: 0`
com tooltip "arquivo não rastreado". O diff de um untracked é o arquivo inteiro
vs `/dev/null` — gerar via `git diff --no-index /dev/null <path>`.

---

## 7. FS-13 — Integração com VS Code (botão "Abrir no VS Code")

### 7.1 Por que isso é não-trivial

O painel de arquivos do Vectora cobre os casos rápidos (ver árvore, editar
arquivo curto, stagear/commitar). Mas o usuário sério ainda quer "passar o
projeto para o VS Code" e continuar trabalhando lá com extensions, debugger,
LSP completo. O botão é trivial **quando o workspace é local** — basta chamar
`code <path>`. Fica complexo quando o Vectora roda numa **VPS da empresa** e
o usuário acessa pelo browser do PC dele.

Os transportes já mapeados em `Workspace.transport` (Bloco C6 do plano
mestre) definem o leque de cenários:

| Transport        | Vectora roda em              | User acessa de                     |
| ---------------- | ---------------------------- | ---------------------------------- |
| `local`          | Mesma máquina do user        | Browser/Electron local             |
| `ssh`            | VPS / servidor remoto        | Browser local + SSH no VPS         |
| `codespace`      | GitHub Codespace             | Browser local + `gh codespace ssh` |
| `host_client` \* | Host central, user no Client | Vectora Client (Tier 2B)           |

\* `host_client` é o modo Host/Client do Tier 2B (products.md) — ainda
não tem transport entry, mas a lógica é idêntica a `ssh`.

Cada combinação exige uma estratégia diferente para abrir o VS Code, e o
usuário pode não ter SSH disponível — caso comum em ambientes corporativos
restritos. Daí a necessidade de **múltiplas opções coexistindo**, com o
frontend escolhendo a melhor disponível para o contexto.

### 7.2 Opções de implementação

As opções abaixo não são mutuamente exclusivas — o plano final combina as
recomendadas (A + B + C como base; D, E, F evolutivas).

#### Opção A — `vscode://` URL handler para workspaces locais

**Quando**: `workspace.transport == "local"` e o user está no Electron
desktop ou num browser na mesma máquina onde o Vectora roda.

**Como**: o protocolo `vscode://` é registrado pelo instalador do VS Code em
todas as plataformas. Chamar `vscode://file/<path>` abre a janela apontando
para a pasta.

```ts
// chat/src/components/workbench/tabs/files-tab.tsx
function openInVSCode(workspacePath: string) {
  const url = `vscode://file/${encodeURI(workspacePath)}`;
  window.vectora?.openExternal(url) ?? window.location.assign(url);
}
```

**Backend**: nenhum endpoint novo. `workspace.cwd` já está disponível no
store de workspaces.

**Limites**: o browser bloqueia esquemas não-`https` por default sem
interação do user (o click conta como interação, então funciona). Se VS
Code não estiver instalado, abre dialog "Choose application". Fail-soft —
não há como detectar instalação programaticamente do browser.

**Suporta também**: VS Code Insiders (`vscode-insiders://`), Cursor
(`cursor://`), Windsurf (`windsurf://`) — adicionar select no Settings →
Preferências → "Editor preferido" (default: VS Code).

#### Opção B — Remote-SSH URL para workspaces `transport=ssh`

**Quando**: `workspace.transport == "ssh"`. User tem VS Code local + extension
`ms-vscode-remote.remote-ssh` instalada.

**Como**: VS Code suporta URL handler para Remote-SSH:

```
vscode://vscode-remote/ssh-remote+<user>@<host>:<port>/<remote_path>
```

```python
# src/api/handlers/workspaces.py — endpoint novo
@view_router.get("/{workspace_id}/vscode-url", response_model=VSCodeUrl)
async def workspace_vscode_url(workspace_id: str, user=Depends(get_current_user)):
    ws = workspace_registry.get(workspace_id)
    if ws.transport == "local":
        return VSCodeUrl(scheme="vscode", url=f"vscode://file/{ws.cwd}")
    if ws.transport == "ssh":
        host = ws.remote_host  # "user@host:port"
        return VSCodeUrl(
            scheme="vscode-remote",
            url=f"vscode://vscode-remote/ssh-remote+{quote(host)}{ws.remote_path}",
            requires_extension="ms-vscode-remote.remote-ssh",
        )
    if ws.transport == "codespace":
        return VSCodeUrl(
            scheme="vscode-codespace",
            url=f"https://github.com/codespaces/{ws.codespace_name}?editor=vscode",
        )
    raise HTTPException(400, "Transport não suporta abertura no VS Code.")
```

**Pré-requisito do user**: ter a chave SSH cadastrada no `~/.ssh/config`
local (não apenas no vault do Vectora — o Remote-SSH usa o config do user,
não consegue ler do servidor). O modal de "Abrir no VS Code" oferece
"Exportar config SSH" que baixa um snippet pronto para colar:

```
# Adicione ao seu ~/.ssh/config
Host vectora-<workspace_id>
  HostName <host>
  User <user>
  Port <port>
  IdentityFile ~/.ssh/vectora_<key_id>
```

**Limites**: exige Remote-SSH instalado. Se SSH ao VPS não está liberado
para o IP do user (corporate firewall) → falha sem explicação útil. Para
esse caso, ir para Opção C, E ou F.

#### Opção C — Híbrido: clone local sincronizado por git

**Quando**: user **já tem o mesmo repositório clonado** no PC local e quer
continuar editando ali, mas as últimas mudanças foram feitas pelo agente no
servidor.

**Estratégia**: tratar git como o canal de sincronização — não há FS
compartilhado, mas há um remote comum. O Vectora server faz `git push` para
uma branch dedicada de sync; o local faz `git pull`.

```
Vectora server (VPS)              Local (PC do user)
  workspace abc123                  ~/projects/repo (já clonado)
  branch feat/auth                  branch feat/auth
        │                                  │
        │ git push origin                  │ git pull origin
        │ vectora/sync/<thread_id>         │ vectora/sync/<thread_id>
        └──────────────► origin ◄──────────┘
                       (GitHub/GitLab/Gitea)
```

**Fluxo no botão "Abrir no VS Code (local)"**:

1. Backend valida que `workspace.git_remote` está setado.
2. Backend cria branch `vectora/sync/<workspace_id>/<thread_id>` (worktree
   isolada Bloco B3) e faz `git push --force-with-lease` para ela.
3. Backend retorna `{remote, sync_branch, local_path_hint}`.
4. Frontend mostra modal:

   ```
   📂 Abrir no seu VS Code local

   O agente fez mudanças no servidor. Para continuar localmente:

     1. cd <local_path_hint>           [Copiar]
     2. git fetch origin
     3. git checkout vectora/sync/abc123/thread789
     4. code .                          [Abrir no VS Code]

   Quando terminar de editar localmente:
     git push origin HEAD               [Copiar]
   ```

5. Botão "Abrir no VS Code" tenta `vscode://file/<local_path_hint>` —
   funciona se user configurou previamente o caminho local em Settings →
   Workspaces → "Pasta local do workspace abc123".

**Mapping local persistido**: `chat/lib/stores/local-mirror-store.ts` —
`Map<workspace_id, local_path>` em LocalStorage. UI tem ação "Vincular
pasta local" no menu do workspace (abre folder picker via
`window.vectora.pickFolder()` no desktop; no browser, user cola path
manual).

**Limites**: precisa de remote git acessível por ambos os lados. Não cobre
arquivos `.gitignore`d (dados locais, .env, build artifacts). Bom para
código-fonte; ruim para configs sensíveis.

#### Opção D — Vectora VSIX (extensão oficial — Tier 2A)

**Quando**: para qualquer transport, sem precisar de SSH nem de mirror local.
É a solução **definitiva** já planejada em `docs/products.md` Tier 2A e
`plan.md` Bloco N7.

**Como funciona**:

- Extensão `vectora.code` no VS Code Marketplace.
- Conecta ao Vectora server via `VECTORA_API_URL` + `VECTORA_TOKEN` (ou
  OAuth client credentials Bloco J1).
- Implementa `FileSystemProvider` (API oficial do VS Code) com URI scheme
  `vectora://<workspace_id>/<path>` — arquivos do workspace remoto
  aparecem **como se fossem locais** no Explorer, mas leitura/escrita vai
  pelo REST do Vectora (`GET/PUT /v1/workspaces/{id}/fs/file`).
- Comandos `Vectora: Open Workspace` (lista todos os workspaces do
  user via `GET /v1/workspaces`), `Vectora: Open Current Thread Worktree`.
- Terminal integrado do VS Code reusa o PTY remoto via WebSocket
  (`/vectora.terminal.v1/ws` — Bloco C4).
- Painel lateral com chat completo (webview apontando para
  `https://<host>/?embed=1&token=<oauth>`).
- LSP: a extensão proxia LSP requests local → server (usando
  `vscode-languageclient` com transport custom WebSocket sobre
  `/v1/lsp/<lang>` — endpoint novo no Bloco J).

**Botão no Vectora chat**: `vscode://vscode.open?url=<vectora_url>` —
deep-link que a própria extensão registra.

**Por que esta é a opção "premium"**: zero dependência de SSH, zero
mirror local, funciona em qualquer rede que alcance o servidor Vectora,
unifica edição + chat + terminal num só editor.

**Custo**: é um produto inteiro (Tier 2A em `docs/products.md`). Não cabe em
sprint da fs-git — é planejamento independente referenciado aqui só para
fechar o leque.

#### Opção E — VS Code Web via `code-server` embarcado

**Quando**: user **não tem VS Code local** (máquina corporativa restrita,
tablet, Chromebook) e quer editor visual sem instalar nada.

**Como**: rodar [`code-server`](https://github.com/coder/code-server) (port
oficial do VS Code para servidor, mantido pela Coder) como sidecar no
Vectora server. Expor em `https://<host>/vscode/<workspace_id>/` (mesmo
nginx do chat, proxy reverso).

**Auth**: gateway lê o cookie `vectora_access` (mesmo do chat) e injeta o
proxy do code-server. Sem cookie → redirect `/auth/signin`.

**Provisionamento por workspace**: cada workspace ativo recebe instância
`code-server` em `~/.vectora/code-server/<workspace_id>/` (config isolado
por user; settings.json compartilhado via mount opcional). Idle timeout
de 30min para liberar memória.

**Botão**: `window.open('/vscode/<workspace_id>/', '_blank')` — abre nova
aba com VS Code completo no browser.

**Limites**: code-server pesa ~250MB de imagem + ~500MB residentes por
sessão ativa. Inviável no plano Plus lite. Apenas Pro+ (mesma gate do
`storage.complete` em Bloco K6).

**Variante simplificada**: para repos do GitHub, link direto para
`github.dev/<owner>/<repo>/tree/<branch>` (VS Code Web oficial gratuito,
read-only para edição séria mas suficiente para navegar). Zero custo de
infra do nosso lado. Usar quando `workspace.git_remote` aponta para GitHub.

#### Opção F — VS Code Tunnels (Microsoft tunnel, sem SSH)

**Quando**: SSH bloqueado, mas user tem conta GitHub/Microsoft para
autenticar tunnel.

**Como**: VS Code suporta nativamente
[`code tunnel`](https://code.visualstudio.com/docs/remote/tunnels) — comando
que expõe o filesystem do servidor como destino remoto acessível por
`vscode.dev/tunnel/<name>` (browser) ou VS Code desktop ("Connect to
Tunnel"). Auth via OAuth GitHub/Microsoft, tráfego via servidores da
Microsoft (tunneling reverso, dispensa porta exposta no servidor).

**Provisionamento**:

```python
# src/api/handlers/workspaces.py
@view_router.post("/{workspace_id}/vscode-tunnel/start")
async def start_tunnel(workspace_id: str, ...):
    ws = workspace_registry.get(workspace_id)
    proc = await transport.run(
        f"code tunnel --name vectora-{workspace_id} --accept-server-license-terms",
        cwd=ws.cwd, background=True,
    )
    # parse output para extrair URL vscode.dev/tunnel/<name>
    return VSCodeTunnel(url=..., expires_at=...)
```

**Botão**: "Iniciar tunnel" → mostra QR code + URL → user copia ou autoriza
device-flow → tunnel ativo → "Abrir vscode.dev/tunnel/vectora-abc123".

**Limites**: requer instalação do binário `code` headless no servidor (uma
vez, no setup). Cada user precisa autorizar via device flow Microsoft no
primeiro uso. Tráfego passa pela Microsoft — não atende clientes com
política "zero terceiros".

### 7.3 Recomendação de implementação

**Sprint inicial (cabe em FS-13)** — cobre 80% dos casos:

- **Opção A** (vscode:// local) — workspaces locais. Esforço: 1h.
- **Opção B** (Remote-SSH URL) — workspaces SSH/Codespace. Esforço: 4h.
- **Opção C** (clone local + sync por git) — workspaces remotos com repo
  local mirror. Esforço: 1 dia (UI + endpoint de sync branch).

**Roadmap evolutivo** (não FS-13, referenciado para fechar o leque):

- **Opção D** (Vectora VSIX) — Bloco N7 + Tier 2A. Produto separado.
- **Opção E** (code-server embarcado) — Bloco N7 evolução, gate Pro+.
- **Opção F** (VS Code Tunnels) — alternativa quando SSH inviável; pode
  entrar em FS-13 fase 2 se demanda surgir.

### 7.4 UX do botão único

O frontend não precisa expor 6 opções. O botão é único — "Abrir no VS Code"
— e o backend decide a melhor estratégia disponível:

```ts
// chat/src/components/workbench/open-in-editor-button.tsx
async function handleOpenInEditor() {
  const opts = await api.workspaces.getVSCodeOptions(workspaceId);
  // opts.available = ["local", "remote-ssh", "local-mirror", "tunnel", ...]
  if (opts.available.length === 1) {
    openVSCodeWith(opts.available[0], opts);
  } else {
    showOpenInEditorModal(opts); // user escolhe
  }
}
```

**Modal de seleção** quando há ambiguidade:

```
Como você quer abrir o projeto?

  ◉ VS Code local (clone vinculado em ~/projects/repo)
       Recomendado — você já trabalha aqui localmente.

  ○ VS Code Remote-SSH (conectar ao VPS via SSH)
       Precisa ter "Remote-SSH" instalado no seu VS Code.

  ○ VS Code Web (vscode.dev no browser)
       Sem instalação — abre numa aba nova.

  ○ Instalar extensão Vectora (recomendado para uso frequente)
       → vai para a Marketplace do VS Code

                                       [Lembrar minha escolha]
                                                [Cancelar] [Abrir]
```

Preferência persistida em `chat/lib/stores/editor-preference-store.ts`
(`Map<workspace_id, editor_strategy>`).

### 7.5 Backend — endpoint unificado

```python
# GET /workspaces/{id}/vscode-options
class VSCodeOption(BaseModel):
    strategy: Literal["local", "remote-ssh", "codespace",
                      "local-mirror", "tunnel", "web-github", "vsix"]
    url: str | None
    label: str
    requires: list[str]   # ex: ["Remote-SSH extension"]
    available: bool       # se o backend conseguiu provisionar
    hint: str | None

class VSCodeOptions(BaseModel):
    workspace_id: str
    options: list[VSCodeOption]
    default: str          # strategy recomendada
```

Lógica de detecção:

- `transport=local` → habilita `local`.
- `transport=ssh` → habilita `remote-ssh` sempre; `tunnel` se `code`
  binary detectado no servidor.
- `transport=codespace` → habilita `codespace` (URL github.com/codespaces).
- `workspace.git_remote` setado + user tem mirror configurado em
  `editor-preference-store` → habilita `local-mirror`.
- `workspace.git_remote` aponta para `github.com/*` → habilita
  `web-github` (vscode.dev).
- Sempre lista `vsix` como opção "futuro" com link para Marketplace
  (placeholder até Tier 2A entregar).

### 7.6 Arquivos críticos (FS-13)

| Camada   | Arquivos                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------------- |
| Backend  | `src/api/handlers/workspaces.py` (+ `vscode-options`, `vscode-tunnel/start`, `git/sync-to-branch`)         |
| Backend  | `src/services/workspace.py` (+ `pick_vscode_strategies(ws, user_prefs)`)                                   |
| Frontend | `chat/src/components/workbench/open-in-editor-button.tsx` (novo)                                           |
| Frontend | `chat/src/components/workbench/open-in-editor-modal.tsx` (novo)                                            |
| Frontend | `chat/src/lib/stores/editor-preference-store.ts` (novo — local-mirror paths + strategy preferida por ws)   |
| Frontend | `chat/src/components/layout/settings-dialog/tabs/workspaces-tab.tsx` (+ campo "pasta local" por workspace) |
| i18n     | `chat/src/lib/i18n/strings.csv.ts` (+ `editor.*` em en/es/pt-BR)                                           |

### 7.7 Prioridade

Já incluído na tabela do §4 como **P2**, com entrada no Sprint 3 ao
lado de FS-1 / FS-2C / FS-4. D/E/F são evolutivos (D depende do produto
VSIX do Tier 2A; E/F dependem de demanda real).
