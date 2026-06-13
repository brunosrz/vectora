# Vectora — Posicionamento

> Documento canônico de posicionamento. Define o que Vectora **É**, o que
> Vectora **NÃO É**, e para quem **NÃO** foi feito. Todo material de
> marketing, copy de site, mensagem de vendas e onboarding deve estar
> alinhado a este doc.
>
> **Por que existir:** posicionamento difuso mata produto. "Vectora é
> para qualquer um que use IA" é a melhor forma de não vender para
> ninguém. Este doc afia o discurso.

---

## A frase canônica

> **"Vectora é o agente de produtividade self-hosted para engenheiros
> sêniores e seus times — escreve código com contexto real do projeto,
> e atende o resto da empresa (PM, marketing, design, exec) com a mesma
> base de conhecimento."**

Cabe num tweet. Diz para quem é (engenheiros sêniores + times), o que
faz (produtividade, não só código), o diferencial técnico (self-hosted,
contexto real), e a expansão natural (resto da empresa via mesma KB).

---

## O que Vectora **é**

- **Self-hosted comercial.** Roda na sua infra, código proprietário
  licenciado. Sem markup de tokens, sem servidor intermediário, sem lock-in.
- **Agente com memória real.** RAG sobre seu código, docs, decisões e
  histórico de trabalho. Não é assistente amnésico que esquece o projeto
  a cada mensagem.
- **Auditável.** Toda resposta vem com fontes citadas (`[1] [2]`).
  Toda tool call é registrada com input/output. Toda decisão de routing
  é rastreável.
- **Multi-modal nativo.** LLM + embedding + reranker + STT + TTS + image
  gen sob protocols abstratos — troca de provider é mudança de config.
- **Multi-acesso.** O mesmo agente atende via CLI, chat web, desktop
  app, MCP server (delegação) e REST API (integração).
- **Multi-pessoa.** A mesma instalação serve devs sêniores, PMs,
  marketing, design e executivos — cada perfil acessa via Skills
  específicas que afinam o agente para seu domínio.
- **Auto-treinável.** Você indexa o que quiser via `/rag add`. Você
  ajusta comportamento via `AGENTS.md`. Você adiciona capacidades via
  Skills e plugins MCP. Você decide o que o agente sabe.

---

## O que Vectora **NÃO é** (anti-positioning explícito)

| Vectora **NÃO é**                        | Para isso use:                                                         |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| Gerador de apps com 1 prompt             | Lovable, v0, Bolt.new, Replit Agent                                    |
| Autocomplete inline no editor            | GitHub Copilot, Codeium, Cursor Tab                                    |
| Substituto de engenheiro júnior          | Devin, Cognition, Magic.dev (quando provarem que funcionam de verdade) |
| Chat de IA para conversa casual          | ChatGPT, Claude.ai, Gemini app                                         |
| Assistente de reuniões                   | Perssua, Otter.ai, Fireflies                                           |
| Wiki/documentação editorial colaborativa | Notion, Confluence, Outline                                            |
| BI tool / dashboard SaaS dedicado        | Metabase, Looker, Tableau                                              |
| Automação no-code de workflows           | Zapier, n8n, Make                                                      |
| Plataforma de hosting de apps            | Vercel, Netlify, Render                                                |
| Sistema de tickets / project management  | Jira, Linear, Asana                                                    |
| CRM                                      | Salesforce, HubSpot, Pipedrive                                         |

Vectora **integra** com vários destes (via MCP ou plugins DLC), mas
**não substitui** nenhum.

---

## Para quem Vectora **foi feito**

### Persona primária — Engenheiro Sênior + Tech Lead

- 5+ anos de experiência. Sabe ler stack trace. Sabe o que é race
  condition. Não pede para a IA "resolver o bug" — pede para ela
  **mostrar onde o estado divergiu** e propor 2 abordagens com
  trade-offs.
