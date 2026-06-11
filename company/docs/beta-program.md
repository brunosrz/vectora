# Vectora — Programa Beta com Feedback Recompensado

> Programa formal de teste fechado de features pré-lançamento. Recompensa
> feedback útil com tempo extra de assinatura ou acesso vitalício.
>
> **Por que existir:** Vectora ainda não foi lançado. Lançar features
> grandes (Helpdesk, Code Review, ia-plus, Host/Client, VSIX) sem
> usuários reais testando é apostar no escuro. Programa beta entrega
> três coisas simultaneamente: (1) produto refinado pela realidade,
> (2) case studies + testimonials para o lançamento público,
> (3) base de evangelistas orgânicos.
>
> **Premissa cardinal:** _"testes sem feedback são inúteis"_. Toda
> recompensa exige feedback estruturado validado humanamente. Sem isso,
> é apenas trial estendido — não é programa beta.

---

## Três tiers de participação

### 1. Beta Tester (entrada)

**O que faz:**

- Recebe acesso a uma feature em beta fechado
- Usa por pelo menos 14 dias
- Responde survey estruturado ao final (10–15 perguntas, ~20 min)

**Recompensa:**

- **+3 meses do plano atual** após validação do feedback
- Acesso público à feature 30 dias antes do lançamento geral

**Critérios de elegibilidade:**

- Cliente Plus ou Pro ativo há ≥ 30 dias
- Resposta a inscrição (formulário curto: cargo, stack, contexto)
- Aceite dos Termos do Beta (NDA leve)

**Capacidade por feature:** 50–100 slots

---

### 2. Power Tester (intermediário)

**O que faz:**

- Tudo do Beta Tester +
- Abre **3+ issues qualificadas** (com repro steps, contexto, severidade)
- Sugere **1 melhoria com proposta concreta** (não "fica bom" — proposta
  específica)
- Participa de **1 entrevista de 30 min** ao final do ciclo beta

**Recompensa:**

- **+12 meses do plano atual** após validação
- Selo público "Vectora Power Tester" (badge no perfil + reconhecimento
  em release notes)
- Acesso antecipado a TODAS as próximas betas (sem precisar se inscrever
  caso a caso)

**Critérios de elegibilidade:**

- Foi Beta Tester antes em pelo menos 1 ciclo, OU
- Cliente Pro ativo há ≥ 90 dias com histórico de uso significativo
  (medido por número de threads + tool calls)

**Capacidade por feature:** 10–20 slots

---

### 3. Founding User (vitalício)

**O que faz:**

- Tudo do Power Tester +
- Participa de **entrevistas mensais** com fundador (1h)
- Permite **case study público** com nome e empresa
- Disponibilidade para gravar 1 vídeo testimonial (5–10 min)
- Aceita ser citado em pitch deck, site e materiais comerciais
- Testa **TODAS** as betas, não apenas as de interesse

**Recompensa:**

- **Acesso vitalício ao plano Pro** (ou plano atual, o que for maior)
- Selo público "Founding User" + página dedicada no site (`vectora.company/founding`)
- Convite para Discord/Slack privado direto com fundador
- Influência real no roadmap (voto qualificado em decisões de produto)
- Camiseta + brinde físico (custo simbólico, valor simbólico)

**Critérios de elegibilidade:**

- Foi Power Tester em pelo menos 2 ciclos, OU
- Cliente Enterprise/OEM com uso comprovado de ≥ 6 meses, OU
- Convite direto do fundador
- Aceite de NDA mais rigoroso (não pode falar publicamente sobre features
  pré-anúncio)

**Capacidade global:** **máximo 50 founding users** (escassez deliberada
para manter exclusividade e qualidade do feedback)

**Quando atinge limite:** novos slots só abrem se um Founding User
deixar de cumprir (não participar de entrevistas mensais por 3 meses
seguidos = perda do status, mas mantém o acesso vitalício como
compensação histórica).

---

## Anti-gaming — como evitar feedback de baixa qualidade

### 1. Survey estruturado, não livre

Não aceitamos "ficou bom" ou "achei legal". Survey tem perguntas
obrigatórias:

