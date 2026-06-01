# Vectora Company — OEM Licensing & Cloud Plan

> Dois documentos de planejamento de longo prazo:
> (1) Licenciamento OEM — proteção e monetização quando empresas usam
> o Vectora como motor interno de produtos próprios via API REST.
> (2) Vectora Cloud — versão hosted da Vectora Company com Vectora Data Store.

---

## PARTE 1 — Licenciamento OEM

### O cenário

A API REST do Vectora (Bloco Z do chat-first) abre uma possibilidade real:
empresas compram licença do Vectora, montam um produto próprio em cima
(um app estilo ChatGPT, uma IDE, uma ferramenta de automação interna) e
vendem esse produto com assinatura própria.

Isso é legítimo e saudável — significa que o Vectora é bom o suficiente
para ser a base de outros produtos. Mas há um problema econômico: se essa
empresa tem 5.000 usuários pagantes no app delas, são 5.000 usuários que
estão gerando receita para ela, não para a Vectora Company. A licença que
ela paga é de um único servidor Pro — R$55/mês — enquanto monetiza milhares
de usuários em cima disso.

Esse cenário precisa de um modelo de licenciamento específico: o **OEM License**.

---

### Definindo os cenários de uso

**Uso interno (coberto pelas licenças atuais):**
Empresa instala o Vectora para uso dos próprios funcionários. 20 devs
usando o Vectora internamente = plano Team. Isso já está coberto.

**Uso como motor de produto externo (requer OEM License):**
Empresa usa a API REST do Vectora para alimentar um produto que vende
para clientes externos. O produto final não é "o Vectora" — é outro app
que usa o Vectora por baixo. Essa empresa está revendendo indiretamente
o valor do Vectora.

O gatilho para OEM License é claro: **uso comercial via API REST para
servir usuários externos à organização licenciada.**

---

### Modelo de OEM License

**Princípio:** a Vectora Company deve capturar valor proporcional ao
sucesso do produto construído em cima do Vectora. Não uma taxa fixa
que ignora o tamanho do negócio.

**Estrutura de tiers OEM:**

| Tier           | Usuários externos | Preço mensal      | Inclui                                         |
| -------------- | ----------------- | ----------------- | ---------------------------------------------- |
| OEM Starter    | até 500           | $199/mês          | 1 instância Pro + suporte básico               |
| OEM Growth     | até 5.000         | $599/mês          | 2 instâncias Pro + suporte prioritário         |
| OEM Scale      | até 25.000        | $1.499/mês        | Instâncias ilimitadas + SLA + suporte dedicado |
| OEM Enterprise | acima de 25.000   | Negociação direta | Contrato customizado + revenue share           |

**Revenue share (OEM Enterprise):**
Para produtos com base grande de usuários, negociar percentual da receita
do produto externo em vez de (ou além de) mensalidade fixa. Tipicamente
2–5% da receita bruta do produto que usa o Vectora como motor.

---

### Termos de OEM License (o que muda nos Termos de Uso)

**O que é permitido com OEM License:**

- Usar a API REST do Vectora para alimentar produto externo comercial
- Construir interface própria sobre o Vectora (white-label de UX)
- Vender assinatura do produto externo para usuários finais
- Escalar o produto sem limitação de usuários (dentro do tier contratado)

**O que nunca é permitido (mesmo com OEM License):**

- Remover ou ofuscar a atribuição "Powered by Vectora" no produto externo
  (exceto em contratos Enterprise com negociação específica)
- Redistribuir o código-fonte do Vectora
- Oferecer o Vectora como produto concorrente direto (revenda da licença
  em si, não de um produto construído em cima)
- Remover as restrições de licença para os usuários finais

**Atribuição obrigatória:**
Produtos construídos em cima do Vectora devem exibir "Powered by Vectora"
em local visível (rodapé, about page, ou tela de loading). Exceção
negociável apenas em contratos Enterprise acima de $3.000/mês.

---

### Detecção e enforcement

**Como detectamos uso OEM não licenciado:**

- Monitoramento de volume de chamadas de API por VECTORA_TOKEN
- Se um token Plus ou Pro gera volume atípico de usuários simultâneos
  (muito acima do esperado para uso interno), flag automático para revisão
- Nos Termos de Uso: uso OEM sem licença específica é violação contratual

**Processo:**

