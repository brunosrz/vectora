"""Sprint 7 — Tools nativas utilitárias (backend/tools/native/).

Cobre caminho feliz + erro para cada uma das 8 tools:
time_now, time_parse, http_request, hash_text, jwt_decode,
base64_encode, regex_test, json_query.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

# ---------------------------------------------------------------------------
# time_now
# ---------------------------------------------------------------------------


class TestTimeNow:
    @pytest.mark.asyncio
    async def test_returns_iso_string_utc(self) -> None:
        from backend.tools.native.time import time_now

        result = await time_now.ainvoke({"timezone": "UTC"})
        assert isinstance(result, str)
        assert "T" in result  # ISO 8601

    @pytest.mark.asyncio
    async def test_default_timezone_is_utc(self) -> None:
        from backend.tools.native.time import time_now

        result = await time_now.ainvoke({})
        assert "T" in result

    @pytest.mark.asyncio
    async def test_invalid_timezone_returns_error(self) -> None:
        from backend.tools.native.time import time_now

        result = await time_now.ainvoke({"timezone": "Invalid/Zone"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# time_parse
# ---------------------------------------------------------------------------


class TestTimeParse:
    @pytest.mark.asyncio
    async def test_iso_date_parses(self) -> None:
        from backend.tools.native.time import time_parse

        result = await time_parse.ainvoke({"text": "2024-01-15T10:30:00Z"})
        assert "2024" in result
        assert result.startswith("error:") is False

    @pytest.mark.asyncio
    async def test_date_only_parses(self) -> None:
        from backend.tools.native.time import time_parse

        result = await time_parse.ainvoke({"text": "2024-01-15"})
        assert "2024" in result

    @pytest.mark.asyncio
    async def test_invalid_date_returns_error(self) -> None:
        from backend.tools.native.time import time_parse

        result = await time_parse.ainvoke({"text": "not a date at all $$$$"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# hash_text
# ---------------------------------------------------------------------------


class TestHashText:
    @pytest.mark.asyncio
    async def test_sha256_hash(self) -> None:
        from backend.tools.native.hash import hash_text

        result = await hash_text.ainvoke({"text": "hello", "algorithm": "sha256"})
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    @pytest.mark.asyncio
    async def test_md5_hash(self) -> None:
        from backend.tools.native.hash import hash_text

        result = await hash_text.ainvoke({"text": "world", "algorithm": "md5"})
        expected = hashlib.md5(b"world").hexdigest()  # noqa: S324
        assert result == expected

    @pytest.mark.asyncio
    async def test_sha512_hash(self) -> None:
        from backend.tools.native.hash import hash_text

        result = await hash_text.ainvoke({"text": "x", "algorithm": "sha512"})
        assert len(result) == 128  # sha512 hex = 128 chars

    @pytest.mark.asyncio
    async def test_invalid_algorithm_returns_error(self) -> None:
        from backend.tools.native.hash import hash_text

        result = await hash_text.ainvoke({"text": "x", "algorithm": "zzz"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# base64_encode
# ---------------------------------------------------------------------------


class TestBase64Encode:
    @pytest.mark.asyncio
    async def test_encode(self) -> None:
        from backend.tools.native.base64_tool import base64_encode

        result = await base64_encode.ainvoke({"text": "hello", "operation": "encode"})
        assert result == base64.b64encode(b"hello").decode()

    @pytest.mark.asyncio
    async def test_decode(self) -> None:
        from backend.tools.native.base64_tool import base64_encode

        encoded = base64.b64encode(b"world").decode()
        result = await base64_encode.ainvoke({"text": encoded, "operation": "decode"})
        assert result == "world"

    @pytest.mark.asyncio
    async def test_invalid_decode_returns_error(self) -> None:
        from backend.tools.native.base64_tool import base64_encode

        result = await base64_encode.ainvoke(
            {"text": "!!!not_valid_base64!!!", "operation": "decode"}
        )
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# regex_test
# ---------------------------------------------------------------------------


class TestRegexTest:
    @pytest.mark.asyncio
    async def test_match_found(self) -> None:
        from backend.tools.native.regex import regex_test

        result = await regex_test.ainvoke({"pattern": r"\d+", "text": "abc123def"})
        data = json.loads(result)
        assert data["matched"] is True
        assert "123" in data.get("matches", [])

    @pytest.mark.asyncio
    async def test_no_match(self) -> None:
        from backend.tools.native.regex import regex_test

        result = await regex_test.ainvoke({"pattern": r"\d{5}", "text": "abc"})
        data = json.loads(result)
        assert data["matched"] is False

    @pytest.mark.asyncio
    async def test_invalid_pattern_returns_error(self) -> None:
        from backend.tools.native.regex import regex_test

        result = await regex_test.ainvoke({"pattern": "[invalid(", "text": "abc"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# json_query
# ---------------------------------------------------------------------------


class TestJsonQuery:
    @pytest.mark.asyncio
    async def test_simple_key(self) -> None:
        from backend.tools.native.json_query import json_query

        obj = json.dumps({"name": "Alice", "age": 30})
        result = await json_query.ainvoke({"json_text": obj, "path": "name"})
        assert result == "Alice"

    @pytest.mark.asyncio
    async def test_nested_key(self) -> None:
        from backend.tools.native.json_query import json_query

        obj = json.dumps({"a": {"b": {"c": 42}}})
        result = await json_query.ainvoke({"json_text": obj, "path": "a.b.c"})
        assert result == "42"

    @pytest.mark.asyncio
    async def test_array_index(self) -> None:
        from backend.tools.native.json_query import json_query

        obj = json.dumps({"items": [10, 20, 30]})
        result = await json_query.ainvoke({"json_text": obj, "path": "items[1]"})
        assert result == "20"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self) -> None:
        from backend.tools.native.json_query import json_query

        result = await json_query.ainvoke({"json_text": "not json {{{", "path": "key"})
        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_missing_key_returns_error(self) -> None:
        from backend.tools.native.json_query import json_query

        obj = json.dumps({"x": 1})
        result = await json_query.ainvoke({"json_text": obj, "path": "missing"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# jwt_decode
# ---------------------------------------------------------------------------


class TestJwtDecode:
    @pytest.mark.asyncio
    async def test_decode_hs256_payload(self) -> None:
        import jwt

        from backend.tools.native.jwt_tool import jwt_decode

        token = jwt.encode(
            {"sub": "user1", "role": "admin"}, "secret", algorithm="HS256"
        )
        result = await jwt_decode.ainvoke({"token": token})
        data = json.loads(result)
        assert data.get("sub") == "user1"
        assert data.get("role") == "admin"

    @pytest.mark.asyncio
    async def test_malformed_token_returns_error(self) -> None:
        from backend.tools.native.jwt_tool import jwt_decode

        result = await jwt_decode.ainvoke({"token": "not.a.token.at.all"})
        assert result.startswith("error:")


# ---------------------------------------------------------------------------
# http_request
# ---------------------------------------------------------------------------


class TestHttpRequest:
    @pytest.mark.asyncio
    async def test_get_returns_body(self, monkeypatch) -> None:
        import httpx

        from backend.tools.native.http import http_request

        class _FakeResponse:
            status_code = 200
            text = '{"ok": true}'

            def raise_for_status(self) -> None:
                pass

        class _FakeClient:
            async def __aenter__(self) -> _FakeClient:
                return self

            async def __aexit__(self, *_: object) -> None:
                pass

            async def request(self, *_: object, **__: object) -> _FakeResponse:
                return _FakeResponse()

        monkeypatch.setattr(httpx, "AsyncClient", lambda **_kw: _FakeClient())
        result = await http_request.ainvoke(
            {"url": "https://example.com/api", "method": "GET"}
        )
        data = json.loads(result)
        assert data["status"] == 200
        assert "ok" in data.get("body", "")

    @pytest.mark.asyncio
    async def test_connection_error_returns_error(self, monkeypatch) -> None:
        import httpx

        from backend.tools.native.http import http_request

        class _ErrorClient:
            async def __aenter__(self) -> _ErrorClient:
                return self

            async def __aexit__(self, *_: object) -> None:
                pass

            async def request(self, *_: object, **__: object) -> None:
                raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx, "AsyncClient", lambda **_kw: _ErrorClient())
        result = await http_request.ainvoke(
            {"url": "https://bad-host.invalid/", "method": "GET"}
        )
        assert result.startswith("error:")
