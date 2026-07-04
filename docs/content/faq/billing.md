---
title: Billing
weight: 2
---

**Como funciona o billing?**
Trial/assinatura/licenciamento são geridos por `services.vectora.company`, um Worker Cloudflare pequeno — não um "Vectora Cloud" que hospeda sua instância. Pagamento internacional via Stripe; no Brasil, via Asaas (PIX, boleto, cartão).

**O que muda entre Free e Pro?**
Free é 100% local, sem conta. Pro desbloqueia chat web multi-usuário, storage complete (Postgres+Qdrant+Redis), webhooks e a API REST com rate limit maior — veja [preços atualizados](https://vectora.company/#pricing).

**Cancelar a assinatura apaga meus dados?**
Não. Seus dados ficam no **seu** servidor — cancelar a assinatura só rebaixa o tier de volta pra Free (recursos Pro deixam de funcionar), não deleta nada localmente.

**Onde vejo meu `VECTORA_TOKEN`?**
No [dashboard](https://vectora.company/dashboard), seção Token — pode ser revelado de novo sempre que precisar. Use "Rotacionar" só se suspeitar que ele vazou (invalida o token atual e gera um novo).

**Tem trial gratuito?**
Sim — verifique a duração e condições atuais na [página de preços](https://vectora.company/#pricing).