1. Flag automático ao detectar padrão de uso inconsistente com o plano
2. Email de notificação: "Identificamos uso que pode requerer OEM License"
3. Período de regularização de 30 dias
4. Após 30 dias sem regularização: suspensão da licença

**Nota:** o objetivo não é punir, é monetizar corretamente. A comunicação
deve ser amigável — uma empresa que está usando o Vectora como motor de
produto externo é exatamente o tipo de cliente que queremos, só precisamos
do contrato certo.

---

### Adição ao Vectora Company Plan (Bloco J — Marketing)

OEM License abre um canal de vendas B2B diferente:

**Perfil do cliente OEM:**

- Startups SaaS construindo produto de IA sem querer construir infraestrutura
- Agências de desenvolvimento que querem oferecer AI features para clientes
- Empresas de software legado que querem "colocar IA" no produto sem reescrever tudo

**Abordagem de vendas OEM:**

- Não é self-serve como os planos Plus/Pro/Team
- Requer call comercial antes de fechar contrato
- Bruno faz as primeiras vendas diretamente; contrata sales quando houver
  3+ clientes OEM ativos

---

## PARTE 2 — Vectora Cloud & Vectora Data Store

### O problema do BYOK

O modelo atual do Vectora é BYOK (Bring Your Own Keys): o usuário traz suas
próprias API keys de OpenAI, Anthropic, Cohere, Tavily. Isso é ótimo para
o self-hosted — dá controle total, sem margem da Vectora Company sobre uso de IA.

Mas para uma versão cloud, o BYOK cria atrito demais:

- Usuário precisa criar conta em 3–4 providers diferentes antes de usar
- Usuário precisa entender limites de uso, preços por token, quotas
- Usuário casual não quer gerenciar API keys — quer só usar

Para o Vectora Cloud funcionar para um público mais amplo, o BYOK deve ser
**opcional** — não obrigatório. O padrão é: você paga o Vectora Cloud e
ele vem com créditos de IA incluídos.

---

### O que é o Vectora Cloud

Uma versão hosted do Vectora rodando em servidores da Vectora Company.
Não substitui o self-hosted — é uma opção adicional para quem não quer
gerenciar infraestrutura.

**Diferenças do self-hosted:**

| Aspecto         | Self-hosted                   | Vectora Cloud                                 |
| --------------- | ----------------------------- | --------------------------------------------- |
| Infraestrutura  | Servidor do cliente           | Servidores da Vectora Company                 |
| RAG customizado | Total (indexa qualquer coisa) | Vectora Data Store (buckets prontos + upload) |
| BYOK            | Obrigatório                   | Opcional (créditos incluídos)                 |
| Privacidade     | Total                         | Dados no servidor da Vectora Co.              |
| Setup           | 10–30 min                     | Zero — usa direto no browser                  |
| Plano gratuito  | Não                           | Sim (subsidiado por parceiros)                |

**URL:** `vectora.chat` ou `app.vectora.company`

---

### Vectora Data Store

O maior desafio do Vectora Cloud: o RAG não pode ser retreinado livremente
pelo usuário da forma que é no self-hosted (onde o usuário indexa sua própria
codebase, docs, etc.). No cloud, não faz sentido cada usuário subir gigabytes
de dados para um servidor compartilhado.

A solução: **Vectora Data Store** — uma biblioteca de buckets de conhecimento
prontos, curados pela Vectora Company, que o usuário ativa conforme necessário.

**Analogia:** como playlists de streaming. Você não precisa ter os arquivos
— você ativa o que quer usar.

---

### Categorias de buckets no Data Store

**Programação e desenvolvimento:**

- `python-backend` — Python, FastAPI, SQLAlchemy, asyncio, boas práticas
- `typescript-frontend` — React, Next.js, TypeScript, Tailwind, shadcn
- `typescript-backend` — Node.js, Hono, tRPC, Bun, APIs REST
- `devops-cloud` — Docker, Kubernetes, CI/CD, GitHub Actions, Terraform
- `databases` — PostgreSQL, SQLite, Redis, MongoDB, queries e otimização
- `ruby-rails` — Ruby on Rails, gems populares, padrões MVC
- `godot-gdscript` — Godot Engine, GDScript, sistemas de jogo

**IA e dados:**