```
1. Qual fluxo você executou primeiro? Descreva passo a passo.
2. Em qual ponto você ficou confuso ou travado? (se nenhum, escreva
   "nenhum" e justifique)
3. Qual feature você esperava que existisse e não existia?
4. Qual feature existe mas é difícil de descobrir/usar?
5. Você indicaria a feature ao seu time? Por quê (sim ou não)?
6. O que faria você cancelar o uso desta feature?
7. Compare com [feature equivalente em concorrente, se conhecer].
8. Estimativa de tempo economizado por semana (em horas).
9. Bugs encontrados (mesmo pequenos): liste todos.
10. Sugestão livre.
```

Surveys com respostas vazias ou superficiais (`"ok", "bom", "gostei"`)
são **rejeitadas** — recompensa não é liberada.

### 2. Validação humana

Cada feedback passa por revisão do fundador (ou de pessoa designada)
**antes** da recompensa ser creditada. Tempo médio: 7–14 dias após o
fim do ciclo beta.

Critério de aprovação:

- Respostas demonstram uso real (não preenchimento mecânico)
- Pelo menos 3 das 10 respostas são acionáveis (geram issue ou ajustam
  roadmap)
- Não há indício de bot ou múltiplas contas

### 3. Anti-duplicação

- 1 usuário = 1 inscrição por feature
- Múltiplas contas do mesmo CPF/CNPJ contam como 1
- IP/email duplicado dispara revisão manual

### 4. Power Tester: issues qualificadas

Issue qualificada precisa ter:

- Título descritivo (não "tá bugado")
- Steps to reproduce
- Comportamento esperado vs observado
- Severidade auto-classificada (crítico / alto / médio / baixo)
- Anexo (screenshot, logs, ou trace) quando aplicável

Issues que não cumprem o template são **devolvidas para ajuste** antes
de contarem.

---

## Operacionalização

### Lifecycle de uma beta

```
T-30 dias  │ Anúncio público no site + Discord + email para opt-in
T-21 dias  │ Inscrição abre (formulário Tally/Typeform)
T-14 dias  │ Inscrição fecha; seleção dos participantes
T-7 dias   │ Onboarding por email (link de instalação, doc beta, NDA)
T+0        │ Beta start: feature liberada
T+14 dias  │ Lembrete + survey intermediário (opcional, gamification)
T+30 dias  │ Beta end: feature continua disponível, survey obrigatório envia
T+45 dias  │ Validação dos feedbacks (fundador revisa)
T+60 dias  │ Recompensas creditadas + relatório agregado publicado
T+90 dias  │ Lançamento público da feature (com ajustes do beta)
```

### Onde os betas vivem

- **Página pública:** `vectora.company/beta` lista betas abertas, fechadas
  e próximas
- **Inscrição:** Tally form simples (sem login obrigatório)
- **Comunicação privada:** canal `#beta-<feature>` em Discord/Slack
- **Suporte direto:** fundador disponível 1h/semana em office hours via
  Google Meet
- **Issues:** repositório privado no GitHub `vectora-beta/<feature>` com
  acesso para os participantes

### Documentação por beta

Cada feature em beta tem um doc interno:

```
docs/betas/<feature-slug>.md

# Beta: <Nome da Feature>

## Objetivos do beta
- Validar fluxo X
- Medir adoção da feature Y
- Coletar feedback sobre UX Z

## Escopo
- O que está em beta
- O que NÃO está em beta (out of scope)
- Limitações conhecidas (não reportar como bug)

## Onboarding
- Como instalar / habilitar
- Tutorial rápido (5 min)
- Comandos / endpoints expostos

## Survey
- Link para survey
- Prazo de resposta

## Resultados (preenchido pós-beta)
- N participantes
- N feedbacks válidos
- N issues criadas
- N issues resolvidas antes do lançamento
- Mudanças significativas pré-lançamento
```

---

## Calendário pré-lançamento Vectora (proposta)

Antes do lançamento público (público geral), rodar betas das seguintes
features para garantir produto polido:

| Feature                        | Beta start | Beta end | Lançamento | Slots |
| ------------------------------ | ---------- | -------- | ---------- | ----- |
| **Storage backends (Pro)**     | Mês -6     | Mês -5   | Mês -4     | 30    |
| **Chat web multi-usuário**     | Mês -5     | Mês -4   | Mês -3     | 50    |
| **MCP Library + Native Tools** | Mês -4     | Mês -3   | Mês -2     | 80    |
| **IA+ (TTS/STT/image gen)**    | Mês -3     | Mês -2   | Mês -1     | 100   |
| **VSIX**                       | Mês -2     | Mês -1   | Mês 0      | 60    |
| **Vectora público geral**      | —          | —        | **Mês 0**  | ∞     |

