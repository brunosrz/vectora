---
title: Segurança
weight: 3
---

**Meus dados saem do meu servidor?**
Não pro backend da Vectora Company. Eles saem só pras APIs que você mesmo configurou (LLM, Cohere/Voyage, Tavily) e pra MCP servers que você instalou.

**O Vectora tem criptografia ponta-a-ponta?**
Não no sentido de SaaS clássico — veja [BYOK & Privacidade](../../security/byok-privacy) pro modelo de ameaça completo. Senhas são Argon2id, secrets ficam num vault AES-256, mas o conteúdo das conversas fica em claro no seu próprio servidor (que é operado por você).

**Como o Vectora lida com prompt injection?**
Conteúdo vindo de tools (arquivos lidos, páginas web, resultados de function calls) **não** tem autoridade de mensagem direta do usuário. Quando esse conteúdo contém uma instrução de alto impacto (deletar, exfiltrar, executar script), o agente para e pergunta antes de agir.

**Posso restringir o que o agente pode fazer?**
Sim — modos de permissão (perguntar sempre / aceitar edições / autônomo / plano), tool policy por servidor MCP, toggle de tools globais pra admin, e o mecanismo de trust folder por workspace.

**Onde reporto uma vulnerabilidade?**
`security@vectora.company`, com divulgação responsável.
