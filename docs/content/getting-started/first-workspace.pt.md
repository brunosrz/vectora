---
title: Primeiro Workspace
weight: 5
---

Um **workspace** é uma pasta do seu sistema de arquivos registrada no Vectora. É a unidade em torno da qual o agente organiza contexto: RAG, Context Graph, git, terminal e o editor de arquivos operam dentro do workspace ativo.

## Adicionar um workspace

No seletor de workspace (topo do chat), escolha "Adicionar workspace" e aponte pra uma pasta local. Não existe limite de workspaces registrados — troque entre eles a qualquer momento sem perder o histórico de conversas.

## Confiar em uma pasta

Por padrão, um workspace recém-adicionado é **não confiável**: o agente pode ler arquivos, mas **não** pode escrever, rodar comandos no terminal, nem executar git. Isso existe pra evitar que o agente rode comandos arbitrários numa pasta que você só quis abrir pra consulta.

Clique em "Confio nesta pasta" pra liberar:

- Escrita de arquivos (`file_write`, `file_edit`)
- Terminal (PTY real)
- Operações git que alteram estado (commit, push, checkout)

A confiança é por pasta, não global — abrir uma pasta nova sempre começa não confiável.

## Pastas seguras (admin)

Administradores podem configurar uma lista de **pastas seguras** em **Configurações → Administração → Pastas Seguras** — caminhos que exigem aprovação extra mesmo depois de confiados, útil pra proteger diretórios sensíveis num servidor compartilhado.

## Git

Se a pasta já é um repositório git, o Vectora detecta automaticamente e habilita a aba **Diff (Git)** na workbench. Se não for, você pode pedir ao agente pra rodar `git init`, ou fazer isso você mesmo antes de confiar na pasta.

## `.vectoraignore`

Um arquivo `.vectoraignore` na raiz do workspace (mesma sintaxe de `.gitignore`) esconde caminhos do Vectora inteiro — RAG, Context Graph, filesystem e chat. Use pra excluir `node_modules/`, builds, secrets, etc.

## Próximo passo

→ [Usando o chat](../../guides/using-the-chat)
