# Vectora — Tools Nativas (Batteries Included)

> Filosofia de tooling: torne **nativo** o que outros agentes deixam
> para o user instalar via MCP. Reduz fricção, garante qualidade,
> elimina "tenho que instalar 10 plugins antes de começar".
>
> Documento pareado com [`mcp-library.md`](mcp-library.md) — este define
> o que está dentro do Vectora; aquele define como o user instala
> qualquer outro MCP do ecossistema.

---

## A filosofia "Sublime vs vim+plugins"

Vim ganha em flexibilidade. Sublime Text ganha em produtividade de
saída-da-caixa. Para 90% dos usuários, **Sublime venceu**. Não porque
seja superior tecnicamente — porque eliminou a etapa "instale 30
plugins antes de escrever sua primeira linha".

Claude Code e Cursor caíram na mesma armadilha do vim:

> _"Para fazer browser automation, instale o MCP playwright. Para
> consultar PostgreSQL, instale o MCP postgres. Para gerar PDF, instale
> o MCP pdf. Para ler Excel, instale o MCP excel. Etc."_

Cada install é fricção. Cada server externo é mais um ponto de falha,
uma versão para acompanhar, uma vulnerabilidade potencial. **Vectora
inverte:** o que é alta-frequência + utilidade-ampla + estabilidade
vem nativo. O que é vendor-específico ou nicho fica na MCP Library.

---

## Critério de inclusão como tool nativa

Uma tool entra no binário Vectora **se e somente se** cumpre os 4:

1. **Alta frequência:** > 20% dos workflows reais provavelmente usam
2. **Utilidade ampla:** serve dev, PM, marketing, design — não só 1 persona
3. **Estável:** API/CLI/biblioteca não muda toda semana
4. **Sem dependência vendor-específica:** não exige conta paga em SaaS
   específico

Tudo que falha em pelo menos 1 critério vira **plugin DLC Tier 2C**
ou **MCP de terceiro** (via MCP Library).

---

## Inventário de tools nativas

### Já implementadas (Vectora atual)

| Tool          | Categoria   | Status | Backend                                   |
| ------------- | ----------- | ------ | ----------------------------------------- |
| `fs_read`     | File System | ✅     | stdlib                                    |
| `fs_write`    | File System | ✅     | stdlib                                    |
| `fs_edit`     | File System | ✅     | stdlib + difflib                          |
| `fs_grep`     | File System | ✅     | ripgrep wrap                              |
| `fs_glob`     | File System | ✅     | pathlib                                   |
| `fs_tree`     | File System | ✅     | stdlib                                    |
| `git_*`       | Git         | ✅     | subprocess gitpython                      |
| `gh_*`        | GitHub      | ✅     | `gh` CLI wrap                             |
| `web_search`  | Web         | ✅     | Tavily v2 via langchain-tavily            |
| `web_fetch`   | Web         | ✅     | httpx                                     |
| `rag_search`  | RAG         | ✅     | LanceDB/Qdrant + Cohere rerank            |
| `rag_add`     | RAG         | ✅     | embedding queue                           |
| `workspace_*` | Workspace   | ✅     | LangGraph store + filesystem              |
| `memory_*`    | Memory      | ✅     | LangGraph SqliteStore/PostgresStore       |
| `mcp_call`    | MCP         | ✅     | mcp-client (delegação para MCPs externos) |
| `terminal`    | Terminal    | ✅     | PTY (xterm.js no chat)                    |
| `skill_*`     | Skills      | ✅     | skill resolver                            |

### A adicionar — Onda 1 (pré-lançamento, crítico)

