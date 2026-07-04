---
title: Billing
weight: 2
---

**How does billing work?**
Trial/subscription/licensing are managed by `services.vectora.company`, a small Cloudflare Worker — not a "Vectora Cloud" hosting your instance. International payment via Stripe; in Brazil, via Asaas (PIX, boleto, card).

**What changes between Free and Pro?**
Free is 100% local, no account. Pro unlocks multi-user web chat, complete storage (Postgres+Qdrant+Redis), webhooks, and the REST API with a higher rate limit — see [current pricing](https://vectora.company/#pricing).

**Does canceling my subscription delete my data?**
No. Your data stays on **your** server — canceling the subscription only downgrades the tier back to Free (Pro features stop working), it doesn't delete anything locally.

**Where do I see my `VECTORA_TOKEN`?**
In the [dashboard](https://vectora.company/dashboard), Token section — you can reveal it again anytime you need. Use "Rotate" only if you suspect it leaked (invalidates the current token and generates a new one).

**Is there a free trial?**
Yes — check current duration and terms on the [pricing page](https://vectora.company/#pricing).
