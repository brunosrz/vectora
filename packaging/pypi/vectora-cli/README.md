# vectora-cli

CLI textual do Vectora — mirror público no PyPI do produto completo.

```bash
pip install vectora-cli
vectora setup          # configurar provider de IA + Cohere
vectora chat           # chat textual
vectora rag list       # gerencia coleções RAG
vectora config --set verbosity=2
```

## O que está dentro

- Chat textual no terminal (Rich / textual).
- RAG (LanceDB embarcado + Cohere reranker).
- Agente completo (orchestrator + coder + search + RAG).
- Subcomando `setup` interativo.

## O que **não** está dentro

`vectora server chat`, `vectora server mcp`, `vectora server headless`,
chat web e desktop. Para isso, baixe o instalador nativo (Win/macOS/Linux)
em **<https://vectora.company/download>**.

## Por quê?

O produto comercial Vectora distribui um binário Nuitka assinado + shell
Electron com auto-update, autenticação, billing e self-hosting completos.
Este mirror PyPI existe para devs que querem usar **apenas** o CLI textual
como ferramenta local, sem cadastro nem licença.

## Licença

Proprietary. Veja <https://vectora.company/terms>.