**Volume total esperado de testers pré-lançamento:** ~300–400 pessoas
únicas (com sobreposição entre ciclos).

**ROI esperado:** ~30 Founding Users + ~50 Power Testers + ~200 Beta
Testers no momento do lançamento público. Cada um é um vetor potencial
de evangelização orgânica.

---

## Pós-lançamento — programa contínuo

Após o lançamento público, betas continuam para **toda feature nova
significativa**:

- Sprint M5 do ia-plus (image edit)
- Bloco H+ do plan (Deep Agents 2.0)
- Bloco L (SDKs externos)
- Tier 2A (VSIX se ainda em beta)
- Tier 2B (Host/Client)
- Tier 2C (cada plugin novo)
- Tier 3 (Helpdesk, Code Review — betas longos, 60+ dias)

Cadência típica: 1 beta start por mês após o lançamento, com 2–3 ciclos
ativos em paralelo.

---

## Aspectos legais

### NDA leve (Beta Tester)

Texto resumido:

- Você concorda em não fazer screenshots/vídeos públicos de features
  ainda não anunciadas
- Você pode falar publicamente que está em beta de algo Vectora, sem
  detalhar
- Você concorda em ser contatado para o survey final
- Você concorda que feedback enviado pode ser usado pelo Vectora
  livremente

Aceite via checkbox no formulário de inscrição.

### NDA mais rigoroso (Founding User)

Texto adicional:

- Você não pode discutir publicamente features pré-anúncio
- Você não pode compartilhar credenciais ou builds com terceiros
- Período: enquanto for Founding User ativo

Assinado eletronicamente via DocuSign/Clicksign.

### IP do feedback

- Feedback enviado é de propriedade do Vectora
- Ideias, sugestões e críticas podem ser implementadas livremente
- Sem compensação adicional além da recompensa estabelecida no tier
- Vectora pode citar nome/empresa do tester em release notes (com opt-in
  via checkbox)

### Cancelamento de assinatura

- Recompensa em meses extras é creditada na conta. Se o usuário cancelar,
  o saldo permanece — pode ser usado depois (com prazo de validade de 24
  meses).
- Founding User vitalício: se a empresa for vendida ou descontinuada,
  obrigação se transfere para sucessor. Documentado em contrato.

---

## Métricas de saúde do programa

Acompanhar mensalmente:

| Métrica                                 | Meta             | Por quê                                     |
| --------------------------------------- | ---------------- | ------------------------------------------- |
| Inscritos / slots disponíveis           | ≥ 3×             | Indica demanda; permite seleção qualitativa |
| Survey completion rate                  | ≥ 70%            | Sub-meta indica problema de engajamento     |
| Feedbacks aprovados / enviados          | ≥ 80%            | Sub-meta indica problema de qualidade       |
| Bugs reportados → resolvidos pré-launch | ≥ 60%            | Indica que beta está cumprindo função       |
| Founding Users ativos                   | ≥ 40 (de 50 max) | Sub-meta indica churn ou seleção ruim       |
| NPS médio dos beta testers              | ≥ 50             | Indicador de qualidade percebida            |

Métricas baixas dispararão revisão do programa (formato dos surveys,
critérios de seleção, tipo de recompensa).

---

## Erros a evitar

Lições de programas beta de outros produtos que vamos **não repetir**:

1. **Beta perpétuo** — feature em beta por > 6 meses sem decisão de
   lançamento ou kill é sinal de produto sem direção. Cada beta tem
   prazo fechado.

2. **Feedback sem ação visível** — tester reportar bug e nunca ver
   resposta mata engajamento. Toda issue qualificada recebe
   acknowledge em ≤ 7 dias.

3. **Recompensa em produto que o tester não usa** — dar "1 ano de
   Vectora Plus" para empresa que já é Pro não vale. Recompensa é em
   meses do plano **atual** ou superior.

4. **Selecionar amigos** — bias confirmatório destrói o programa.
   Critério de seleção é objetivo (uso real, cargo, contexto) e
   transparente.

5. **Burnout do fundador** — entrevistas mensais com 50 Founding Users
   = 50h/mês. Insustentável solo. Quando o programa crescer, contratar
   community manager part-time.

6. **NDA pesado demais** — vira atrito. NDA leve é checkbox; NDA
   pesado é só para Founding User.

7. **Mistura de betas público + fechado** — confunde marketing. Beta
   fechado é privado até o anúncio público de "feature lançada".