| Tool           | Categoria | Backend Python            | Justificativa                                                      |
| -------------- | --------- | ------------------------- | ------------------------------------------------------------------ |
| `time_*`       | Time/Date | `datetime`, `zoneinfo`    | Trivial e usado constantemente                                     |
| `http_request` | Network   | `httpx`                   | REST client genérico — alternativa explícita a "fetch with method" |
| `hash_*`       | Crypto    | `hashlib`                 | SHA/MD5/etc. para uso quotidiano                                   |
| `jwt_decode`   | Crypto    | `PyJWT`                   | Debug de auth é uso comum                                          |
| `base64_*`     | Encoding  | stdlib                    | Trivial mas frequente                                              |
| `regex_test`   | Util      | stdlib                    | Validar regex sem leave-and-test no chat                           |
| `json_*`       | Util      | stdlib + `jq`-like via py | Manipulação de JSON sem REPL                                       |

### A adicionar — Onda 2 (pós-lançamento Q3, alta demanda)

| Tool                  | Categoria | Backend                   | Justificativa                                 |
| --------------------- | --------- | ------------------------- | --------------------------------------------- |
| `browser_screenshot`  | Browser   | Playwright                | QA + scraping + verificação visual            |
| `browser_navigate`    | Browser   | Playwright                | Multi-step browser automation                 |
| `browser_fill_form`   | Browser   | Playwright                | Auth flows, smoke tests                       |
| `browser_extract`     | Browser   | Playwright + Cheerio      | Scraping estruturado                          |
| `db_query`            | Database  | sqlalchemy + drivers      | PostgreSQL/MySQL/SQLite/SQLServer (read-only) |
| `db_introspect`       | Database  | sqlalchemy reflection     | Lista tables/columns/relations                |
| `db_migrate`          | Database  | alembic wrap (HITL gated) | Apply migration (com aprovação humana)        |
| `code_python`         | Code Exec | subprocess sandbox        | REPL persistente Python (Deep Agents Bloco I) |
| `code_node`           | Code Exec | subprocess sandbox        | REPL persistente Node                         |
| `code_shell`          | Code Exec | (já existe via terminal)  | —                                             |
| `sequential_thinking` | Reasoning | Anthropic MCP spec nativo | Chain-of-thought tool padrão MCP              |

### A adicionar — Onda 3 (capabilities de output não-código)

| Tool                 | Categoria     | Backend                | Justificativa                                 |
| -------------------- | ------------- | ---------------------- | --------------------------------------------- |
| `pdf_read`           | Documents     | pypdf                  | PDF é input universal                         |
| `pdf_extract_tables` | Documents     | pdfplumber + camelot   | Tabelas em PDF é uso comum                    |
| `pdf_generate`       | Documents     | reportlab / weasyprint | Gerar PDF a partir de Markdown/HTML           |
| `pdf_merge_split`    | Documents     | pypdf                  | Manipulação básica                            |
| `xlsx_read`          | Office        | openpyxl               | Excel é onipresente em empresas               |
| `xlsx_generate`      | Office        | openpyxl               | Gerar planilha com fórmulas + formatação      |
| `docx_read`          | Office        | python-docx            | Word é onipresente                            |
| `docx_generate`      | Office        | python-docx            | Gerar relatório com formatação                |
| `pptx_generate`      | Office        | python-pptx            | Apresentações para liderança/clientes         |
| `csv_read_write`     | Data          | pandas                 | CSV universal                                 |
| `chart_generate`     | Visualization | matplotlib + plotly    | Retorna asset_id de imagem (alinhado ia-plus) |
| `dashboard_generate` | Visualization | HTML+Chart.js+Tailwind | Dashboard standalone que abre no browser      |
| `diagram_mermaid`    | Visualization | mermaid-cli            | Diagrama via texto                            |
| `diagram_plantuml`   | Visualization | plantuml jar           | UML legacy mas comum                          |
| `diagram_graphviz`   | Visualization | graphviz               | DAGs, fluxogramas                             |

### A adicionar — Onda 4 (mídia + análise)