- Trabalha em projetos de médio/grande porte onde o contexto importa:
  monolitos legados, microserviços com convenções internas, codebases
  com 50k+ linhas.
- Já testou Cursor/Copilot e gostou em parte, mas se frustra quando o
  modelo ignora os padrões da equipe ou propõe soluções que violam
  decisões já tomadas.
- Valoriza self-hosted por motivos reais: código proprietário, dados de
  cliente, regulação setorial.
- Preço de $7–20/mês é trivial vs hora dele; mas se sente desrespeitado
  por SaaS que cobra $20 e ainda manda tudo para a nuvem do fornecedor.

### Persona secundária — Time técnico (3–50 devs)

- CTO / VP Engineering / Engineering Manager decide a compra.
- Cada dev usa o Vectora pelo VSIX, chat web ou desktop. Compartilha
  workspaces, decisões, skills internas.
- Empresa tem alguma sensibilidade a dados (cliente em fintech, saúde,
  jurídico, governo, defesa).
- Já tem Cohere/Tavily ou aceita pagar; já tem PostgreSQL/Redis na infra
  ou aceita subir.

### Persona terciária — Não-técnicos do mesmo time

- PM / Product Designer / Marketing / Sales / Exec da mesma empresa.
- **Não compra o Vectora sozinho** — chega por arrasto, porque o time
  técnico já tem.
- Usa para tarefas adjacentes: PRD com contexto do produto, deck para
  board com dados do RAG, dashboard de KPI, resumo de reunião,
  rascunho de proposta.
- Instala Skills/Personas packs específicas (ver `docs/personas.md`).
- Pressiona admin a comprar plano Team para liberar Vectora para mais
  gente da empresa.

### Persona enterprise — Empresa com requirements pesados

- 50+ devs ou setor regulado.
- Compra OEM ou Enterprise. Quer SLA, DPA, suporte dedicado, auditoria
  sob NDA, on-premise air-gapped.
- Ciclo de venda longo (3–6 meses). Não é foco do primeiro ano.

---

## Para quem Vectora **NÃO foi feito** (anti-buyer personas)

### "Vibe coder" / não-engenheiro construindo app

- Quer mandar 3 mensagens e ter um SaaS pronto.
- Não lê código. Não sabe debugar. Confia 100% no que o LLM gera.
- **Use Lovable, v0 ou Bolt.** Vectora vai frustrar essa pessoa porque
  exige saber o que está acontecendo, ler o diff antes de aprovar, e
  entender contexto.

### Dev júnior aprendendo

- Vectora é poderoso demais sem supervisão. As tools destrutivas
  (terminal, edit, git push) podem causar estrago.
- Recomendação honesta: comece com Copilot ou Cursor por 6+ meses,
  depois migre para Vectora quando souber o que está aprovando.

### Quem quer "IA grátis"

- Vectora cobra $7–20/mês + tokens. Não há free tier perpétuo (só
  trial de 30 dias).
- **Use OpenCode, Continue.dev ou Aider.** São open-source de verdade,
  você roda na sua máquina sem pagar nada.

### Empresa que quer cloud-managed sem instalar nada

- Vectora exige instalar (mesmo que seja `vectora server chat` numa
  VPS de R$50/mês).
- Quem não quer infra nenhuma usa Claude Code direto (assinatura
  Anthropic) ou Cursor (cloud-managed).

### Quem precisa de assistente de reuniões / áudio em tempo real

- Vectora tem TTS/STT (via `ia-plus.md`), mas é input/output do agente,
  não diarização ao vivo de reuniões.
- **Use Perssua** (BR, excelente) ou Otter.ai / Fireflies (US).

### Marketing genérico, ops sem RAG necessário

- Quem só quer "ChatGPT pra escrever post de LinkedIn" não precisa do
  Vectora. Use ChatGPT direto.
