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


def test_generic_error_fallback():
    code, message = classify_stream_error(ValueError("algo inesperado"))
    assert code == "STREAM_ERROR"
    assert message