| Tool                       | Categoria | Backend           | Justificativa                    |
| -------------------------- | --------- | ----------------- | -------------------------------- |
| `image_resize_crop`        | Image     | Pillow (PIL)      | Manipulação básica sem chamar IA |
| `image_convert_format`     | Image     | Pillow            | PNG ↔ JPEG ↔ WebP                |
| `image_metadata`           | Image     | Pillow + exifread | EXIF, dimensões, etc.            |
| `image_ocr`                | Image     | Tesseract         | OCR sem pagar API                |
| `audio_convert`            | Audio     | FFmpeg wrap       | Formato + sample rate + duration |
| `audio_extract_from_video` | Audio     | FFmpeg wrap       | Preparação para STT              |
| `video_thumbnail`          | Video     | FFmpeg wrap       | Frame extraction                 |
| `archive_zip_tar`          | Files     | stdlib            | Compactar/descompactar           |

### A adicionar — Onda 5 (infra/devops)

| Tool             | Categoria | Backend      | Justificativa                            |
| ---------------- | --------- | ------------ | ---------------------------------------- |
| `dns_lookup`     | Network   | dnspython    | Debug de DNS é comum                     |
| `port_check`     | Network   | socket       | "Tá ouvindo na porta X?"                 |
| `traceroute`     | Network   | subprocess   | Debug de rede                            |
| `whois`          | Network   | python-whois | Domínio, IP                              |
| `docker_ps_logs` | DevOps    | docker SDK   | Read-only: list, logs, inspect           |
| `kubectl_read`   | DevOps    | kubectl wrap | Read-only: get pods/deployments/services |
| `process_list`   | OS        | psutil       | Lista processos + uso de recursos        |

---

## O que **fica de fora** das tools nativas (e por quê)

### Conectores vendor-específicos → Plugins DLC Tier 2C

| Service                            | Por que não nativo                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Notion, Jira, Linear, Figma, Slack | Cada um exige OAuth, manutenção de API mutável, gerenciamento de webhooks. Vira plugin first-party (Tier 2C). |
| Google Workspace                   | Auth pesada, escopos complexos. Plugin DLC.                                                                   |
| Datadog, Sentry, Grafana           | Observability é vertical específico (`docs/observability.md`).                                                |
| Stripe, Shopify, HubSpot           | Commerce/CRM tem ciclo de vida próprio. Plugin DLC.                                                           |
| AWS/GCP/Azure CLIs                 | Auth complexa + risco de custo descontrolado. Plugin (futuro).                                                |

### MCPs do ecossistema → MCP Library

Tudo que não cabe nativo nem em plugin first-party fica disponível via
MCP Library — user instala sob demanda (`docs/mcp-library.md`).

### Capacidades pesadas/regulatórias → fora de escopo

| Capacidade                      | Por quê fora                                                 |
| ------------------------------- | ------------------------------------------------------------ |
| Compilação de C++/Rust/Swift    | Vectora não distribui compiladores; user instala se precisar |
| GPU compute (CUDA, etc.)        | Não temos como portar sem inflar o binário 5×                |
| Drivers de hardware específicos | Fora do escopo de produtividade                              |
| Crypto operacional (carteiras)  | Risco regulatório / financeiro                               |
| Geração de vídeo                | Custo/latência inviáveis (já documentado em `ia-plus.md`)    |

---

## Render hints novos derivados das tools

Cada tool com output não-trivial precisa de render hint correspondente
em `chat/lib/types/render.ts`:

```ts
export type RenderHint =
  | ...existentes...
  | "browser_screenshot"     // imagem com URL + timestamp
  | "db_result"              // tabela + query original + count + duration
  | "pdf_preview"            // primeira página + N pages + download
  | "xlsx_preview"           // primeiras N linhas + count + download
  | "pptx_preview"           // thumbnail dos primeiros slides + download
  | "docx_preview"           // primeiro parágrafo + page count + download
  | "dashboard_preview"      // iframe sandboxed + open-in-new-tab
  | "diagram_render"         // SVG inline + source toggle
  | "chart_inline"           // alias de image_preview com hint de source
  | "json_tree"              // JSON colapsível interativo
  | "regex_test"             // teste de regex com match highlights
  | "transcript"             // já em ia-plus
  | "audio_player"           // já em ia-plus
  | "image_preview"          // já em ia-plus
  | "image_grid";            // já em ia-plus
```