- `langchain-langgraph` — LangChain, LangGraph, agents, RAG patterns
- `ml-fundamentals` — conceitos de ML, scikit-learn, pandas, numpy
- `data-engineering` — pipelines de dados, Spark, dbt, Airflow

**Design e produto:**

- `ux-design-patterns` — padrões de UX, acessibilidade, design systems
- `product-management` — frameworks de produto, PRDs, user stories, métricas

**Negócios e operações:**

- `startup-ops` — operações de startup, processos, frameworks de gestão
- `legal-tech-br` — contratos de software, LGPD, termos de uso (Brasil)
- `finance-basics` — fluxo de caixa, métricas SaaS, MRR, churn, LTV

**Especialidades verticais (futuramente):**

- `healthcare-tech` — regulamentações, HIPAA/LGPD saúde, sistemas hospitalares
- `fintech-br` — Open Finance, PIX, regulamentações do Bacen
- `ecommerce` — plataformas, logística, métricas de e-commerce

---

### Como o Data Store funciona tecnicamente

**Arquitetura:**

- Cada bucket é uma coleção LanceDB (ou Qdrant) pré-indexada pela equipe
  da Vectora Company
- Os buckets ficam em armazenamento centralizado — não são copiados para
  cada usuário, são consultados via busca vetorial compartilhada
- O usuário ativa buckets no seu perfil → esses buckets são incluídos nas
  buscas RAG das suas sessões

**Seleção de buckets:**

```
Dashboard → "Meus Workspaces de Conhecimento"

  Ativos:
  ✓ python-backend
  ✓ typescript-frontend
  ✓ langchain-langgraph

  Sugeridos pelo Vectora:
  "Você está trabalhando em um projeto Next.js + FastAPI.
   Quer ativar typescript-backend e databases?"
  [Ativar sugestões] [Ignorar]

  Disponíveis:
  ○ devops-cloud
  ○ godot-gdscript
  ○ ruby-rails
  ...
```

**Upload de dados do usuário (híbrido):**
Mesmo no Cloud, o usuário pode fazer upload de documentos próprios:

- Limite por plano (ex: 50MB no free, 500MB no Plus Cloud)
- Documentos ficam em bucket privado do usuário, isolados dos buckets públicos
- Processamento assíncrono (embedding em background)

---

### Sugestão automática de buckets pelo agente

O Vectora detecta o contexto da conversa e sugere buckets relevantes:

```python
# vectora/agents/orchestrator.py — lógica de sugestão

# Detecta stack a partir de arquivos no workspace ativo:
# package.json → sugere typescript-frontend, typescript-backend
# requirements.txt com langchain → sugere langchain-langgraph
# project.godot → sugere godot-gdscript

# Ou a partir do contexto da conversa:
# "estou construindo uma API em FastAPI" → sugere python-backend
```

No chat:

```
[Vectora]: Detectei que você está trabalhando com Python e LangChain.
Quer ativar os workspaces de conhecimento "python-backend" e
"langchain-langgraph"? Isso me dará contexto muito mais preciso
para te ajudar.

[Ativar] [Ver detalhes] [Não por agora]
```

---

### Planos do Vectora Cloud

| Plano      | Preço   | Créditos IA/mês  | Buckets Data Store | Upload privado |
| ---------- | ------- | ---------------- | ------------------ | -------------- |
| Free       | Grátis  | $2 em créditos   | 2 buckets          | 10MB           |
| Plus Cloud | $12/mês | $15 em créditos  | 10 buckets         | 200MB          |
| Pro Cloud  | $29/mês | $40 em créditos  | Ilimitado          | 2GB            |
| Team Cloud | $79/mês | $100 em créditos | Ilimitado + custom | 10GB           |

**BYOK opcional:** qualquer plano pode conectar API keys próprias para
créditos adicionais além do incluso. Ideal para power users que consomem
mais do que o incluso no plano.

---

### A questão da parceria para o Cloud

O Vectora Cloud envolve infraestrutura real, subsídio do plano gratuito e
créditos de IA incluídos — três custos que precisam ser cobertos além da
receita das assinaturas. Por isso, o Cloud **requer parceiros estratégicos**
antes de ser lançado.

**O que precisamos de parceiros:**

**Infraestrutura de computação:**

