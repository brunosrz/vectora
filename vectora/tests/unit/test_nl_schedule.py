"""Schedule — parser determinístico de linguagem natural pra cron.

Erro/borda: expressão ambígua/vazia/fora dos padrões suportados nunca é
adivinhada — retorna None, e quem chama pede esclarecimento.
"""

from __future__ import annotations

from backend.scheduling.nl_schedule import parse_natural_schedule


def test_daily_with_explicit_time():
    assert parse_natural_schedule("todo dia às 9h") == "0 9 * * *"
    assert parse_natural_schedule("todos os dias às 14:30") == "30 14 * * *"


def test_daily_without_time_defaults_to_9am():
    assert parse_natural_schedule("todo dia") == "0 9 * * *"


def test_weekly_on_weekday_with_time():
    assert parse_natural_schedule("toda sexta-feira às 18h") == "0 18 * * 5"
    assert parse_natural_schedule("toda segunda às 8:15") == "15 8 * * 1"


def test_weekly_without_time_defaults_to_9am():
    assert parse_natural_schedule("toda quinta") == "0 9 * * 4"


def test_interval_minutes_and_hours():
    assert parse_natural_schedule("a cada 15 minutos") == "*/15 * * * *"
    assert parse_natural_schedule("a cada 2 horas") == "0 */2 * * *"


def test_empty_string_returns_none_not_a_guess():
    assert parse_natural_schedule("") is None
    assert parse_natural_schedule("   ") is None


def test_ambiguous_expression_returns_none():
    # "daqui 2 horas" é execução única, não recorrente — fora do escopo do
    # parser (cron não expressa "uma vez"); não deve inventar uma
    # recorrência errada.
    assert parse_natural_schedule("daqui 2 horas") is None
    assert parse_natural_schedule("quando der") is None


def test_interval_zero_or_out_of_range_is_rejected():
    assert parse_natural_schedule("a cada 0 minutos") is None
    assert parse_natural_schedule("a cada 60 minutos") is None
    assert parse_natural_schedule("a cada 24 horas") is None
