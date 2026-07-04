---
title: BYOK & Privacidade
weight: 4
---

## O que "self-hosted" garante de verdade

Seus dados nunca passam por um servidor intermediário da Vectora Company. O agente conecta **direto** às APIs que você configurou (Gemini, OpenAI, Anthropic, Cohere, Tavily) e aos MCP servers que você instalou. A Vectora Company não vê o conteúdo das suas conversas, seu código, ou seus arquivos.

## O que isso não significa

Self-hosted **não é** criptografia ponta-a-ponta no sentido de SaaS clássico. O servidor que roda o Vectora (seu servidor) precisa ver o conteúdo em claro pra chamar o LLM e indexar no RAG — não existe forma de processar conteúdo homomorficamente cifrado com LLMs hoje. Se você acessa seu próprio Vectora numa VPS a partir de casa, os dados são protegidos por TLS no caminho, hash forte de senha, JWT assinado, vault AES-256 pra secrets — mas **não** há criptografia tal que você mesmo (operador da VPS) não consiga ler suas próprias conversas. Esse não é o modelo de ameaça.

## BYOK (Bring Your Own Key)

Free e Pro funcionam com suas próprias chaves de API — LLM, Cohere/VoyageAI (embeddings), Tavily (busca web). Vectora nunca vê nem armazena essas chaves em texto puro (ficam no [vault](../secrets-vault)); a chamada de API acontece direto do seu servidor pro provedor escolhido.

## LGPD/GDPR

A responsabilidade pelo tratamento de dados enviados a providers de LLM/embedding é entre **você** (operador) e **cada provider conectado** — o Vectora não é parte dessa relação de dados. Os Termos de Uso da Vectora Company descrevem exatamente o que trafega em cada integração.

## Auditoria

Clientes Pro+ recebem o binário compilado e documentação completa de arquitetura. Auditoria de código-fonte sob NDA está disponível pra clientes Enterprise.
