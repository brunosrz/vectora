---
title: POST /v1/classify
weight: 2
---

Classifica um texto em uma ou mais labels fornecidas, usando `response_format` estruturado do deep-agent (auto-detecta `ProviderStrategy` nativo do modelo ou `ToolStrategy` como fallback).

## Request

```json
{
  "text": "O app trava toda vez que eu tento exportar um PDF",
  "labels": ["bug", "feature-request", "pergunta", "elogio"],
  "multi_label": false,
  "description": "Categoriza feedback de usuário"
}
```

| Campo         | Tipo     | Obrigatório          | Descrição                                        |
| ------------- | -------- | -------------------- | ------------------------------------------------ |
| `text`        | string   | Sim                  | Texto a classificar                              |
| `labels`      | string[] | Sim                  | 2 ou mais labels possíveis                       |
| `multi_label` | bool     | Não (padrão `false`) | Se `true`, permite mais de uma label na resposta |
| `description` | string   | Não                  | Contexto adicional pra guiar a classificação     |

## Response

```json
{
  "label": "bug",
  "confidence": 0.94,
  "labels": [],
  "reasoning": "Menciona travamento consistente numa ação específica (exportar PDF)",
  "strategy": "auto"
}
```

| Campo        | Tipo           | Descrição                                                         |
| ------------ | -------------- | ----------------------------------------------------------------- |
| `label`      | string         | Label mais provável                                               |
| `confidence` | float          | 0.0–1.0                                                           |
| `labels`     | string[]       | Todas as labels aplicáveis (só preenchido se `multi_label: true`) |
| `reasoning`  | string \| null | Justificativa da classificação                                    |
| `strategy`   | string         | Estratégia usada internamente (`provider` ou `tool`)              |

## Rate limit

10/min (Free) ou 100/min (Pro) — veja [Visão Geral](../overview).