- Vectora faz sentido para marketing **quando** existe brand voice
  documentada + histórico de campanhas indexado + integração com
  analytics. Sem RAG, é overkill.

---

## Frases canon de venda

### Para tech lead / engenheiro sênior

> _"Cursor é ótimo até você cansar de explicar a mesma decisão de
> arquitetura toda semana. Vectora lembra — porque você indexou no RAG.
> E roda na sua infra, então pode ler todo o código sem medo."_

### Para CTO de PME tech

> _"Self-hosted comercial. Sem markup de tokens. Mesmo agente atende
> seus devs (via VSIX/chat), seu PM (via persona pack), e sistemas
> internos (via REST API). $20/mês por seat ou plano Team para o time
> inteiro."_

### Para empresa em setor regulado

> _"Seus dados nunca passam pelo nosso servidor — você liga direto às
> APIs que escolheu. Auditoria de código sob NDA. Suporte para
> on-premise air-gapped no plano Enterprise."_

### Para usuário não-técnico do mesmo time

> _"O Vectora já está rodando no servidor da sua empresa. Você instala
> a persona pack 'marketing' (ou 'design', 'pm', 'sales') e ganha um
> assistente que conhece os clientes, as campanhas e a marca — porque
> tudo já está no RAG da empresa."_

### Para integrador / partner

> _"REST API limpa, OAuth2 client credentials, SDKs Python/TS, MCP
> server expondo todas as tools. O Vectora vira o motor RAG do seu
> produto sem você precisar construir o pipeline do zero."_

---

## Frases que **não** devem ser usadas (anti-copy)

| Frase ruim                           | Por que é ruim                                                  |
| ------------------------------------ | --------------------------------------------------------------- |
| "Construa apps com IA em minutos"    | É promessa de vibe coding — não somos isso                      |
| "Substitua sua equipe de devs"       | Falso e antipático                                              |
| "IA mais poderosa do mercado"        | Subjetivo, indefensável, todo mundo diz                         |
| "Grátis para sempre"                 | Não é o modelo                                                  |
| "Mais barato que ChatGPT Plus"       | Comparação errada — público diferente                           |
| "Funciona sem configuração"          | Falso — exige instalar, configurar API keys, indexar workspaces |
| "Tudo que ChatGPT faz, mas privado"  | Reduz Vectora a "ChatGPT self-hosted", ignora RAG/MCP/agentes   |
| "Compatível com qualquer LLM"        | Vago e meio-verdade — só Gemini/OpenAI/Anthropic/Cohere/Ollama  |
| "Crie um SaaS completo com 1 prompt" | Vibe coding outra vez                                           |

---

## Checklist de coerência

Toda peça pública (site, README, post, deck, vídeo) deve passar por:

- [ ] A frase canônica aparece sem mutação significativa
- [ ] Nenhuma das frases proibidas aparece
- [ ] Pelo menos uma das frases canon de venda é usada
- [ ] Se menciona concorrente, o diferencial está claro e honesto
      (sem fud)
- [ ] Se menciona price, está alinhado com `docs/products.md`
- [ ] Se menciona feature em roadmap, status correto (✅ disponível /
      🔄 em desenvolvimento / 📋 planejado)
- [ ] Se menciona open source, **deixa claro que NÃO é** (versões antigas
      Apache não contam)

---

## Mudanças de posicionamento ao longo do tempo

Posicionamento não é imutável. Quando atualizar este doc:

- Lançamento de produto Tier 3 (Helpdesk, Code Review) — adicionar à
  frase canônica? Provavelmente não — eles têm posicionamento próprio.
- Mudança de pricing — atualizar frases que mencionam valor.
- Pivô de público (ex: focar Enterprise) — riscar este doc e começar de
  novo, com aprovação explícita do fundador.
- Concorrente novo relevante — atualizar tabela de anti-positioning.

**Quem aprova mudanças:** Bruno (fundador). Posicionamento é decisão
estratégica, não tarefa delegável.
