---
title: Security
weight: 3
---

**Does my data leave my server?**
Not to Vectora Company's backend. It only goes out to the APIs you configured yourself (LLM, Cohere/Voyage, Tavily) and to MCP servers you installed.

**Does Vectora have end-to-end encryption?**
Not in the classic SaaS sense — see [BYOK & Privacy](../../security/byok-privacy) for the full threat model. Passwords are Argon2id, secrets live in an AES-256 vault, but conversation content stays in the clear on your own server (which you operate).

**How does Vectora handle prompt injection?**
Content coming from tools (files read, web pages, function call results) does **not** carry the authority of a direct user message. When that content contains a high-impact instruction (delete, exfiltrate, run a script), the agent stops and asks before acting.

**Can I restrict what the agent can do?**
Yes — permission modes (always ask / accept edits / autonomous / plan), per-MCP-server tool policy, global tool toggles for admins, and the per-workspace trust folder mechanism.

**Where do I report a vulnerability?**
`security@vectora.company`, with responsible disclosure.