- Servidores para rodar as instâncias do Vectora Cloud
- Candidatos: **Hostinger** (VPS com preço competitivo no Brasil),
  **Hetzner** (melhor custo-benefício europeu com PoP no Brasil),
  **DigitalOcean** (programa para startups)
- O que negociar: créditos de infraestrutura para o plano gratuito em troca
  de co-marketing ("Vectora Cloud powered by Hostinger")

**Créditos de IA (LLM):**

- Os créditos incluídos nos planos Cloud precisam de margem — compramos
  tokens no atacado e repassamos aos usuários
- Candidatos: **Cohere** (já é parceiro estratégico planejado — créditos
  para embedding + Command como LLM padrão do Cloud),
  **Google** (Gemini via Google Cloud for Startups),
  **Anthropic** (programa de startups)
- O que negociar: créditos gratuitos ou com desconto de volume para
  subsidiar o plano gratuito

**Busca web:**

- **Tavily** (já é parceiro estratégico planejado) — créditos de busca
  para subsidiar usuários do plano gratuito

**Banco de dados e armazenamento:**

- **Supabase** (já usamos para billing — extensão natural para o Cloud)
- **Qdrant Cloud** (vector store gerenciado para os buckets do Data Store)

---

### Modelo de parceria para o Cloud

A proposta para cada parceiro segue a mesma lógica:

> "O Vectora Cloud vai expor [X] usuários às suas tecnologias. Em vez
> de esses usuários nunca descobrirem vocês, eles vão usar vocês no dia
> a dia via Vectora — e quando precisarem de mais, vão assinar diretamente.
> Em troca de créditos que subsidiam nosso plano gratuito, vocês ganham
> um canal de distribuição para um público qualificado."

**Para Cohere especificamente:**
O plano gratuito do Vectora Cloud usando Cohere Command como LLM padrão

- embedding + reranker = cada usuário gratuito é uma demonstração viva
  do produto Cohere. É mais eficiente que qualquer campanha de marketing.

---

### Sequência de lançamento do Cloud

O Cloud **não** é lançado junto com o self-hosted. A sequência correta:

```
Fase 1 (Ano 1): self-hosted estabelecido, base de usuários, receita
Fase 2 (Ano 2, Q1): Vectora Data Store lançado para self-hosted
  → usuários self-hosted podem ativar buckets de conhecimento prontos
  → sem custo adicional para planos Pro+ (validação do conceito)
Fase 3 (Ano 2, Q2): negociação de parcerias para Cloud
  → com base de usuários real para mostrar aos parceiros
Fase 4 (Ano 2, Q3-Q4): Vectora Cloud beta fechado
  → parceiros contribuem com infraestrutura e créditos
  → plano gratuito subsidiado
Fase 5 (Ano 3): Vectora Cloud público
  → plano gratuito aberto como canal de aquisição
  → conversão para planos pagos
```

**Por que Data Store vem antes do Cloud:**
O Data Store pode ser lançado para self-hosted sem precisar de parceiros —
é só hospedar os buckets em um servidor próprio e distribuir via API.
Isso valida o conceito (usuários querem isso?), gera feedback para melhorar
os buckets, e cria o ativo que torna o Cloud mais valioso.

---

## Impacto no Vectora Company Plan (revisão)

### Adições ao Bloco A (Legal)

- Termos de Uso precisam de seção específica de OEM License
- EULA separado para parceiros OEM com cláusulas de atribuição e revenue share

### Adições ao Bloco B (Billing)

- Novo plano `oem_starter`, `oem_growth`, `oem_scale` no Supabase + Stripe
- Campo `license_type` em `subscriptions`: `'standard' | 'oem' | 'cloud'`
- Monitoramento de volume de API calls por token para detecção de uso OEM

### Adições ao Bloco F (Site)

- Página `/oem` explicando o programa de licenciamento OEM
- Página `/cloud` com waitlist antes do lançamento (captura interesse)
- Página `/data-store` apresentando os buckets disponíveis

### Adições ao Bloco J (Marketing)

- Canal de aquisição OEM: DevRel em comunidades de builders (Indie Hackers,
  Product Hunt, grupos de SaaS BR)
- Waitlist do Cloud como campanha de pré-lançamento com parceiros

---

_Última atualização: planejamento inicial._
_Revisitar OEM quando API REST for lançada (Bloco Z do chat-first)._
_Revisitar Cloud quando self-hosted atingir 300+ usuários ativos._
