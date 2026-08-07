"""Testes de `backend/llm/native_redis_cache.py` — lógica pura (sem Redis).

Testes que precisam de Redis real com RediSearch (round-trip do cache
exato/semântico contra o índice vetorial de verdade) vivem em
`tests/integration/test_storage_redis.py` — fakeredis não implementa os
comandos `FT.*`, então essa parte não é testável de forma hermética.
"""

from __future__ import annotations

import struct

from langchain_core.load import dumps
from langchain_core.outputs import Generation

from backend.llm.native_redis_cache import (
    _exact_key,
    _extract_index_dim,
    _flatten,
    _llm_tag,
    _pack_vector,
    _parse_ft_search_top1,
)


class TestExactKey:
    def test_determinismo_e_unicidade(self):
        k1 = _exact_key("prompt A", "llm-config-1")
        k2 = _exact_key("prompt A", "llm-config-1")
        assert k1 == k2
        assert k1.startswith("vectora:cache:exact:")

        # Erro/borda: prompt ou llm_string diferentes nunca colidem por acaso
        # (mesmo com concatenação simples) — separador \x1f evita ambiguidade
        # tipo ("ab", "c") vs ("a", "bc").
        assert _exact_key("ab", "c") != _exact_key("a", "bc")
        assert _exact_key("prompt A", "llm-config-2") != k1


class TestLlmTag:
    def test_tag_curta_e_deterministica(self):
        t1 = _llm_tag("model=gpt-4,temp=0.7")
        t2 = _llm_tag("model=gpt-4,temp=0.7")
        assert t1 == t2
        assert len(t1) == 16

        # Erro/borda: strings com caracteres especiais de TAG do RediSearch
        # (vírgula, chaves) não quebram a tag — é sempre hex puro.
        weird = _llm_tag("model={gpt-4},params=[1,2,3]")
        assert all(c in "0123456789abcdef" for c in weird)


class TestPackVector:
    def test_empacota_e_desempacota_float32(self):
        vector = [0.1, -0.5, 3.25, 0.0]
        packed = _pack_vector(vector)
        assert len(packed) == 4 * 4  # 4 floats * 4 bytes

        unpacked = struct.unpack(f"<{len(vector)}f", packed)
        for original, restored in zip(vector, unpacked, strict=True):
            assert abs(original - restored) < 1e-6

    def test_vetor_vazio_nao_levanta(self):
        # Erro/borda: dimensão zero é um caso degenerado, mas não deve
        # explodir — só produz bytes vazios.
        assert _pack_vector([]) == b""


class TestFlattenAndExtractIndexDim:
    def test_extrai_dim_de_resposta_ft_info_aninhada(self):
        # Formato real de FT.INFO: lista de pares chave/valor, com o campo
        # "attributes" contendo uma lista de listas aninhadas por atributo.
        ft_info = [
            "index_name",
            "idx",
            "attributes",
            [
                ["identifier", "vector", "attribute", "vector", "type", "VECTOR"],
                ["DIM", 1024, "DISTANCE_METRIC", "COSINE"],
            ],
        ]
        assert _extract_index_dim(ft_info) == 1024

    def test_sem_campo_dim_retorna_none(self):
        # Erro/borda: resposta sem DIM (ex.: índice sem campo vetorial) não
        # deve levantar — só devolve None pra sinalizar "recriar índice".
        ft_info = ["index_name", "idx", "attributes", []]
        assert _extract_index_dim(ft_info) is None

    def test_flatten_lida_com_bytes_e_tipos_mistos(self):
        nested = [b"a", [1, 2, ["b", 3.0]], {"k": "v"}]
        flat = _flatten(nested)
        assert b"a" in flat
        assert 1 in flat
        assert "v" in flat


class TestParseFtSearchTop1:
    def test_extrai_score_e_return_val_do_primeiro_hit(self):
        generations = [Generation(text="resposta cacheada")]
        return_val = dumps(generations)
        result = [
            1,
            b"vectora:cache:sem:abc123",
            [b"return_val", return_val.encode(), b"score", b"0.05"],
        ]
        hit = _parse_ft_search_top1(result)
        assert hit is not None
        score, raw = hit
        assert score == 0.05
        assert raw == return_val

    def test_zero_resultados_retorna_none(self):
        # Erro/borda: FT.SEARCH sem hit devolve total=0 e nenhum documento —
        # não pode ser confundido com um hit válido.
        assert _parse_ft_search_top1([0]) is None

    def test_resposta_malformada_sem_campos_esperados_retorna_none(self):
        # Erro/borda: hit existe mas sem return_val/score (índice corrompido
        # ou schema mudou) — degrada pra miss, não levanta exceção.
        result = [1, b"doc_id", [b"outro_campo", b"valor"]]
        assert _parse_ft_search_top1(result) is None

    def test_resposta_vazia_ou_curta_demais_retorna_none(self):
        assert _parse_ft_search_top1([]) is None
        assert _parse_ft_search_top1([1, b"doc"]) is None
