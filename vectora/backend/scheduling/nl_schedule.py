"""Schedule — parser de linguagem natural (pt-BR) pra expressão cron.

MVP determinístico (regex), não um LLM call: cobre os padrões mais comuns
("todo dia às 9h", "toda segunda às 14:30", "a cada 2 horas") sem
depender de uma chamada de modelo extra nem introduzir não-determinismo
nos testes. Expressão fora desses padrões retorna `None` — o caller
(`schedule_task`) pede esclarecimento em vez de adivinhar (nunca cria um
agendamento errado silenciosamente).
"""

from __future__ import annotations

import re

_WEEKDAYS = {
    "domingo": 0,
    "segunda": 1,
    "segunda-feira": 1,
    "terça": 2,
    "terca": 2,
    "terça-feira": 2,
    "terca-feira": 2,
    "quarta": 3,
    "quarta-feira": 3,
    "quinta": 4,
    "quinta-feira": 4,
    "sexta": 5,
    "sexta-feira": 5,
    "sábado": 6,
    "sabado": 6,
}

_TIME_RE = r"(\d{1,2})(?:[:h](\d{2}))?h?"


class _InvalidTimeError(ValueError):
    """Horário reconhecido na expressão mas fora de faixa (0-23h/0-59min).

    Distinto de "nenhum horário presente" (que usa o default 9h) — um
    horário presente porém inválido não deve ser tratado como ausente,
    senão a expressão vira um agendamento silenciosamente errado."""


def _parse_time(text: str) -> tuple[int, int] | None:
    match = re.search(_TIME_RE, text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise _InvalidTimeError(f"horário fora de faixa: {hour}:{minute}")
    return hour, minute


def _parse_every_n(normalized: str) -> str | None:
    every_n = re.search(r"a cada (\d+)\s*(minuto|hora)s?", normalized)
    if not every_n:
        return None
    n = int(every_n.group(1))
    unit = every_n.group(2)
    limit = 60 if unit == "minuto" else 24
    if not (0 < n < limit):
        return None
    return f"*/{n} * * * *" if unit == "minuto" else f"0 */{n} * * *"


def _parse_weekly(normalized: str) -> str | None:
    weekday_match = re.search(
        r"toda(?:s)?\s+(domingo|segunda-feira|segunda|terça-feira|terça|terca-feira|"
        r"terca|quarta-feira|quarta|quinta-feira|quinta|sexta-feira|sexta|sábado|sabado)",
        normalized,
    )
    if not weekday_match:
        return None
    dow = _WEEKDAYS[weekday_match.group(1)]
    try:
        hour, minute = _parse_time(normalized) or (9, 0)
    except _InvalidTimeError:
        # Horário explícito fora de faixa ("toda segunda às 25h") — rejeita
        # a expressão inteira em vez de cair no default 9h silenciosamente.
        return None
    return f"{minute} {hour} * * {dow}"


def _parse_daily(normalized: str) -> str | None:
    if not re.search(r"todo(?:s)?\s+(os?\s+)?dias?", normalized):
        return None
    try:
        hour, minute = _parse_time(normalized) or (9, 0)
    except _InvalidTimeError:
        return None
    return f"{minute} {hour} * * *"


def parse_natural_schedule(when: str) -> str | None:
    """Converte uma expressão em linguagem natural pra cron de 5 campos.

    Padrões suportados:
    - "todo dia às 9h" / "todos os dias às 9:30" -> diário num horário fixo
    - "toda segunda às 14h" / "toda sexta-feira" -> semanal num dia fixo
    - "a cada N minutos" / "a cada N horas" -> intervalo fixo

    Retorna `None` (não adivinha) quando a expressão não casa com nenhum
    padrão reconhecido, incluindo string vazia.
    """
    normalized = when.strip().lower()
    if not normalized:
        return None

    for parser in (_parse_every_n, _parse_weekly, _parse_daily):
        try:
            result = parser(normalized)
        except _InvalidTimeError:
            return None
        if result is not None:
            return result
    return None
