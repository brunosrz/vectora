---
title: Billing
weight: 2
---

**¿Cómo funciona la facturación?**
El trial/suscripción/licenciamiento son gestionados por `services.vectora.company`, un pequeño Cloudflare Worker — no una "Vectora Cloud" que aloja tu instancia. Pago internacional vía Stripe; en Brasil, vía Asaas (PIX, boleto, tarjeta).

**¿Qué cambia entre Free y Pro?**
Free es 100% local, sin cuenta. Pro desbloquea chat web multiusuario, almacenamiento completo (Postgres+Qdrant+Redis) y automatizaciones disparadas por webhook — ver [precios actuales](https://vectora.company/#pricing).

**¿Cancelar mi suscripción borra mis datos?**
No. Tus datos permanecen en **tu** servidor — cancelar la suscripción solo baja el nivel de vuelta a Free (las funciones Pro dejan de funcionar), no borra nada localmente.

**¿Dónde veo mi `VECTORA_TOKEN`?**
En el [dashboard](https://vectora.company/dashboard), sección Token — puedes revelarlo de nuevo cuando lo necesites. Usa "Rotar" solo si sospechas que se filtró (invalida el token actual y genera uno nuevo).

**¿Hay un trial gratis?**
Sí — consulta la duración y términos actuales en la [página de precios](https://vectora.company/#pricing).