---

## Implementação: estrutura proposta

```
src/
├── tools/
│   ├── __init__.py            # ALL_TOOLS registry
│   ├── fs.py                  # File system (já existe)
│   ├── git.py                 # Git/GitHub (já existe)
│   ├── web.py                 # Web/Tavily (já existe)
│   ├── rag.py                 # RAG (já existe)
│   ├── memory.py              # Memory (já existe)
│   ├── mcp.py                 # MCP client (já existe)
│   ├── terminal.py            # Terminal/PTY (já existe)
│   ├── time.py                # NOVO Onda 1
│   ├── http.py                # NOVO Onda 1
│   ├── crypto.py              # NOVO Onda 1 (hash, jwt, base64)
│   ├── util.py                # NOVO Onda 1 (regex, json)
│   ├── browser/               # NOVO Onda 2
│   │   ├── __init__.py
│   │   ├── playwright.py
│   │   └── scraping.py
│   ├── database/              # NOVO Onda 2
│   │   ├── __init__.py
│   │   ├── query.py
│   │   ├── introspect.py
│   │   └── migrate.py
│   ├── code_exec/             # NOVO Onda 2 (alinhado Deep Agents)
│   │   ├── __init__.py
│   │   ├── python.py
│   │   └── node.py
│   ├── pdf.py                 # NOVO Onda 3
│   ├── office/                # NOVO Onda 3
│   │   ├── __init__.py
│   │   ├── xlsx.py
│   │   ├── docx.py
│   │   ├── pptx.py
│   │   └── csv.py
│   ├── viz/                   # NOVO Onda 3
│   │   ├── __init__.py
│   │   ├── chart.py
│   │   ├── dashboard.py
│   │   └── diagram.py
│   ├── media/                 # NOVO Onda 4 (compartilha com ia-plus)
│   │   ├── __init__.py
│   │   ├── image.py
│   │   ├── audio.py
│   │   └── video.py
│   └── infra/                 # NOVO Onda 5
│       ├── __init__.py
│       ├── network.py
│       ├── docker.py
│       └── k8s.py
```

Cada tool herda da base com:

- Metadata padronizada (`render_hint`, `category`, `destructive`, `icon`,
  `cost_estimate`, `requires_internet`, `requires_filesystem`)
- HITL automático se `destructive=True`
- Logging estruturado
- Tier gating via `services/tool_resolver.py`

---

## Impacto no tamanho do binário

Preocupação legítima: cada tool nativa adiciona peso ao Nuitka onefile.

Estimativa por onda:

| Onda | Tamanho extra Python deps | Notas                                                         |
| ---- | ------------------------- | ------------------------------------------------------------- |
| 1    | ~2 MB                     | stdlib + httpx + PyJWT                                        |
| 2    | ~120 MB ⚠️                | Playwright drivers (~80 MB) + alembic + drivers DB            |
| 3    | ~40 MB                    | reportlab + openpyxl + python-docx + python-pptx + matplotlib |
| 4    | ~50 MB                    | Pillow + Tesseract + FFmpeg estático ⚠️                       |
| 5    | ~10 MB                    | dnspython + psutil + docker SDK                               |

**Total estimado: ~220 MB extras** — Vectora hoje sai em ~150 MB, ficaria
~370 MB. Aceitável para desktop install, **pesado para Docker base
image** e **alto demais para Termux Android**.

### Estratégia de mitigação

**Modular install via Nuitka onefile com extensões lazy-loaded:**

```
vectora-base.exe       (150 MB)  — core + Ondas 1 e 5
vectora-pack-office    (40 MB)   — Onda 3
vectora-pack-browser   (80 MB)   — Onda 2 (Playwright)
vectora-pack-media     (50 MB)   — Onda 4
vectora-pack-data      (40 MB)   — Onda 2 (DB drivers + alembic)
```

Comportamento:

- Instalação default baixa `vectora-base` apenas
- Primeira chamada a tool de pack não-instalado dispara prompt:
  _"Esta ferramenta requer o pack 'browser' (80 MB). Instalar agora?"_
