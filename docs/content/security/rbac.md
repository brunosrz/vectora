---
title: RBAC & Permissões
weight: 2
---

## Papéis (roles)

| Papel    | Descrição                                                                       |
| -------- | ------------------------------------------------------------------------------- |
| `root`   | primeiro usuário cadastrado na instância; acesso total, incluindo Administração |
| `admin`  | gerencia usuários, tools globais, pastas seguras e configuração do servidor     |
| `member` | uso normal do chat, workspaces e workbench                                      |
| `viewer` | acesso somente leitura                                                          |

Gerenciado em **Configurações → Administração → Usuários**, com convites por email/link e TTL configurável (1–720h).

## Tool policy (ABAC)

Além do papel, cada tool pode ser habilitada/desabilitada globalmente (**Configurações → Administração → Ferramentas**) ou por servidor MCP individual (**Configurações → Ambiente → Plugins → Tool Policy**) — controle de acesso baseado em atributo, não só em papel.

## Trust folder

Independente de RBAC, cada **workspace** tem seu próprio estado de confiança — um `member` com acesso normal ainda precisa confiar explicitamente numa pasta antes do agente poder escrever nela ou rodar comandos. Veja [Primeiro workspace](../../getting-started/first-workspace).

## Pastas seguras

Administradores podem marcar caminhos específicos como **pastas seguras**, exigindo aprovação extra mesmo depois de confiados — útil em servidores compartilhados onde nem todo `member` deveria ter acesso irrestrito a certos diretórios.

## Veja também

- [Autenticação](../authentication)
- [Usando as configurações](../../guides/using-settings) — aba Administração em detalhe
