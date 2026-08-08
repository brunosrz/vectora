"""Remember — distill_transcript/dedupe_skill_drafts: destilação de um
transcript em skills reutilizáveis e fatos duráveis, via LLM estruturado."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.learning import (
    DistillationResult,
    SkillDraft,
    dedupe_fact_drafts,
    dedupe_skill_drafts,
    distill_transcript,
)


@pytest.mark.asyncio
async def test_distill_transcript_empty_input_returns_empty_result_without_llm_call(
    monkeypatch,
):
    load_llm_mock = MagicMock()
    monkeypatch.setattr("backend.services.utils.load_llm", load_llm_mock)

    result = await distill_transcript("   ")

    assert result == DistillationResult()
    load_llm_mock.assert_not_called()


@pytest.mark.asyncio
async def test_distill_transcript_happy_path_returns_skills_and_facts(monkeypatch):
    expected = DistillationResult(
        skills=[
            SkillDraft(
                name="Debug de streaming duplicado",
                description="Use quando tokens SSE duplicarem",
                content="1. Verifique o fallback model\n2. Confira reasoning blocks",
            )
        ],
        facts=["Usuário prefere respostas em português brasileiro"],
    )
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=expected)
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: bug no streaming\nassistant: corrigido")

    assert result == expected


@pytest.mark.asyncio
async def test_distill_transcript_llm_failure_degrades_to_empty_result(monkeypatch):
    llm = MagicMock()
    llm.with_structured_output.side_effect = RuntimeError("modelo indisponível")
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: oi\nassistant: olá")

    assert result == DistillationResult()


def test_dedupe_skill_drafts_removes_names_already_installed():
    drafts = [
        SkillDraft(name="Debug de streaming", description="d", content="c"),
        SkillDraft(name="Nova skill", description="d2", content="c2"),
    ]

    result = dedupe_skill_drafts(drafts, {"debug de streaming"})

    assert [d.name for d in result] == ["Nova skill"]


def test_dedupe_skill_drafts_no_existing_names_keeps_all_drafts():
    drafts = [SkillDraft(name="A", description="d", content="c")]

    result = dedupe_skill_drafts(drafts, set())

    assert result == drafts


def test_dedupe_skill_drafts_empty_drafts_list_returns_empty():
    result = dedupe_skill_drafts([], {"algo"})

    assert result == []


def test_dedupe_skill_drafts_matches_case_and_whitespace_insensitively():
    # "quase idênticos" — mesma skill com capitalização/espaços diferentes
    # não deve virar uma entrada nova (duplicata disfarçada).
    drafts = [
        SkillDraft(name="  Debug DE Streaming  ", description="d", content="c"),
    ]

    result = dedupe_skill_drafts(drafts, {"debug de streaming"})

    assert result == []


def test_dedupe_skill_drafts_duplicate_names_within_input_both_removed():
    drafts = [
        SkillDraft(name="Skill X", description="d1", content="c1"),
        SkillDraft(name="skill x", description="d2", content="c2"),
    ]

    result = dedupe_skill_drafts(drafts, {"skill x"})

    assert result == []


def test_dedupe_skill_drafts_preserves_order_of_kept_drafts():
    drafts = [
        SkillDraft(name="Mantida 1", description="d", content="c"),
        SkillDraft(name="Removida", description="d", content="c"),
        SkillDraft(name="Mantida 2", description="d", content="c"),
    ]

    result = dedupe_skill_drafts(drafts, {"removida"})

    assert [d.name for d in result] == ["Mantida 1", "Mantida 2"]


@pytest.mark.asyncio
async def test_distill_transcript_whitespace_only_never_touches_llm(monkeypatch):
    # Borda adicional: transcript só com quebras de linha/tabs — mesmo
    # tratamento de vazio, sem chamar load_llm.
    load_llm_mock = MagicMock()
    monkeypatch.setattr("backend.services.utils.load_llm", load_llm_mock)

    result = await distill_transcript("\n\t  \n")

    assert result == DistillationResult()
    load_llm_mock.assert_not_called()


@pytest.mark.asyncio
async def test_distill_transcript_llm_returns_no_reusable_pattern_yields_empty_lists(
    monkeypatch,
):
    # "Se o transcript não tiver nenhum padrão reutilizável... devolva
    # listas vazias — isso é um resultado válido, não uma falha."
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=DistillationResult(skills=[], facts=[]))
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: oi\nassistant: oi, tudo bem?")

    assert result.skills == []
    assert result.facts == []


@pytest.mark.asyncio
async def test_distill_transcript_llm_returns_dict_is_validated_into_result(
    monkeypatch,
):
    # Nem todo provider devolve a instância Pydantic diretamente — um dict
    # bruto deve ser validado via model_validate, não rejeitado.
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value={
            "skills": [{"name": "X", "description": "y", "content": "z"}],
            "facts": ["fato"],
        }
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: teste\nassistant: ok")

    assert result.skills[0].name == "X"
    assert result.facts == ["fato"]


@pytest.mark.asyncio
async def test_distill_transcript_llm_returns_malformed_payload_degrades_to_empty(
    monkeypatch,
):
    # Payload malformado (não valida contra DistillationResult) — não
    # propaga ValidationError, degrada como qualquer outra falha de LLM.
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value={"skills": "não é uma lista"})
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: teste\nassistant: ok")

    assert result == DistillationResult()


@pytest.mark.asyncio
async def test_distill_transcript_truncates_input_beyond_20000_chars(monkeypatch):
    huge_transcript = "a" * 25000
    captured_messages: list = []

    structured = MagicMock()

    async def _fake_ainvoke(messages):
        captured_messages.extend(messages)
        return DistillationResult()

    structured.ainvoke = _fake_ainvoke
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    await distill_transcript(huge_transcript)

    human_message = captured_messages[-1]
    assert len(human_message.content) == 20000


@pytest.mark.asyncio
async def test_distill_transcript_llm_timeout_degrades_to_empty_result(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(side_effect=TimeoutError("llm demorou demais"))
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: teste\nassistant: ok")

    assert result == DistillationResult()


def test_dedupe_skill_drafts_nome_com_espacos_internos_nao_e_colapsado():
    # Borda: normalização é só strip+lower nas pontas, não colapsa espaços
    # internos duplicados — "debug  streaming" != "debug streaming".
    drafts = [SkillDraft(name="Debug  Streaming", description="d", content="c")]

    result = dedupe_skill_drafts(drafts, {"debug streaming"})

    assert [d.name for d in result] == ["Debug  Streaming"]


def test_dedupe_skill_drafts_existing_names_tambem_normalizado_com_espacos_nas_pontas():
    # O lado `existing_names` também passa por strip+lower, não só os
    # drafts — nome vindo do backend com espaço residual ainda casa.
    drafts = [SkillDraft(name="minha skill", description="d", content="c")]

    result = dedupe_skill_drafts(drafts, {"  Minha Skill  "})

    assert result == []


def test_dedupe_skill_drafts_muitos_drafts_e_muitos_existentes_ordem_trocada():
    # Ordem trocada: existing_names é um set (sem ordem); drafts mantêm a
    # ordem de entrada independente da ordem de iteração do set.
    drafts = [
        SkillDraft(name="Z", description="d", content="c"),
        SkillDraft(name="A", description="d", content="c"),
        SkillDraft(name="M", description="d", content="c"),
    ]

    result = dedupe_skill_drafts(drafts, {"a", "m"})

    assert [d.name for d in result] == ["Z"]


@pytest.mark.asyncio
async def test_distill_transcript_transcript_so_com_um_caractere_ainda_chama_llm(
    monkeypatch,
):
    # Borda: um único caractere não-vazio passa pela checagem `.strip()`
    # e chega a chamar o LLM — só string vazia/whitespace pula a chamada.
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=DistillationResult())
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    load_llm_mock = MagicMock(return_value=llm)
    monkeypatch.setattr("backend.services.utils.load_llm", load_llm_mock)

    await distill_transcript("x")

    load_llm_mock.assert_called_once()


# ---------------------------------------------------------------------------
# dedupe_fact_drafts — Sprint 16 WS3: mesma paridade de dedup que skills já
# tinham (dedupe_skill_drafts), agora também pra fatos propostos pelo
# Remember, pra não propor de novo um fato já aprovado em sessão anterior.
# ---------------------------------------------------------------------------


def test_dedupe_fact_drafts_removes_facts_already_saved():
    facts = ["Usuário prefere respostas em português brasileiro", "Fato novo"]

    result = dedupe_fact_drafts(
        facts, ["usuário prefere respostas em português brasileiro"]
    )

    assert result == ["Fato novo"]


def test_dedupe_fact_drafts_no_existing_facts_keeps_all_drafts():
    facts = ["Fato A", "Fato B"]

    result = dedupe_fact_drafts(facts, [])

    assert result == facts


def test_dedupe_fact_drafts_empty_drafts_list_returns_empty():
    result = dedupe_fact_drafts([], ["algo"])

    assert result == []


def test_dedupe_fact_drafts_matches_case_and_edge_whitespace_insensitively():
    # Mesma normalização de dedupe_skill_drafts: strip+lower nas pontas —
    # não colapsa espaços internos duplicados.
    facts = ["  Prefere DARK mode  "]

    result = dedupe_fact_drafts(facts, ["prefere dark mode"])

    assert result == []


def test_dedupe_fact_drafts_internal_double_spaces_not_collapsed():
    facts = ["Prefere  dark mode"]

    result = dedupe_fact_drafts(facts, ["prefere dark mode"])

    assert result == ["Prefere  dark mode"]


def test_dedupe_fact_drafts_duplicate_facts_within_input_both_removed():
    facts = ["Fato X", "fato x"]

    result = dedupe_fact_drafts(facts, ["fato x"])

    assert result == []


def test_dedupe_fact_drafts_preserves_order_of_kept_facts():
    facts = ["Mantido 1", "Removido", "Mantido 2"]

    result = dedupe_fact_drafts(facts, ["removido"])

    assert result == ["Mantido 1", "Mantido 2"]


def test_dedupe_fact_drafts_existing_facts_also_normalized_with_edge_whitespace():
    facts = ["minha preferência"]

    result = dedupe_fact_drafts(facts, ["  Minha Preferência  "])

    assert result == []