- Download in-place (sem reboot do Vectora)
- Verificação de assinatura GPG por pack

**Resultado:** binário base leve, capabilities full disponíveis sob
demanda, sem inflar usuários que não precisam.

---

## Comparação honesta com concorrentes

| Tool nativa proposta       |  Vectora  |      Claude Code      | Cursor |  Aider   | Continue |
| -------------------------- | :-------: | :-------------------: | :----: | :------: | :------: |
| File system completo       |    ✅     |          ✅           |   ✅   |    ✅    |    ✅    |
| Git/GitHub                 |    ✅     |          ✅           |   ✅   |    ✅    | Parcial  |
| Terminal persistente       |    ✅     |          ✅           |   ✅   |    ❌    |    ❌    |
| RAG sobre projeto          |    ✅     |        Parcial        |   ✅   | Repo-map |    ✅    |
| Browser automation         | 🔄 Onda 2 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Database query             | 🔄 Onda 2 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Code REPL sandboxado       | 🔄 Onda 2 |          ❌           |   ❌   |    ❌    |    ❌    |
| PDF gen/read               | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Excel gen/read             | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| PowerPoint gen             | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| Word gen/read              | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Charts/Plotly              | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| Mermaid/PlantUML/Graphviz  | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| OCR Tesseract              | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Image manipulação básica   | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Audio convert (FFmpeg)     | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Time/timezone tools        | 🔄 Onda 1 |          ❌           |   ❌   |    ❌    |    ❌    |
| JWT decode / hash / base64 | 🔄 Onda 1 |          ❌           |   ❌   |    ❌    |    ❌    |
| Sequential thinking        | 🔄 Onda 2 | ✅ extension thinking |   ❌   |    ❌    |    ❌    |
| Docker/k8s read-only       | 🔄 Onda 5 |       MCP ext.        |   ❌   |    ❌    |    ❌    |

**Diferencial competitivo claro:** Vectora oferece batteries-included
em escala que nenhum concorrente match.

---

## Cronograma de implementação

```
Pré-lançamento (próximos 3 meses)
  Onda 1: Time, HTTP, Crypto, Util — ~1 sprint (1 semana)

Pós-lançamento Q1
  Onda 5: Infra (DNS, ports, Docker, k8s) — ~1 sprint
  Beta program (docs/beta-program.md) para Onda 2/3

Pós-lançamento Q2
  Onda 2: Browser + DB + Code REPL — ~3 sprints
   (browser é o mais pesado; DB inclui HITL para migrate)

Pós-lançamento Q3
  Onda 3: Office (PDF, Excel, Word, PowerPoint, Charts, Diagrams) — ~3 sprints

Pós-lançamento Q4
  Onda 4: Media (Image, Audio, Video, OCR) — ~2 sprints
   (alinhado com sprints M5/M6 de ia-plus)
```

---

## Princípios cardinais

1. **Nativo > MCP quando frequência justifica.** Não criar plugin para o
   que 80% dos users vai querer no dia 1.

2. **Plugin DLC > nativo quando vendor-específico.** Notion não vira
   nativo nunca — a API muda demais, requer OAuth, etc.

3. **MCP Library > plugin quando vertical.** Para nichos onde Vectora
   não compete, ecossistema cobre.

4. **Tudo é tool, nada é mágica.** Toda capability passa pelo mesmo
   pipeline de tool calling, com mesmo render hint, mesma rastreabilidade.

5. **HITL para destrutivo.** Migrate de schema, delete de arquivo, send
   email — sempre passa por aprovação humana (configurável).

6. **Modularidade no install, não no código.** Tools agrupadas em packs
   instaláveis sob demanda para não inflar o binário base.

7. **Sandbox por padrão para code execution.** REPL Python/Node roda em
   container isolado; FS access mediado; network gated.

8. **Cost estimate antes de operações caras.** Toda tool que custa
   ($) declara estimate; HITL gate por threshold configurável.
