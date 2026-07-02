**BRUNO SOARES**

Software Engineer | Arquiteto de Sistemas de IA | Python & LLM Specialist

\+55 (35) 91017-9164 • [bruno.soarxz@gmail.com](mailto:bruno.soarxz@gmail.com) • [github.com/brunosrz](https://github.com/brunosrz)

**RESUMO PROFISSIONAL**

Engenheiro de software full stack com 6 anos de experiência em arquitetura de sistemas e produtos de IA/LLM production-grade. Projeta e constrói, de ponta a ponta, ecossistemas completos — backend em Python/FastAPI, frontend em TypeScript/React, orquestração de agentes com LangChain/LangGraph, infraestrutura distribuída na Cloudflare (Durable Objects) e empacotamento desktop (Electron/Nuitka). Autor único do Vectora, produto de IA registrado como marca, e do Ability System, framework open source de gameplay de alta performance para Godot Engine em C++. Combina profundidade técnica em sistemas distribuídos e IA aplicada com autonomia total sobre decisões de arquitetura, do design ao deploy.

**STACK TÉCNICO**

- **Python —** FastAPI, LangChain, LangGraph, FastMCP, Deep Agents, RAG (Cohere embeddings \+ reranking). Orquestração de agentes, pipelines de recuperação semântica e APIs de alta performance.

- **TypeScript / Bun —** Hono, Next.js, React 19, Vite, TanStack (Query, Router), Tailwind CSS. Microsserviços, SPAs e dashboards de produção.

- **Infraestrutura & Cloud —** Cloudflare Workers/Durable Objects (arquitetura distribuída stateful), Docker, GitHub Actions, Jenkins, VPS.

- **Dados —** PostgreSQL, Redis, LanceDB / vetores para RAG e busca semântica.

- **Desktop / Packaging —** Electron, Nuitka (compilação Python → binário nativo).

- **Integrações —** Google APIs, OAuth, Asaas (pagamentos), Resend (e-mail transacional).

**PROJETOS DESTACADOS**

**Vectora** _| Produto de IA proprietário (marca registrada) — Founder & Engenheiro_

Copiloto de produtividade e engine de IA multi-agent, construído e mantido inteiramente sozinho — da arquitetura ao deploy. Vectora não é uma aplicação isolada, mas um ecossistema completo composto por: aplicativo desktop (Electron \+ Nuitka), site institucional com criação de conta, assinatura e cobrança recorrente (7 idiomas), portal de documentação (uso do produto e da API REST pública /v1, que expõe o Vectora como engine/núcleo para projetos de terceiros) e dois serviços de borda publicados na Cloudflare — um relay stateful (Durable Objects) que viabiliza OAuth local com GitHub e outros provedores, e um servidor de atualização (update server) para distribuição de releases do app desktop.

- **Arquitetura de produto:** projetei e implementei o ecossistema completo (app \+ site \+ docs \+ 2 serviços cloud) sozinho, tomando todas as decisões técnicas — da escolha de stack à infraestrutura distribuída.

- **Arquitetura de agente:** motor multi-agent construído sobre o padrão deep-agent (LangGraph) — subagents especializados, middleware human-in-the-loop para ações sensíveis e checkpointer para persistência de estado de conversa, com RAG híbrido (dense \+ BM25 sparse) e reranking Cohere para maximizar a precisão do contexto entregue aos agentes.

- **Context Graph:** motor complementar ao RAG baseado em análise estática (parsing AST via tree-sitter, múltiplas linguagens) para mapear dependências e propagação de informação no código-fonte.

- **Modelo de negócio e billing:** projetei e implementei o enforcement de assinatura de ponta a ponta — tiers free/pro reais gated no backend (HTTP 402 Payment Required), rate limiting diferenciado por tier, e cobrança dual-provider (Stripe internacional, Asaas Brasil/Pix) com reconciliação de estado via webhooks assinados.

- **Workbenches integrados:** arquivos, git, planos, tarefas em segundo plano, preview, memória (visualização do RAG), context graph e terminal (xterm) com editor Monaco — um ambiente de desenvolvimento assistido por IA completo, não apenas um chat.

- **Infraestrutura distribuída:** dois serviços de borda na Cloudflare desacoplados do core local-first do produto — relay stateful via Durable Objects e update server via Worker.

- **Qualidade e testes:** ~2.400 testes automatizados no backend Python \+ suíte dedicada no frontend, com TDD como prática obrigatória (bug vira teste antes do fix; feature vira teste antes da implementação).

- **Execução:** produto desenvolvido 100% individualmente, incluindo definição de escopo, arquitetura, implementação e operação — trabalho equivalente ao de uma equipe multidisciplinar (backend, frontend, infra, produto).

**Tecnologias:** Python (FastAPI, LangChain, LangGraph, Deep Agents), TypeScript (React, Vite, TanStack Query/Router, Tailwind), PostgreSQL, Redis, LanceDB, Cohere, tree-sitter, MCP, Stripe, Electron, Nuitka, Cloudflare Workers/Durable Objects, Docker, GitHub Actions

**Ability System** _| Framework open source para Godot 4.x — Autor_

Framework orientado a dados (data-driven) de alta performance em C++/GDExtension para sistemas de habilidades em jogos. Implementa um sistema hierárquico de propagação de informação via Tags (estados, condicionais e eventos), fases de execução (Windup/Execution/Recovery), injeção de física via áreas de colisão e suporte nativo a multiplayer com predição de cliente e rollback baseado em cache de estado circular (128 ticks). Escopo e profundidade técnica equivalentes a um projeto que, em contexto corporativo, exigiria uma equipe dedicada por múltiplos semestres — entregue sozinho em 3 meses.

- **Sistema de propagação de estado:** arquitetura de Tags hierárquicas (NAME/CONDITIONAL/EVENT) com histórico, permitindo reagir e propagar informação de gameplay de forma desacoplada entre sistemas.

- **Networking:** suporte nativo a multiplayer com predição de cliente e rollback, usando cache de estado circular para 128 ticks — engenharia de sincronização de estado sob latência.

- **API extensa:** Resources desacoplados de Specs de runtime, permitindo composição e extensão do sistema sem alterar o core.

**Tecnologias:** C++, Godot 4.x, GDExtension

**ClinicFlow** _| Sistema full stack de agendamento para clínicas estéticas — Projeto freelance_

Sistema completo de gestão de agendamentos, com vitrine pública de serviços, fluxo de pagamento (sandbox Asaas — Pix/débito/crédito), dashboard administrativo e integração em tempo real com Google Calendar API, entregue como solução operacional pronta para uso por um cliente real.

- **Autenticação e segurança:** sessão JWT, proteção de rotas e validação de dados com Zod em todo o fluxo de agendamento e pagamento.

- **Integração externa:** sincronização bidirecional com Google Calendar API, permitindo acesso direto de cada evento agendado na agenda do cliente.

**Tecnologias:** Next.js, TypeScript, Hono, Tailwind CSS, Zod, JWT, Google Calendar API, Asaas, Resend, SQLite
