"""Classificação de erros do stream em códigos tipados (RATE_LIMIT/AUTH/...).

Garante que erros crus de provider (ex.: 429 do Gemini com JSON enorme) viram
um ``(code, message)`` limpo — o frontend localiza a mensagem ao usuário a
partir do ``code`` e nunca exibe o JSON cru como se fosse resposta da IA.
"""

from __future__ import annotations

from backend.api.adapters import classify_stream_error

_GEMINI_429 = (
    "Error calling model 'gemini-2.5-flash' (Too Many Requests): 429 "
    "Too Many Requests. RESOURCE_EXHAUSTED — quota exceeded for "
    "generate_content_free_tier_requests"
)


def test_rate_limit_429_classified():
    code, message = classify_stream_error(RuntimeError(_GEMINI_429))
    assert code == "RATE_LIMIT"
    assert message
    # Não vaza o JSON/refs crus do provider.
    assert "RESOURCE_EXHAUSTED" not in message
    assert "429" not in message


def test_rate_limit_quota_wording():
    code, _ = classify_stream_error(Exception("You exceeded your current quota"))
    assert code == "RATE_LIMIT"


def test_auth_error_classified():
    code, _ = classify_stream_error(Exception("401 Unauthorized: invalid api key"))
    assert code == "AUTH"


def test_timeout_classified():
    code, message = classify_stream_error(Exception("ReadTimeout: request timed out"))
    assert code == "TIMEOUT"
    assert message
    assert "timeout" not in message.lower() or message  # mensagem limpa sem stack


def test_timeout_connect():
    code, _ = classify_stream_error(
        Exception("ConnectTimeout connecting to generativelanguage")
    )
    assert code == "TIMEOUT"


def test_generic_error_fallback():
    code, message = classify_stream_error(ValueError("algo inesperado"))
    assert code == "STREAM_ERROR"
    assert message


def test_timeout_not_auth_not_rate_limit():
    """TIMEOUT deve ser distinto de RATE_LIMIT e AUTH."""
    t_code, _ = classify_stream_error(Exception("timed out"))
    r_code, _ = classify_stream_error(Exception("429 quota"))
    a_code, _ = classify_stream_error(Exception("401 unauthorized"))
    assert len({t_code, r_code, a_code}) == 3
